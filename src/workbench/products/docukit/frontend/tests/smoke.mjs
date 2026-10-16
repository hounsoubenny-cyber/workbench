/*
 * Docukit — test de fumée de l'interface (serveur RÉEL + DOM simulé).
 *
 *   cd frontend/tests && npm install && node smoke.mjs
 *
 * Lance `python -m workbench.products.docukit` sur un port libre, charge
 * index.html dans jsdom, exécute app.js et pilote l'interface comme un
 * utilisateur (dépôt de fichiers, réordonnancement, envoi, résultat, erreurs).
 * Prérequis : python3 avec reportlab, qpdf, poppler, tesseract.
 */
import { spawn, execFileSync } from "node:child_process";
import { readFileSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "node:net";
import { JSDOM } from "jsdom";

const here = dirname(fileURLToPath(import.meta.url));
const SRC = join(here, "..", "..", "..", "..", "..");           // dossier « src » du dépôt
const APP_JS = readFileSync(join(here, "..", "app.js"), "utf8");

let passed = 0, failed = 0;
const check = (cond, label) => {
  if (cond) { passed++; console.log(`  ✓ ${label}`); }
  else { failed++; console.log(`  ✗ ${label}`); }
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function waitFor(fn, label, ms = 20000) {
  const end = Date.now() + ms;
  while (Date.now() < end) { try { const v = fn(); if (v) return v; } catch { /* pas prêt */ } await sleep(50); }
  throw new Error(`délai dépassé : ${label}`);
}
const freePort = () => new Promise((res) => {
  const s = createServer().listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => res(p)); });
});

// ─── Serveur ─────────────────────────────────────────────────────────────────
const tmp = mkdtempSync(join(tmpdir(), "docukit-ui-"));
const port = await freePort();
const base = `http://127.0.0.1:${port}`;
const server = spawn("python3", ["-m", "workbench.products.docukit"], {
  cwd: SRC, stdio: ["ignore", "pipe", "pipe"],
  env: { ...process.env, DOCUKIT_PORT: String(port), DOCUKIT_OPEN_BROWSER: "0", DOCUKIT_CONFIG_FILE: join(tmp, "c.toml") },
});
let serverLog = "";
server.stderr.on("data", (d) => { serverLog += d; });
const stop = () => server.kill("SIGTERM");
process.on("exit", stop);

try {
  await waitFor(async () => (await fetch(`${base}/api/status`).catch(() => null))?.ok, "démarrage du serveur").catch(() => {});
  for (let i = 0; i < 100; i++) { if ((await fetch(`${base}/api/status`).catch(() => null))?.ok) break; await sleep(100); }

  // PDF d'exemple (reportlab)
  execFileSync("python3", ["-c", `
from reportlab.pdfgen import canvas
for name, n in (("a", 3), ("b", 2)):
    c = canvas.Canvas("${tmp}/%s.pdf" % name)
    for i in range(n):
        c.setFont("Helvetica", 24); c.drawString(72, 700, "%s PAGE %d" % (name.upper(), i + 1)); c.showPage()
    c.save()
`]);
  const pdfA = readFileSync(join(tmp, "a.pdf")), pdfB = readFileSync(join(tmp, "b.pdf"));

  // ─── DOM ───────────────────────────────────────────────────────────────────
  const html = await (await fetch(`${base}/`)).text();
  const dom = new JSDOM(html, { url: `${base}/`, runScripts: "outside-only", pretendToBeVisual: true });
  const { window } = dom;
  const { document } = window;

  const requests = [];
  const readFile = (file) => new Promise((resolve, reject) => {
    const reader = new window.FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsArrayBuffer(file);
  });
  // fetch de Node, avec conversion du FormData jsdom -> FormData Node.
  window.fetch = async (url, opts = {}) => {
    const target = new URL(url, base);
    requests.push(`${opts.method ?? "GET"} ${target.pathname}`);
    let body = opts.body;
    if (body && body.constructor?.name === "FormData") {
      const nodeForm = new FormData();
      for (const [key, value] of body.entries()) {
        if (value && typeof value === "object" && "name" in value) {
          nodeForm.append(key, new Blob([await readFile(value)]), value.name);
          requests.push(`  upload ${value.name}`);
        } else nodeForm.append(key, value);
      }
      body = nodeForm;
    }
    return fetch(target, { ...opts, body });
  };
  window.URL.createObjectURL = () => "blob:docukit-test";
  window.URL.revokeObjectURL = () => {};

  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const makeFile = (bytes, name) => new window.File([bytes], name, { type: "application/pdf" });
  const drop = (zone, files) => {
    const ev = new window.Event("drop", { bubbles: true, cancelable: true });
    ev.dataTransfer = { files };
    zone.dispatchEvent(ev);
  };
  const submit = () => $("#spec-form").dispatchEvent(new window.Event("submit", { bubbles: true, cancelable: true }));
  const open = async (id) => {
    const previous = $("#spec-form");          // attendre que le formulaire soit REMPLACÉ
    window.location.hash = id;
    await waitFor(() => { const f = $("#spec-form"); return f && f !== previous; }, `formulaire ${id}`);
  };

  // jsdom IGNORE un `null` passé à replaceChildren(), alors que Chrome/Firefox écrivent le
  // TEXTE « null » dans la page : on rend ce cas bruyant pour qu'il ne passe jamais inaperçu.
  const nativeReplace = window.Element.prototype.replaceChildren;
  window.Element.prototype.replaceChildren = function (...nodes) {
    if (nodes.some((n) => n == null || n === false)) {
      throw new Error("replaceChildren a reçu null/false : un vrai navigateur afficherait « null »");
    }
    return nativeReplace.apply(this, nodes);
  };

  window.eval(APP_JS);

  // ─── 1. Accueil ────────────────────────────────────────────────────────────
  console.log("\n▸ Accueil et navigation");
  await waitFor(() => $$(".cat-card").length, "accueil");
  check($$(".cat-card").length === 8, "8 catégories affichées");
  check($$("#nav .nav-item").length === 21, "21 outils dans la navigation");
  check($("#version").textContent === "v1.0.0", "version affichée");
  check($$("#tools-list li").length === 7, "statut des 7 binaires affiché");
  const search = $("#search");
  search.value = "mot de passe";
  search.dispatchEvent(new window.Event("input"));
  check($$("#nav .nav-item").length >= 2 && $$("#nav .nav-item").every((b) => /mot de passe|Protéger|Retirer|protéger/i.test(b.title + b.textContent)),
    "la recherche filtre (accents et casse ignorés)");
  search.value = "zzzz"; search.dispatchEvent(new window.Event("input"));
  check(!!$(".nav-empty"), "message quand rien ne correspond");
  search.value = ""; search.dispatchEvent(new window.Event("input"));

  // ─── 2. Fusion : dépôt, réordonnancement, exécution, résultat ──────────────
  console.log("\n▸ Fusion de deux PDF");
  await open("qpdf_merge");
  check($("#in-inputs").multiple === true, "champ multi-fichiers");
  check(!/\bnull\b|undefined/.test($("#view").textContent), "aucun « null » / « undefined » affiché dans le formulaire");
  drop($(".drop"), [makeFile(pdfA, "rapport.pdf"), makeFile(pdfB, "annexe.pdf")]);
  await waitFor(() => $$("#files-inputs li").length === 2, "2 fichiers listés");
  check($$("#files-inputs .name")[0].textContent === "rapport.pdf", "ordre initial respecté");
  $$("#files-inputs li")[1].querySelector('button[aria-label^="Monter"]').click();
  check($$("#files-inputs .name")[0].textContent === "annexe.pdf", "le bouton ↑ réordonne");
  $$("#files-inputs li")[1].querySelector('button[aria-label^="Monter"]').click();   // retour à l'ordre initial
  requests.length = 0;
  submit();
  await waitFor(() => $("#result-panel .result-ok"), "résultat de la fusion");
  check(requests.includes("  upload file-01.pdf") && requests.includes("  upload file-02.pdf"),
    "les fichiers sont envoyés sous des noms neutres (file-01.pdf, file-02.pdf)");
  check(!requests.some((r) => r.includes("rapport") || r.includes("annexe")), "les noms d'origine ne partent jamais au serveur");
  check($("#result-panel .file-chip").textContent.startsWith("merged.pdf"), "résultat : merged.pdf");
  check($("#result-panel a[download]").getAttribute("download") === "merged.pdf", "lien de téléchargement");
  check(!!$("#result-panel iframe"), "aperçu PDF intégré");
  check(!!$("#result-panel button.btn:not(.btn-primary)"), "bouton « Continuer avec ce fichier »");

  // ─── 3. Validation côté client ─────────────────────────────────────────────
  console.log("\n▸ Validation du formulaire");
  await open("qpdf_extract_pages");
  requests.length = 0;
  submit();
  await sleep(150);
  check($("#err-input_file").hidden === false && $("#err-input_file").textContent.includes("Ajoutez un fichier"),
    "fichier manquant : message sous le champ");
  check(!requests.some((r) => r.includes("job/create")), "aucune requête envoyée tant que le formulaire est invalide");

  await open("pdftotext_extract");
  drop($(".drop"), [makeFile(pdfA, "a.pdf")]);
  await waitFor(() => $$("#files-input_file li").length === 1, "fichier ajouté");
  $("#in-first_page").value = "3"; $("#in-first_page").dispatchEvent(new window.Event("input"));
  $("#in-last_page").value = "2"; $("#in-last_page").dispatchEvent(new window.Event("input"));
  submit(); await sleep(100);
  check($("#err-last_page").textContent.includes("supérieure"), "dernière page < première page : refusé");

  await open("qpdf_protect");
  drop($(".drop"), [makeFile(pdfA, "a.pdf")]);
  await waitFor(() => $$("#files-input_file li").length === 1, "fichier ajouté");
  check($("#in-password").type === "password", "le mot de passe est masqué par défaut");
  submit(); await sleep(100);
  check($("#err-password").textContent.includes("obligatoire"), "mot de passe obligatoire");

  // ─── 4. Sécurité : nom de fichier piégé & type refusé ──────────────────────
  console.log("\n▸ Sécurité de l'affichage");
  await open("qpdf_check");
  drop($(".drop"), [makeFile(pdfA, '<img src=x onerror="window.__pwned=1">.pdf')]);
  await waitFor(() => $$("#files-input_file li").length === 1, "fichier piégé listé");
  check(!$("#files-input_file img") && !window.__pwned, "un nom de fichier HTML est affiché comme texte (aucune injection)");
  check($("#files-input_file .name").textContent.includes("<img"), "… et reste lisible tel quel");
  drop($(".drop"), [new window.File(["x"], "virus.exe")]);
  check($("#err-input_file").textContent.includes("non accepté"), "un fichier .exe est refusé");
  const CODE = APP_JS.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");   // sans commentaires
  check(!/innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(/.test(CODE),
    "app.js n'utilise ni innerHTML, ni insertAdjacentHTML, ni document.write, ni eval");

  // ─── 5. Échec : message clair, journal ouvert ──────────────────────────────
  console.log("\n▸ Échec d'une opération");
  await open("docukit_ocr_page");
  drop($(".drop"), [makeFile(pdfA, "a.pdf")]);
  await waitFor(() => $$("#files-input_file li").length === 1, "fichier ajouté");
  $("#in-page").value = "99"; $("#in-page").dispatchEvent(new window.Event("input"));
  $("#in-language").value = "eng"; $("#in-language").dispatchEvent(new window.Event("change"));
  submit();
  await waitFor(() => $(".banner.error strong")?.textContent.includes("a échoué"), "bandeau d'échec");
  check($(".banner.error").textContent.includes("step_render"), "le message nomme l'étape en échec");
  check(!$(".spinner"), "plus de spinner après l'échec (l'interface ne reste pas bloquée)");
  check($("button[type=submit]").disabled === false, "le bouton Lancer est de nouveau actif");

  // ─── 6. Pipeline réussi : OCR ──────────────────────────────────────────────
  console.log("\n▸ Workflow OCR (pdftoppm → tesseract)");
  $("#in-page").value = "2"; $("#in-page").dispatchEvent(new window.Event("input"));
  submit();
  await waitFor(() => $("#result-panel .result-ok"), "résultat OCR", 60000);
  check($("#result-panel .file-chip").textContent.startsWith("ocr_text.txt"), "résultat : ocr_text.txt");
  const ocrText = $("#result-panel .preview pre")?.textContent ?? "";
  check(/PAGE/.test(ocrText) && /\b2\b/.test(ocrText), `texte reconnu affiché en aperçu (« ${ocrText.trim().slice(0, 30)} »)`);

  // ─── 7. Rendu d'une image ──────────────────────────────────────────────────
  console.log("\n▸ Page → image");
  await open("pdftoppm_render_page");
  drop($(".drop"), [makeFile(pdfA, "a.pdf")]);
  await waitFor(() => $$("#files-input_file li").length === 1, "fichier ajouté");
  submit();
  await waitFor(() => $("#result-panel .result-ok"), "résultat image");
  check($("#result-panel .file-chip").textContent.startsWith("page.png") && !!$("#result-panel .preview img"), "page.png avec aperçu image");

  console.log(`\n${failed ? "✗" : "✓"} ${passed} vérifications réussies, ${failed} échec(s)`);
} catch (err) {
  failed++;
  console.error("\n✗ ERREUR :", err.message);
  if (serverLog) console.error("--- journal serveur ---\n" + serverLog.slice(-1500));
} finally {
  stop();
  writeFileSync(join(tmp, "done"), "");
}
process.exit(failed ? 1 : 0);
