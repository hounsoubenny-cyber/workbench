"""
Docukit — tests d'intégration : VRAIS binaires, application complète.

Chaque test passe par l'API HTTP/WebSocket réelle (création du job, upload,
exécution, téléchargement) puis VÉRIFIE le fichier produit avec un outil
indépendant (qpdf --show-npages, pdftotext, pdfinfo...) : on contrôle le
résultat, pas seulement le code de retour.
"""

import struct
import subprocess

import pytest

from workbench.products.docukit.dk_utils.tools import pandoc_sandbox_supports
from workbench.products.docukit.tests.conftest import (
    need, page_count, pdf_text, run_tool,
)


def _rc(*cmd) -> int:
    return subprocess.run(cmd, capture_output=True, timeout=60).returncode


# =============================================================================
# qpdf
# =============================================================================

@need("qpdf", "pdftotext")
class TestQpdf:
    def test_merge_keeps_order(self, api, pdf3, pdf2, tmp_path):
        job = api.run("qpdf_merge", {"inputs": ["a.pdf", "b.pdf"]}, [("a.pdf", pdf3), ("b.pdf", pdf2)])
        assert job.ok, job.result
        out = job.download()
        text = pdf_text(out, tmp_path)
        assert page_count(out, tmp_path) == 5
        assert text.index("ALPHA PAGE 1") < text.index("ALPHA PAGE 3") < text.index("BRAVO PAGE 1")

    def test_extract_pages(self, api, pdf3, tmp_path):
        job = api.run("qpdf_extract_pages", {"input_file": "a.pdf", "pages": "2-3"}, [("a.pdf", pdf3)])
        out = job.download()
        text = pdf_text(out, tmp_path)
        assert job.ok and page_count(out, tmp_path) == 2
        assert "ALPHA PAGE 2" in text and "ALPHA PAGE 1" not in text

    def test_delete_pages(self, api, pdf3, tmp_path):
        job = api.run("qpdf_delete_pages", {"input_file": "a.pdf", "pages": "2"}, [("a.pdf", pdf3)])
        out = job.download()
        text = pdf_text(out, tmp_path)
        assert job.ok and page_count(out, tmp_path) == 2
        assert "PAGE 1" in text and "PAGE 3" in text and "PAGE 2" not in text

    def test_reverse_pages(self, api, pdf3, tmp_path):
        job = api.run("qpdf_reverse_pages", {"input_file": "a.pdf"}, [("a.pdf", pdf3)])
        text = pdf_text(job.download(), tmp_path)
        assert text.index("PAGE 3") < text.index("PAGE 2") < text.index("PAGE 1")

    def test_rotate_selected_page_only(self, api, pdf3, tmp_path):
        job = api.run("qpdf_rotate", {"input_file": "a.pdf", "angle": "90", "pages": "2"}, [("a.pdf", pdf3)])
        assert job.ok, job.result
        path = tmp_path / "rot.pdf"
        path.write_bytes(job.download())
        info = run_tool("pdfinfo", "-f", "1", "-l", "3", str(path))
        rotations = {int(line.split()[1]): int(line.split()[-1]) for line in info.splitlines() if " rot:" in line}
        assert rotations == {1: 0, 2: 90, 3: 0}

    @pytest.mark.parametrize("mode", ["overlay", "underlay"])
    def test_stamp(self, api, pdf3, stamp_pdf, tmp_path, mode):
        job = api.run(
            "qpdf_stamp", {"input_file": "a.pdf", "stamp_file": "s.pdf", "mode": mode},
            [("a.pdf", pdf3), ("s.pdf", stamp_pdf)],
        )
        out = job.download()
        text = pdf_text(out, tmp_path)
        assert job.ok and page_count(out, tmp_path) == 3
        assert text.count("CONFIDENTIEL") == 3, "le tampon doit figurer sur chaque page"

    def test_protect_then_unlock_roundtrip(self, api, pdf3, tmp_path):
        job = api.run(
            "qpdf_protect",
            {"input_file": "a.pdf", "password": "S3cret é", "allow_print": False},
            [("a.pdf", pdf3)],
        )
        assert job.ok, job.result
        protected = tmp_path / "protected.pdf"
        protected.write_bytes(job.download())
        assert _rc("qpdf", "--is-encrypted", str(protected)) == 0, "le PDF doit être chiffré"
        assert "ncorrect password" in run_tool("pdftotext", str(protected), "-")

        job2 = api.run("qpdf_unlock", {"input_file": "p.pdf", "password": "S3cret é"}, [("p.pdf", protected.read_bytes())])
        assert job2.ok, job2.result
        assert "ALPHA PAGE 1" in pdf_text(job2.download(), tmp_path)

    def test_unlock_with_wrong_password_fails_cleanly(self, api, pdf3, tmp_path):
        protected = api.run("qpdf_protect", {"input_file": "a.pdf", "password": "good"}, [("a.pdf", pdf3)]).download()
        job = api.run("qpdf_unlock", {"input_file": "p.pdf", "password": "bad"}, [("p.pdf", protected)])
        assert not job.ok and job.result["returncode"] == 2

    def test_check_report(self, api, pdf3):
        job = api.run("qpdf_check", {"input_file": "a.pdf"}, [("a.pdf", pdf3)])
        assert job.ok
        assert "No syntax or stream encoding errors found" in job.download().decode()

    def test_repair_damaged_xref(self, api, pdf3, tmp_path):
        damaged = pdf3.replace(b"startxref", b"startxreX")
        job = api.run("qpdf_repair", {"input_file": "a.pdf"}, [("a.pdf", damaged)])
        assert job.ok, job.result            # --warning-exit-0 : réparé avec avertissements = succès
        assert page_count(job.download(), tmp_path) == 3

    @pytest.mark.parametrize("web", [False, True])
    def test_optimize(self, api, pdf3, tmp_path, web):
        job = api.run("qpdf_optimize", {"input_file": "a.pdf", "web_optimized": web}, [("a.pdf", pdf3)])
        assert job.ok, job.result
        path = tmp_path / "opt.pdf"
        path.write_bytes(job.download())
        report = run_tool("qpdf", "--check", str(path))
        assert ("File is linearized" in report) is web
        assert page_count(path.read_bytes(), tmp_path) == 3


# =============================================================================
# poppler
# =============================================================================

@need("pdftotext", "pdftoppm", "pdfinfo", "pdfimages")
class TestPoppler:
    def test_text_extraction_page_range(self, api, pdf3):
        job = api.run("pdftotext_extract", {"input_file": "a.pdf", "first_page": 2, "last_page": 2}, [("a.pdf", pdf3)])
        text = job.download().decode()
        assert job.ok and "ALPHA PAGE 2" in text and "PAGE 1" not in text and "PAGE 3" not in text

    def test_text_extraction_options(self, api, pdf3):
        job = api.run(
            "pdftotext_extract",
            {"input_file": "a.pdf", "layout": True, "page_breaks": False}, [("a.pdf", pdf3)],
        )
        text = job.download().decode()
        assert job.ok and "\f" not in text and "Bonjour le monde" in text

    def test_render_png_is_bounded(self, api, pdf3):
        job = api.run(
            "pdftoppm_render_page", {"input_file": "a.pdf", "page": 2, "longest_side": 400}, [("a.pdf", pdf3)]
        )
        png = job.download()
        assert job.ok and png.startswith(b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", png[16:24])
        assert max(width, height) == 400, "le plus grand côté est borné, quelle que soit la page"

    def test_render_jpeg_grayscale(self, api, pdf3):
        job = api.run(
            "pdftoppm_render_page",
            {"input_file": "a.pdf", "format": "jpeg", "grayscale": True, "longest_side": 300}, [("a.pdf", pdf3)],
        )
        assert job.ok and job.result_file() == "page.jpg" and job.download().startswith(b"\xff\xd8\xff")

    def test_render_page_out_of_range_fails(self, api, pdf3):
        job = api.run("pdftoppm_render_page", {"input_file": "a.pdf", "page": 99}, [("a.pdf", pdf3)])
        assert not job.ok

    def test_info(self, api, pdf3):
        job = api.run("pdfinfo_summary", {"input_file": "a.pdf"}, [("a.pdf", pdf3)])
        assert job.ok and "Pages:" in job.download().decode() and "3" in job.download().decode()

    def test_images_list_without_images(self, api, pdf3):
        job = api.run("pdfimages_list", {"input_file": "a.pdf"}, [("a.pdf", pdf3)])
        lines = [ln for ln in job.download().decode().splitlines() if ln.strip()]
        assert job.ok and len(lines) <= 2   # en-tête seul : aucune image


# =============================================================================
# tesseract
# =============================================================================

@need("qpdf", "pdftoppm", "pdftotext", "tesseract")
class TestOcr:
    @pytest.fixture
    def scan_png(self, api, pdf3) -> bytes:
        job = api.run(
            "pdftoppm_render_page", {"input_file": "a.pdf", "page": 1, "longest_side": 2200}, [("a.pdf", pdf3)]
        )
        return job.download()

    def test_image_to_text(self, api, scan_png):
        job = api.run(
            "tesseract_ocr_text", {"input_file": "scan.png", "language": "eng"}, [("scan.png", scan_png)]
        )
        assert job.ok, job.result
        assert "ALPHA" in job.download().decode()

    def test_image_to_searchable_pdf(self, api, scan_png, tmp_path):
        job = api.run(
            "tesseract_searchable_pdf", {"input_file": "scan.png", "language": "eng"}, [("scan.png", scan_png)]
        )
        assert job.ok, job.result
        assert "ALPHA" in pdf_text(job.download(), tmp_path)

    def test_missing_language_model_is_refused_with_a_clear_message(self, api, scan_png, monkeypatch):
        monkeypatch.setattr(
            "workbench.products.docukit.specs.tesseract.actions.tesseract_languages",
            lambda: frozenset({"eng"}),
        )
        r = api.create("tesseract_ocr_text", {"input_file": "scan.png", "language": "fra"}, [("scan.png", scan_png)])
        assert r.status_code == 422 and "modèle OCR manquant" in r.text and "fra" in r.text


# =============================================================================
# pandoc
# =============================================================================

@need("pandoc")
class TestPandoc:
    MD = b"# Titre\n\nUn **test** avec une liste :\n\n- un\n- deux\n"

    def test_markdown_to_html(self, api):
        job = api.run("pandoc_convert", {"input_file": "d.md", "to_format": "html"}, [("d.md", self.MD)])
        html = job.download().decode()
        assert job.ok and "<h1" in html and "Titre" in html and "<li>" in html

    def test_markdown_to_plain_text(self, api):
        job = api.run("pandoc_convert", {"input_file": "d.md", "to_format": "plain"}, [("d.md", self.MD)])
        text = job.download().decode()
        assert job.ok and "Titre" in text and "**" not in text

    def test_html_to_markdown(self, api):
        job = api.run(
            "pandoc_convert", {"input_file": "d.html", "from_format": "html", "to_format": "gfm", "standalone": False},
            [("d.html", b"<h2>Sous-titre</h2><p>Texte <em>fin</em></p>")],
        )
        assert job.ok and "## Sous-titre" in job.download().decode()

    @pytest.mark.parametrize("fmt", ["docx", "odt", "epub"])
    def test_office_outputs_work_in_sandbox_or_are_refused_never_unsandboxed(self, api, fmt):
        """
        Binaire officiel : la conversion réussit, EN sandbox. Paquet de
        distribution (données externes) : refus explicite — jamais de repli
        silencieux vers une exécution sans sandbox.
        """
        r = api.create("pandoc_convert", {"input_file": "d.md", "to_format": fmt}, [("d.md", self.MD)])
        if pandoc_sandbox_supports(fmt):
            job = api.run("pandoc_convert", {"input_file": "d.md", "to_format": fmt}, [("d.md", self.MD)])
            assert job.ok and job.download().startswith(b"PK")   # docx / odt / epub = archives zip
        else:
            assert r.status_code == 422 and "sandbox" in r.text.lower()

    def test_toc_requires_standalone(self, api):
        r = api.create("pandoc_convert", {"input_file": "d.md", "to_format": "html", "standalone": False, "toc": True},
                       [("d.md", self.MD)])
        assert r.status_code == 422

    def test_local_file_reference_is_not_read(self, api, tmp_path):
        """Avec --sandbox, `![x](chemin local)` ne fait lire aucun fichier à pandoc."""
        secret = tmp_path / "secret.png"
        secret.write_bytes(b"\x89PNG-SECRET-CONTENT")
        md = f"![x]({secret})\n".encode()
        job = api.run("pandoc_convert", {"input_file": "d.md", "to_format": "html"}, [("d.md", md)])
        assert job.ok and b"SECRET-CONTENT" not in job.download()


# =============================================================================
# Pipelines
# =============================================================================

@need("qpdf", "pdftotext")
class TestPipelinesQpdf:
    def test_merge_then_optimize(self, api, pdf3, pdf2, tmp_path):
        job = api.run("docukit_merge_optimize", {"inputs": ["a.pdf", "b.pdf"]}, [("a.pdf", pdf3), ("b.pdf", pdf2)])
        assert job.ok, (job.result, job.error)
        out = tmp_path / "final.pdf"
        out.write_bytes(job.download())
        assert job.result_file() == "optimized.pdf"
        assert page_count(out.read_bytes(), tmp_path) == 5
        assert "File is linearized" in run_tool("qpdf", "--check", str(out))

    def test_protected_excerpt_and_secrets_never_leave_the_server(self, api, pdf3, tmp_path):
        password = "Tr0ub4dor&3-UNIQUE"
        job = api.run(
            "docukit_protected_excerpt",
            {"input_file": "a.pdf", "pages": "1-2", "password": password, "owner_password": password + "-owner"},
            [("a.pdf", pdf3)],
        )
        assert job.ok, (job.result, job.error)
        import json
        everything = json.dumps(job.messages) + job.client.get("/api/catalog").text
        assert password not in everything, "le mot de passe ne doit JAMAIS apparaître dans les messages"

        protected = job.download()
        unlocked = api.run("qpdf_unlock", {"input_file": "p.pdf", "password": password}, [("p.pdf", protected)])
        assert page_count(unlocked.download(), tmp_path) == 2


@need("pdftoppm", "tesseract")
class TestPipelineOcr:
    def test_ocr_page(self, api, pdf3):
        job = api.run("docukit_ocr_page", {"input_file": "a.pdf", "page": 2, "language": "eng"}, [("a.pdf", pdf3)])
        assert job.ok, (job.result, job.error)
        text = job.download().decode()
        assert "ALPHA" in text and "2" in text

    def test_failing_step_is_reported_not_silent(self, api, pdf3):
        """Page inexistante : l'étape 1 échoue -> job `failed` + message clair (pas de blocage)."""
        job = api.run("docukit_ocr_page", {"input_file": "a.pdf", "page": 99, "language": "eng"}, [("a.pdf", pdf3)])
        assert not job.ok
        assert job.error["error_code"] == "PIPELINE_STEP_FAILED" and "step_render" in job.error["message"]
        status = job.client.get("/api/job/status", params={"job_id": job.job_id}).json()["status"]
        assert status == "failed"


# =============================================================================
# Entrées invalides : refusées AVANT toute exécution
# =============================================================================

@need("qpdf")
class TestInvalidInputs:
    def test_file_content_is_checked_not_the_extension(self, api):
        r = api.create("qpdf_check", {"input_file": "a.pdf"}, [("a.pdf", b"ceci n'est pas un PDF")])
        assert r.status_code == 422 and "PDF" in r.text

    def test_image_spec_refuses_a_pdf(self, api, pdf3):
        r = api.create("tesseract_ocr_text", {"input_file": "a.png"}, [("a.png", pdf3)])
        assert r.status_code == 422

    @pytest.mark.parametrize("name", ["merged.pdf", "../a.pdf", "a/b.pdf", "-a.pdf", "a.txt"])
    def test_dangerous_or_reserved_names_refused(self, api, pdf3, name):
        r = api.create("qpdf_check", {"input_file": name}, [(name, pdf3)])
        assert r.status_code == 422

    @pytest.mark.parametrize("pages", ["0", "1-", "abc", "1,,2", "--password=x", "1;id", "1-3\n--evil"])
    def test_bad_page_ranges_refused(self, api, pdf3, pages):
        r = api.create("qpdf_extract_pages", {"input_file": "a.pdf", "pages": pages}, [("a.pdf", pdf3)])
        assert r.status_code == 422

    def test_password_cannot_look_like_an_option(self, api, pdf3):
        r = api.create("qpdf_protect", {"input_file": "a.pdf", "password": "--decrypt"}, [("a.pdf", pdf3)])
        assert r.status_code == 422

    def test_upload_count_must_match(self, api, pdf3):
        r = api.create("qpdf_merge", {"inputs": ["a.pdf", "b.pdf"]}, [("a.pdf", pdf3)])
        assert r.status_code == 422 and "UPLOAD_COUNT_MISMATCH" in r.text

    def test_merge_needs_at_least_two_files(self, api, pdf3):
        r = api.create("qpdf_merge", {"inputs": ["a.pdf"]}, [("a.pdf", pdf3)])
        assert r.status_code == 422

    def test_unknown_spec_is_404(self, api):
        assert api.create("nope", {}).status_code == 404

    def test_error_responses_never_echo_the_password(self, api, pdf3):
        secret = "ECHO-ME-IF-YOU-DARE"
        r = api.create("qpdf_protect", {"input_file": "merged.pdf", "password": secret}, [("merged.pdf", pdf3)])
        assert r.status_code == 422 and secret not in r.text
