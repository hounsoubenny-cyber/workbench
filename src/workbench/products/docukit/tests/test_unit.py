"""
Docukit — tests unitaires (aucun binaire requis).
"""

import pytest
from pydantic import ValidationError

from workbench.core.subprocess.wb_subprocess_types import EnumArg
from workbench.specs.pipeline_spec import PipelineSpec
from workbench.specs.uploads import collect_upload_filenames
from workbench.wb_utils.model_parser import model_to_dict

from workbench.products.docukit.api.env import Settings
from workbench.products.docukit.dk_utils.files import is_image_file, is_pdf_file
from workbench.products.docukit.specs.common import (
    RESERVED_NAMES, Out, attached_option, check_filename, check_filenames,
    check_page_range, check_password, ordered,
)
from workbench.products.docukit.specs.utils import (
    ALL_SPECS, BINARY_CONFIGS, CATEGORIES, INSTALL_HINTS, get_catalog,
)


# ─── Noms de fichiers ────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", ["a.pdf", "Mon rapport (v2).PDF", "x" * 96 + ".pdf", "é.pdf"])
def test_valid_filenames(name):
    assert check_filename(name, (".pdf",)) == name


@pytest.mark.parametrize("name", [
    "../x.pdf", "a/b.pdf", "a\\b.pdf", "C:evil.pdf", "-rf.pdf", ".hidden.pdf",
    "a.pdf ", "a.", "tab\t.pdf", "nul\x00.pdf", "x" * 101 + ".pdf", "", "a.txt",
])
def test_invalid_filenames(name):
    with pytest.raises(ValueError):
        check_filename(name, (".pdf",))


def test_output_names_are_reserved_case_insensitively():
    """Un upload nommé comme une sortie ferait lire ET écrire le même fichier."""
    for name in ("merged.pdf", "MERGED.PDF", "page.png", "ocr_text.txt", "converted.docx"):
        assert name.lower() in RESERVED_NAMES
        with pytest.raises(ValueError, match="réservé"):
            check_filename(name)
    assert {v.lower() for k, v in vars(Out).items() if not k.startswith("_")} <= RESERVED_NAMES


def test_duplicate_names_refused_ignoring_case():
    with pytest.raises(ValueError, match="double"):
        check_filenames(["a.pdf", "A.PDF"], (".pdf",))


# ─── Plages de pages ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("value", ["1", "1-3", "1-3,5,8-z", "z", "r1", "2-r2", "1-z:odd", "1-z,x3", "10-20:even"])
def test_valid_page_ranges(value):
    assert check_page_range(value) == value


@pytest.mark.parametrize("value", [
    "", "0", "1-", "-3", "abc", "1,,2", "1 2", "--rotate", "1;rm", "1-3\n", "x", "1-z:odd:even", "9" * 8,
])
def test_invalid_page_ranges(value):
    with pytest.raises(ValueError):
        check_page_range(value)


def test_exclusion_is_refused_where_not_allowed():
    assert check_page_range("1-z,x3")
    with pytest.raises(ValueError):
        check_page_range("1-z,x3", allow_exclusion=False)


# ─── Mots de passe ───────────────────────────────────────────────────────────

def test_password_rules():
    assert check_password("S3cret é!") == "S3cret é!"
    for bad in ("", "-abc", "a\nb", "a\x00b", "x" * 129):
        with pytest.raises(ValueError):
            check_password(bad)


# ─── Option collée : une seule chaîne, validée ───────────────────────────────

def test_attached_option_builds_a_single_validated_argv():
    arg = attached_option("--rotate", "+90:1-z", r"\+(?:90|180|270):[0-9z,\-]+")
    assert isinstance(arg, EnumArg) and arg.value == "--rotate=+90:1-z"


@pytest.mark.parametrize("value", ["+90:1-z --password=x", "+90:1-z\n--evil", "+45:1", "+90:"])
def test_attached_option_rejects_injection(value):
    with pytest.raises(ValueError):
        attached_option("--rotate", value, r"\+(?:90|180|270):[0-9z,\-]+")


# ─── Types de fichiers (par signature, pas par extension) ────────────────────

def test_pdf_and_image_sniffing(tmp_path):
    pdf, png, txt = tmp_path / "a.pdf", tmp_path / "a.png", tmp_path / "a.txt"
    pdf.write_bytes(b"%PDF-1.7\n...")
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 20)
    txt.write_text("juste du texte")
    assert is_pdf_file(pdf) and not is_pdf_file(png) and not is_pdf_file(txt)
    assert is_image_file(png) and not is_image_file(pdf) and not is_image_file(txt)
    (tmp_path / "bruit.pdf").write_bytes(b"\xef\xbb\xbfjunk" + b"%PDF-1.4")   # bruit avant l'en-tête : toléré
    assert is_pdf_file(tmp_path / "bruit.pdf")
    assert not is_pdf_file(tmp_path / "absent.pdf") and not is_image_file(tmp_path / "absent.png")


# ─── Réglages ────────────────────────────────────────────────────────────────

def test_settings_defaults_are_local_and_safe():
    s = Settings.from_env({})
    assert s.host == "127.0.0.1" and s.port == 0 and s.max_upload_mb == 200
    assert s.config_path.name == "config.toml" and s.allowed_hosts == ()


def test_settings_from_env():
    s = Settings.from_env({
        "DOCUKIT_PORT": "8123", "DOCUKIT_MAX_UPLOAD_MB": "5", "DOCUKIT_OPEN_BROWSER": "0",
        "DOCUKIT_ALLOWED_HOSTS": "a.local, b.local", "DOCUKIT_CONFIG_FILE": "/tmp/x.toml",
    })
    assert (s.port, s.max_upload_mb, s.open_browser) == (8123, 5, False)
    assert s.allowed_hosts == ("a.local", "b.local") and str(s.config_path) == "/tmp/x.toml"


@pytest.mark.parametrize("env", [{"DOCUKIT_PORT": "abc"}, {"DOCUKIT_PORT": "70000"}, {"DOCUKIT_MAX_UPLOAD_MB": "0"}])
def test_settings_reject_bad_values(env):
    with pytest.raises(ValueError):
        Settings.from_env(env)


# ─── Catalogue : cohérence globale ───────────────────────────────────────────

def test_catalog_integrity():
    assert len(ALL_SPECS) == 21
    cat = get_catalog()
    in_categories = [sid for c in cat["categories"] for sid in c["specs"]]
    assert sorted(in_categories) == sorted(ALL_SPECS), "chaque spec dans UNE catégorie"
    for sid, summary in cat["specs"].items():
        assert summary["label"] and summary["description"], f"{sid} sans libellé/description"
        assert all(t in INSTALL_HINTS and t in BINARY_CONFIGS for t in summary["tools"]), sid
    assert {c["id"] for c in CATEGORIES} == {c["id"] for c in cat["categories"]}


def test_ordered_refuses_duplicate_ids():
    spec = next(iter(ALL_SPECS.values()))
    with pytest.raises(ValueError):
        ordered(spec, spec)


# Entrées valides minimales pour construire la commande de chaque action.
SAMPLES = {
    "qpdf_merge": {"inputs": ["a.pdf", "b.pdf"]},
    "qpdf_extract_pages": {"input_file": "a.pdf", "pages": "1-2"},
    "qpdf_delete_pages": {"input_file": "a.pdf", "pages": "2,4-5"},
    "qpdf_reverse_pages": {"input_file": "a.pdf"},
    "qpdf_rotate": {"input_file": "a.pdf", "angle": "90", "pages": "1-z"},
    "qpdf_stamp": {"input_file": "a.pdf", "stamp_file": "s.pdf"},
    "qpdf_protect": {"input_file": "a.pdf", "password": "secret"},
    "qpdf_unlock": {"input_file": "a.pdf", "password": "secret"},
    "qpdf_check": {"input_file": "a.pdf"},
    "qpdf_repair": {"input_file": "a.pdf"},
    "qpdf_optimize": {"input_file": "a.pdf", "web_optimized": True},
    "pdfinfo_summary": {"input_file": "a.pdf"},
    "pdftotext_extract": {"input_file": "a.pdf", "first_page": 2, "last_page": 3, "layout": True},
    "pdftoppm_render_page": {"input_file": "a.pdf", "page": 2, "format": "jpeg"},
    "pdfimages_list": {"input_file": "a.pdf"},
    "tesseract_ocr_text": {"input_file": "scan.png"},
    "tesseract_searchable_pdf": {"input_file": "scan.png", "language": "fra+eng"},
    "pandoc_convert": {"input_file": "doc.md", "from_format": "markdown", "to_format": "html"},
}


def _flags(args):
    return [getattr(a, "flag", None) for a in args]


@pytest.mark.parametrize("spec_id", [s for s in ALL_SPECS if s in SAMPLES])
def test_every_action_builds_its_command(spec_id, tmp_path):
    """La commande se construit, avec les arguments communs, et le nom de sortie est connu."""
    spec = ALL_SPECS[spec_id]
    user_input = spec.input_cls.model_validate(SAMPLES[spec_id])
    args = spec.full_args(user_input)
    assert args, spec_id
    out = spec.output_filename_template
    out = out(user_input) if callable(out) else out
    assert out and "/" not in out and out.lower() in RESERVED_NAMES
    if spec.tool == "qpdf":
        assert _flags(args)[0] == "--warning-exit-0"
    if spec.tool == "pandoc":
        assert _flags(args)[0] == "--sandbox", "pandoc doit TOUJOURS tourner en --sandbox"


def test_every_input_model_has_a_form_and_pipelines_cover_all_actions():
    assert set(SAMPLES) | {s for s, v in ALL_SPECS.items() if isinstance(v, PipelineSpec)} == set(ALL_SPECS)
    for sid, spec in ALL_SPECS.items():
        form = model_to_dict(spec.input_cls)
        assert form, sid
        assert all(f["type"] and not f["type"].startswith("list[typing") for f in form.values()), sid


def test_upload_fields_reject_every_reserved_name():
    """Pour TOUT champ UploadRef de TOUT modèle : un nom réservé est refusé à la validation."""
    for sid, spec in ALL_SPECS.items():
        model = spec.input_cls
        uploads = [n for n, f in model_to_dict(model).items() if f["is_upload"]]
        assert uploads, sid
        sample = dict(SAMPLES.get(sid) or _pipeline_sample(sid))
        for field_name in uploads:
            bad = dict(sample)
            bad[field_name] = ["merged.pdf", "x.pdf"] if isinstance(sample[field_name], list) else "merged.pdf"
            with pytest.raises(ValidationError):
                model.model_validate(bad)
        assert collect_upload_filenames(model.model_validate(sample))


def _pipeline_sample(sid: str) -> dict:
    return {
        "docukit_merge_optimize": {"inputs": ["a.pdf", "b.pdf"]},
        "docukit_ocr_page": {"input_file": "a.pdf", "page": 1},
        "docukit_protected_excerpt": {"input_file": "a.pdf", "pages": "1-2", "password": "secret"},
    }[sid]


def test_pipeline_steps_use_only_known_tools_and_keep_user_values():
    ocr = ALL_SPECS["docukit_ocr_page"]
    user_in = ocr.input_cls.model_validate({"input_file": "a.pdf", "page": 4, "language": "eng"})
    step_render, step_ocr = ocr.steps
    render_in = step_render.build_step_input(user_in, {})
    assert render_in.page == 4 and render_in.longest_side == 3500 and render_in.input_file == "a.pdf"
    ocr_in = step_ocr.build_step_input(user_in, {"step_render": "page.png"})
    assert ocr_in.input_file == "page.png" and ocr_in.language == "eng"
