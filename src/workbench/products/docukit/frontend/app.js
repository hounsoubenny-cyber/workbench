/*
 * Docukit — interface.
 *
 * JavaScript pur : aucune dépendance, aucun build. Les FORMULAIRES sont
 * générés à partir des schémas Pydantic exposés par l'API (`/api/spec/<id>/info`) :
 * ajouter une action côté Python = un nouveau formulaire ici, sans toucher
 * à ce fichier.
 *
 * Sécurité (CSP stricte : pas de script ni de style inline) :
 *  - le DOM est construit avec `textContent` / `createTextNode` — jamais
 *    d'`innerHTML` avec une donnée externe ;
 *  - les aperçus de texte (y compris HTML) sont affichés comme TEXTE, jamais rendus ;
 *  - les fichiers téléversés sont renommés (source.pdf, file-01.pdf…) : le nom
 *    d'origine n'est jamais envoyé au serveur.
 */
"use strict";

const API = "/api";

// ─── Types de fichiers acceptés, par famille d'outil ─────────────────────────
const KINDS = {
  pdf: { label: "PDF", accept: ".pdf,application/pdf", exts: ["pdf"], def: "pdf" },
  image: {
    label: "Image (PNG, JPEG, TIFF, BMP, GIF, WebP)",
    accept: "image/*,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.gif,.webp",
    exts: ["png", "jpg", "jpeg", "tif", "tiff", "bmp", "gif", "webp"], def: "png",
  },
  doc: {
    label: "Document (Markdown, texte, HTML, Word, OpenDocument, EPUB, reST, LaTeX)",
    accept: ".md,.markdown,.txt,.html,.htm,.docx,.odt,.epub,.rst,.tex",
    exts: ["md", "markdown", "txt", "html", "htm", "docx", "odt", "epub", "rst", "tex"], def: "md",
  },
};
const uploadKind = (specId) =>
  specId.startsWith("tesseract_") ? "image" : specId === "pandoc_convert" ? "doc" : "pdf";

const PANDOC_FROM_EXT = {
  md: "markdown", markdown: "markdown", txt: "markdown", html: "html", htm: "html",
  docx: "docx", odt: "odt", epub: "epub", rst: "rst", tex: "latex",
};
const OFFICE_FORMATS = ["docx", "odt", "epub"];

// ─── Libellés ────────────────────────────────────────────────────────────────
const FIELD_TITLES = {
  input_file: "Document", inputs: "Documents à fusionner (dans l'ordre)",
  stamp_file: "PDF du tampon ou du filigrane", pages: "Pages", angle: "Rotation",
  mode: "Position du tampon", password: "Mot de passe", owner_password: "Mot de passe propriétaire (facultatif)",
  language: "Langue du texte", page_mode: "Disposition du texte", from_format: "Format d'origine",
  to_format: "Format de sortie", first_page: "Première page", last_page: "Dernière page",
  page: "Page", longest_side: "Taille de l'image (pixels)", format: "Format de l'image",
};
const FORMAT_LABELS = {
  markdown: "Markdown", gfm: "Markdown (GitHub)", html: "HTML", docx: "Word (.docx)",
  odt: "OpenDocument (.odt)", epub: "EPUB", rst: "reStructuredText", latex: "LaTeX", plain: "Texte brut",
};
const OPTION_LABELS = {
  angle: { 90: "90° (quart de tour vers la droite)", 180: "180° (demi-tour)", 270: "270° (quart de tour vers la gauche)" },
  mode: { overlay: "Par-dessus le contenu", underlay: "Derrière le contenu" },
  language: { fra: "Français", eng: "Anglais", "fra+eng": "Français + anglais", "eng+fra": "Anglais + français" },
  page_mode: { 3: "Automatique", 4: "Une seule colonne", 6: "Un seul bloc de texte", 11: "Texte épars" },
  format: { png: "PNG", jpeg: "JPEG" },
  from_format: FORMAT_LABELS, to_format: FORMAT_LABELS,
};

// ─── Utilitaires ─────────────────────────────────────────────────────────────
const $ = (sel, root = document) => root.querySelector(sel);

/** Crée un élément. Les enfants chaîne deviennent des nœuds texte (jamais du HTML). */
function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value === false || value == null) continue;
    if (key === "class") el.className = value;
    else if (key.startsWith("on") && typeof value === "function") el.addEventListener(key.slice(2), value);
    else if (["value", "checked", "disabled", "multiple", "open"].includes(key)) el[key] = value;
    else if (value === true) el.setAttribute(key, "");
    else el.setAttribute(key, String(value));
  }
  for (const child of children.flat()) {
    if (child == null || child === false) continue;
    el.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return el;
}

const normalize = (s) => s.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
const prettify = (name) => { const s = name.replace(/_/g, " "); return s[0].toUpperCase() + s.slice(1); };
const extOf = (name) => { const m = /\.([a-z0-9]{1,5})$/i.exec(name); return m ? m[1].toLowerCase() : ""; };

function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(0)} Ko`;
  return `${(bytes / 1024 ** 2).toFixed(1)} Mo`;
}
const fmtElapsed = (ms) => {
  const s = Math.floor(ms / 1000);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
};

function announce(message) { const live = $("#live"); if (live) live.textContent = message; }

let toastTimer = null;
function toast(message) {
  $(".toast")?.remove();
  document.body.append(h("div", { class: "toast", role: "status" }, message));
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $(".toast")?.remove(), 4000);
}

// ─── Appels API ──────────────────────────────────────────────────────────────
class ApiError extends Error {}

/** Message lisible depuis une réponse d'erreur (formats : {detail:{message}}, {message}, {detail:"…"}). */
function errorMessage(body, status) {
  const raw = body?.detail?.message ?? body?.message ?? (typeof body?.detail === "string" ? body.detail : null);
  if (raw) return String(raw).replace(/Value error, /g, "");
  return status === 413 ? "Fichier trop volumineux." : `Erreur ${status}`;
}

async function api(path, options) {
  let response;
  try {
    response = await fetch(API + path, options);
  } catch {
    throw new ApiError("Impossible de joindre Docukit. L'application est-elle toujours lancée ?");
  }
  let body = null;
  try { body = await response.json(); } catch { /* corps non JSON */ }
  if (!response.ok) throw new ApiError(errorMessage(body, response.status));
  return body;
}

// ─── État ────────────────────────────────────────────────────────────────────
const state = {
  catalog: null, tools: {}, specId: null, schema: null,
  values: {}, files: {}, errors: {}, run: null, carry: null,
};
const spec = () => state.catalog.specs[state.specId];
const category = (id) => state.catalog.categories.find((c) => c.id === id);

/** Outils (binaires) manquants pour la spec courante. */
function missingTools(s = spec()) {
  return s.tools.filter((t) => state.tools[t] && !state.tools[t].find);
}

/** Problème propre à la sélection courante (pandoc / OCR), sinon null. */
function selectionProblem() {
  if (state.specId === "pandoc_convert" && OFFICE_FORMATS.includes(state.values.to_format)
      && state.tools.pandoc?.find && state.tools.pandoc.office_output === false) {
    return "Cette installation de pandoc ne peut pas produire ce format en mode sécurisé. "
      + "Installez le binaire officiel de pandoc (pandoc.org/installing.html) ou choisissez un format texte.";
  }
  return null;
}

// ─── Navigation ──────────────────────────────────────────────────────────────
function renderNav() {
  const query = normalize($("#search").value.trim());
  const nav = $("#nav");
  nav.replaceChildren();
  let shown = 0;
  for (const cat of state.catalog.categories) {
    const items = cat.specs.filter((id) => {
      const s = state.catalog.specs[id];
      return !query || normalize(`${s.label} ${s.description}`).includes(query);
    });
    if (!items.length) continue;
    shown += items.length;
    nav.append(h("details", { class: "nav-cat", open: true },
      h("summary", {}, h("span", { class: "chev", "aria-hidden": "true" }, "▶"), h("span", {}, `${cat.icon} ${cat.label}`)),
      items.map((id) => {
        const s = state.catalog.specs[id];
        const unavailable = missingTools(s).length > 0;
        return h("button", {
          type: "button", class: `nav-item${unavailable ? " unavailable" : ""}`,
          "aria-current": id === state.specId ? "true" : "false",
          title: unavailable ? "Un outil requis n'est pas installé" : s.description,
          onclick: () => selectSpec(id),
        }, unavailable ? `⚠ ${s.label}` : s.label);
      })));
  }
  if (!shown) nav.append(h("p", { class: "nav-empty" }, "Aucun outil ne correspond."));
}

function renderTools() {
  const list = $("#tools-list");
  list.replaceChildren(...Object.entries(state.tools).map(([name, t]) =>
    h("li", { title: t.find ? `${name} ${t.version ?? ""}` : t.install },
      h("span", { class: t.find ? "" : "tool-ko", "aria-hidden": "true" }, t.find ? "✓" : "✕"),
      h("span", { class: t.find ? "" : "tool-ko" }, name),
      t.find ? null : h("span", { class: "sr-only" }, "non installé"))));
}

function renderHome() {
  state.specId = null;
  history.replaceState(null, "", location.pathname);
  renderNav();
  $("#view").replaceChildren(h("section", { class: "hero" },
    h("h1", { id: "spec-title", tabindex: "-1" }, "Que voulez-vous faire ?"),
    h("p", {}, "Vos documents restent sur votre ordinateur : rien n'est envoyé sur Internet. Choisissez une action."),
    h("div", { class: "cards" }, state.catalog.categories.map((cat) =>
      h("div", { class: "cat-card" },
        h("div", { class: "ico", "aria-hidden": "true" }, cat.icon),
        h("h3", {}, cat.label),
        h("p", {}, cat.description),
        h("ul", { class: "card-links" }, cat.specs.map((id) =>
          h("li", {}, h("button", { type: "button", class: "nav-item card-link", onclick: () => selectSpec(id) },
            state.catalog.specs[id].label)))))))));
}

// ─── Sélection d'un outil ────────────────────────────────────────────────────
async function selectSpec(id) {
  cleanupRun();
  let info;
  try {
    info = await api(`/spec/${encodeURIComponent(id)}/info`);
    if (!info.success) throw new ApiError("Outil introuvable.");
  } catch (err) {
    return toast(err.message);
  }
  state.specId = id;
  state.schema = info.input;
  state.values = {}; state.files = {}; state.errors = {}; state.run = null;
  for (const [name, f] of Object.entries(state.schema)) {
    state.values[name] = f.default ?? (f.type === "boolean" ? false : f.type === "integer" ? 0 : "");
  }
  applyCarry();
  history.replaceState(null, "", `#${id}`);
  document.body.classList.remove("menu-open");
  $(".sidebar").classList.remove("open");
  renderNav();
  renderSpec();
  $("#spec-title")?.focus();
  announce(spec().label);
}

/** Pré-remplit le 1er champ de fichier avec le résultat précédent (enchaîner deux outils). */
function applyCarry() {
  if (!state.carry) return;
  const first = Object.entries(state.schema).find(([, f]) => f.is_upload);
  if (!first) return;
  const kind = KINDS[uploadKind(state.specId)];
  if (!kind.exts.includes(extOf(state.carry.name))) return;
  state.files[first[0]] = [new File([state.carry.blob], state.carry.name, { type: state.carry.blob.type })];
}

// ─── Formulaire ──────────────────────────────────────────────────────────────
function renderSpec() {
  const s = spec();
  const cat = category(s.category);
  const missing = missingTools(s);
  const view = $("#view");
  view.replaceChildren(
    h("div", { class: "crumb" }, h("button", { type: "button", class: "btn", onclick: renderHome }, "← Accueil"),
      ` ${cat.icon} ${cat.label}`),
    h("header", { class: "spec-head" },
      h("h1", { id: "spec-title", tabindex: "-1" }, s.label), h("p", {}, s.description)),
    missing.length ? h("div", { class: "banner error", role: "alert" },
      h("strong", {}, "Outil manquant sur cet ordinateur"),
      missing.map((t) => h("div", {}, `${t} — ${state.tools[t].install}`))) : null,
    h("form", { class: "panel", novalidate: true, id: "spec-form", onsubmit: (e) => { e.preventDefault(); submit(); } },
      h("div", { class: "fields" }, Object.entries(state.schema).map(([name, f]) => renderField(name, f))),
      h("div", { class: "actions", id: "form-actions" })),
    h("div", { id: "run-area" }),
  );
  refreshActions();
}

function fieldWrap(name, f, control, { showTitle = true } = {}) {
  const hint = f.description && showTitle ? h("p", { class: "hint", id: `hint-${name}` }, f.description) : null;
  return h("div", { class: "field", id: `field-${name}` },
    showTitle ? h("label", { for: `in-${name}`, class: f.type.startsWith("list") || f.is_upload ? "label" : "" },
      FIELD_TITLES[name] ?? prettify(name), f.required && !f.is_upload ? h("span", { class: "req", "aria-hidden": "true" }, " *") : null) : null,
    control, hint, h("p", { class: "error", id: `err-${name}`, role: "alert", hidden: true }));
}

function renderField(name, f) {
  if (f.is_upload) return fieldWrap(name, f, renderUpload(name, f));

  if (f.type === "boolean") {
    const box = h("input", { type: "checkbox", id: `in-${name}`, checked: !!state.values[name],
      onchange: (e) => { state.values[name] = e.target.checked; refreshActions(); } });
    return h("div", { class: "field", id: `field-${name}` },
      h("label", { class: "check", for: `in-${name}` }, box, h("span", {}, f.description || prettify(name))));
  }

  if (f.type === "enum") {
    const labels = OPTION_LABELS[name] ?? {};
    const select = h("select", { class: "input", id: `in-${name}`, onchange: (e) => { state.values[name] = e.target.value; refreshActions(); } },
      f.choices.map((c) => {
        const missingLang = name === "language" && state.tools.tesseract?.languages
          && c.split("+").some((l) => !state.tools.tesseract.languages.includes(l));
        return h("option", { value: c, disabled: !!missingLang },
          `${labels[c] ?? c}${missingLang ? " (non installée)" : ""}`);
      }));
    select.value = state.values[name];
    return fieldWrap(name, f, select);
  }

  const isPassword = /password/i.test(name);
  const input = h("input", {
    class: "input", id: `in-${name}`, type: isPassword ? "password" : f.type === "integer" ? "number" : "text",
    value: state.values[name] ?? "", autocomplete: isPassword ? "new-password" : "off", spellcheck: "false",
    min: f.constraints?.ge, max: f.constraints?.le, maxlength: f.constraints?.max_length,
    "aria-describedby": `hint-${name}`,
    oninput: (e) => { state.values[name] = e.target.value; },
  });
  if (!isPassword) return fieldWrap(name, f, input);
  const toggle = h("button", { type: "button", class: "btn", "aria-pressed": "false",
    onclick: () => { const show = input.type === "password"; input.type = show ? "text" : "password";
      toggle.textContent = show ? "Masquer" : "Afficher"; toggle.setAttribute("aria-pressed", String(show)); } }, "Afficher");
  return fieldWrap(name, f, h("div", { class: "row" }, input, toggle));
}

// ─── Fichiers ────────────────────────────────────────────────────────────────
function renderUpload(name, f) {
  const multi = f.type.startsWith("list");
  const kind = KINDS[uploadKind(state.specId)];
  const input = h("input", { type: "file", id: `in-${name}`, accept: kind.accept, multiple: multi,
    "aria-describedby": `hint-${name}`, onchange: (e) => { addFiles(name, [...e.target.files]); e.target.value = ""; } });
  const zone = h("label", { class: "drop", for: `in-${name}`,
    ondragover: (e) => { e.preventDefault(); zone.classList.add("over"); },
    ondragleave: () => zone.classList.remove("over"),
    ondrop: (e) => { e.preventDefault(); zone.classList.remove("over"); addFiles(name, [...e.dataTransfer.files]); } },
    h("strong", {}, multi ? "Choisissez ou déposez vos fichiers" : "Choisissez ou déposez un fichier"),
    h("div", {}, kind.label), input);
  return h("div", {}, zone, h("ul", { class: "files", id: `files-${name}`, "aria-label": "Fichiers choisis" }));
}

function addFiles(name, incoming) {
  const f = state.schema[name];
  const multi = f.type.startsWith("list");
  const kind = KINDS[uploadKind(state.specId)];
  const accepted = incoming.filter((file) => kind.exts.includes(extOf(file.name)) || (kind === KINDS.image && file.type.startsWith("image/")));
  if (accepted.length < incoming.length) setError(name, `Type de fichier non accepté (attendu : ${kind.label}).`);
  else setError(name, "");
  if (!accepted.length) return;

  const current = multi ? (state.files[name] ?? []) : [];
  for (const file of accepted) {
    if (!current.some((c) => c.name === file.name && c.size === file.size)) current.push(file);
  }
  const max = f.constraints?.max_length;
  state.files[name] = max ? current.slice(0, max) : current;

  // pandoc : devine le format d'origine d'après l'extension.
  if (state.specId === "pandoc_convert" && name === "input_file") {
    const guess = PANDOC_FROM_EXT[extOf(accepted[0].name)];
    const select = $("#in-from_format");
    if (guess && select) { select.value = guess; state.values.from_format = guess; }
  }
  refreshFiles(name);
  refreshActions();
}

function refreshFiles(name) {
  const list = $(`#files-${name}`);
  if (!list) return;
  const files = state.files[name] ?? [];
  const multi = state.schema[name].type.startsWith("list");
  const move = (i, d) => { const a = state.files[name]; [a[i], a[i + d]] = [a[i + d], a[i]]; refreshFiles(name); };
  list.replaceChildren(...files.map((file, i) => h("li", {},
    multi ? h("span", { class: "order" }, `${i + 1}.`) : null,
    h("span", { class: "name", title: file.name }, file.name),
    h("span", { class: "size" }, fmtSize(file.size)),
    multi ? h("button", { type: "button", class: "icon-btn", disabled: i === 0, "aria-label": `Monter ${file.name}`, onclick: () => move(i, -1) }, "↑") : null,
    multi ? h("button", { type: "button", class: "icon-btn", disabled: i === files.length - 1, "aria-label": `Descendre ${file.name}`, onclick: () => move(i, 1) }, "↓") : null,
    h("button", { type: "button", class: "icon-btn", "aria-label": `Retirer ${file.name}`,
      onclick: () => { files.splice(i, 1); refreshFiles(name); refreshActions(); } }, "✕"))));
}

/** Nom envoyé au serveur : jamais le nom d'origine (voir en-tête du fichier). */
function uploadName(field, index, file) {
  const kind = KINDS[uploadKind(state.specId)];
  let ext = extOf(file.name);
  if (!kind.exts.includes(ext)) ext = kind.def;
  const base = field === "inputs" ? `file-${String(index + 1).padStart(2, "0")}`
    : field === "input_file" ? "source" : field.replace(/_file$/, "").replace(/[^a-z0-9]+/gi, "-");
  return `${base}.${ext}`;
}

// ─── Validation & envoi ──────────────────────────────────────────────────────
function setError(name, message) {
  const el = $(`#err-${name}`);
  if (!el) return;
  el.textContent = message;
  el.hidden = !message;
  if (message) state.errors[name] = message; else delete state.errors[name];
}

function validate() {
  state.errors = {};
  let firstInvalid = null;
  const fail = (name, message) => { setError(name, message); firstInvalid ??= name; };
  for (const [name, f] of Object.entries(state.schema)) {
    setError(name, "");
    const value = state.values[name];
    if (f.is_upload) {
      const count = (state.files[name] ?? []).length;
      const min = f.constraints?.min_length ?? 1;
      if (count < min) fail(name, min > 1 ? `Ajoutez au moins ${min} fichiers.` : "Ajoutez un fichier.");
    } else if (f.type === "integer") {
      const n = Number(value);
      if (value === "" || !Number.isInteger(n)) fail(name, "Entrez un nombre entier.");
      else if (f.constraints?.ge != null && n < f.constraints.ge) fail(name, `Au minimum ${f.constraints.ge}.`);
      else if (f.constraints?.le != null && n > f.constraints.le) fail(name, `Au maximum ${f.constraints.le}.`);
    } else if (f.type === "string" && f.required && !String(value).trim()) {
      fail(name, "Ce champ est obligatoire.");
    }
  }
  const { first_page: first, last_page: last } = state.values;
  if (!state.errors.last_page && state.schema.last_page && Number(last) > 0 && Number(last) < Number(first)) {
    fail("last_page", "La dernière page doit être supérieure ou égale à la première.");
  }
  if (firstInvalid) $(`#field-${firstInvalid} input, #field-${firstInvalid} select`)?.focus();
  return !firstInvalid;
}

function collectInput() {
  const input = {};
  const uploads = [];
  for (const [name, f] of Object.entries(state.schema)) {
    if (f.is_upload) {
      const files = state.files[name] ?? [];
      const names = files.map((file, i) => uploadName(name, i, file));
      input[name] = f.type.startsWith("list") ? names : names[0];
      files.forEach((file, i) => uploads.push([names[i], file]));
    } else if (f.type === "integer") input[name] = Number(state.values[name]);
    else if (f.type === "boolean") input[name] = !!state.values[name];
    else input[name] = state.values[name];
  }
  return { input, uploads };
}

function refreshActions() {
  const box = $("#form-actions");
  if (!box) return;
  const busy = !!state.run?.active;
  const problem = selectionProblem();
  const blocked = busy || missingTools().length > 0 || !!problem;
  box.replaceChildren(
    h("button", { type: "submit", class: "btn btn-primary", disabled: blocked }, busy ? "En cours…" : "Lancer"),
    problem ? h("div", { class: "banner warn", role: "status" }, problem) : null);
}

async function submit() {
  if (state.run?.active || !validate()) return;
  const { input, uploads } = collectInput();
  const body = new FormData();
  body.append("data", JSON.stringify({ id: state.specId, user_input: input, timeout: 300 }));
  for (const [name, file] of uploads) body.append("files", file, name);

  const run = state.run = { active: true, phase: "upload", t0: Date.now(), logs: [], result: null, error: null, ws: null };
  refreshActions();
  renderRun();
  announce("Envoi des fichiers…");
  try {
    const job = await api("/job/create", { method: "POST", body });
    if (!job?.job_id) throw new ApiError(errorMessage(job, 400));   // ex. trop de jobs simultanés
    Object.assign(run, { phase: "running", jobId: job.job_id, workdir: job.workdir, outputFiles: job.output_files });
    renderRun();
    watchJob(run);
  } catch (err) {
    run.active = false;
    run.error = { message: err.message };
    finishRun(run);
  }
}

// ─── Suivi du job ────────────────────────────────────────────────────────────
function watchJob(run, attempt = 0) {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}${API}/job/ws/logs?job_id=${encodeURIComponent(run.jobId)}`);
  run.ws = ws;
  let ended = false;
  ws.onmessage = (event) => {
    let msg;
    try { msg = JSON.parse(event.data); } catch { return; }
    if (msg.type === "run_log") appendLog(run, msg.text, msg.stream === "stderr");
    else if (msg.type === "job_result") run.result = msg.result;
    else if (msg.type === "job_error") run.error = msg;
    else if (msg.type === "job_end") { ended = true; ws.close(); finishRun(run); }
  };
  ws.onclose = () => { if (!ended && run.active) recover(run, attempt); };
}

/** WebSocket coupé avant la fin : on interroge le statut puis on se reconnecte (le serveur rejoue les messages). */
async function recover(run, attempt) {
  if (attempt >= 2) {
    run.error = { message: "Connexion au serveur perdue avant la fin de l'opération." };
    return finishRun(run);
  }
  for (let i = 0; i < 40 && run.active; i++) {
    await new Promise((r) => setTimeout(r, 750));
    try {
      const { status } = await api(`/job/status?job_id=${encodeURIComponent(run.jobId)}`);
      if (status !== "running") break;
    } catch { /* serveur momentanément injoignable */ }
  }
  if (run.active) watchJob(run, attempt + 1);
}

function appendLog(run, text, isError) {
  if (!text) return;
  run.logs.push({ text, isError });
  if (run.logs.length > 500) run.logs.shift();
  const box = $("#logbox");
  if (box) {
    box.append(h("span", { class: isError ? "err" : "" }, text.endsWith("\n") ? text : `${text}\n`));
    box.scrollTop = box.scrollHeight;
  }
}

async function stopJob() {
  const run = state.run;
  if (!run?.jobId) return;
  try { await api(`/job/stop?job_id=${encodeURIComponent(run.jobId)}`); } catch { /* le job a peut-être déjà fini */ }
  run.error = { message: "Opération arrêtée." };
  finishRun(run);
}

function cleanupRun() {
  const run = state.run;
  if (run?.ws) { run.ws.onclose = null; run.ws.close(); }
  if (run?.timer) clearInterval(run.timer);
  if (run?.blobUrl) URL.revokeObjectURL(run.blobUrl);
  if (run) run.active = false;
}

// ─── Affichage de l'exécution et du résultat ────────────────────────────────
function renderRun() {
  const run = state.run;
  const area = $("#run-area");
  if (!area || !run) return;
  if (!run.active) return;
  clearInterval(run.timer);
  const timer = h("span", { class: "timer", "aria-hidden": "true" }, fmtElapsed(Date.now() - run.t0));
  run.timer = setInterval(() => { timer.textContent = fmtElapsed(Date.now() - run.t0); }, 500);
  area.replaceChildren(h("section", { class: "panel", "aria-busy": "true" },
    h("div", { class: "run-head" },
      h("span", { class: "spinner", "aria-hidden": "true" }),
      h("strong", {}, run.phase === "upload" ? "Envoi des fichiers…" : "Traitement en cours…"),
      timer,
      run.jobId ? h("button", { type: "button", class: "btn btn-danger", onclick: stopJob }, "Arrêter") : null),
    h("details", { class: "log" }, h("summary", {}, "Journal d'exécution"), h("pre", { class: "logbox", id: "logbox" }))));
}

async function finishRun(run) {
  if (state.run !== run) return;
  run.active = false;
  clearInterval(run.timer);
  refreshActions();
  const area = $("#run-area");
  const ok = run.result?.success === true && !run.error;
  const logs = h("details", { class: "log", open: !ok && run.logs.length > 0 },
    h("summary", {}, "Journal d'exécution"),
    h("pre", { class: "logbox" }, run.logs.map((l) => h("span", { class: l.isError ? "err" : "" }, l.text.endsWith("\n") ? l.text : `${l.text}\n`))));

  if (!ok) {
    const stderr = run.logs.filter((l) => l.isError).map((l) => l.text).join("").trim();
    const reason = run.error?.message
      ?? (run.result?.stderr || stderr
        ? `L'outil a signalé une erreur${run.result?.returncode != null ? ` (code ${run.result.returncode})` : ""}.`
        : "L'opération a échoué.");
    area.replaceChildren(h("section", { class: "panel" },
      h("div", { class: "banner error", role: "alert" }, h("strong", {}, "L'opération a échoué"), reason),
      run.result?.stderr ? h("pre", { class: "logbox" }, String(run.result.stderr).trim()) : null, logs));
    announce("L'opération a échoué");
    return;
  }

  const last = run.outputFiles?.find((f) => f.last);
  const name = last?.file || run.result?.[last?.id];
  area.replaceChildren(h("section", { class: "panel", id: "result-panel" },
    h("div", { class: "run-head" }, h("span", { class: "spinner", "aria-hidden": "true" }), h("strong", {}, "Préparation du résultat…"))));
  try {
    const response = await fetch(`${API}/download?workdir=${encodeURIComponent(run.workdir)}&path=${encodeURIComponent(name)}`);
    if (!response.ok) throw new ApiError("Le fichier résultat est introuvable.");
    const blob = await response.blob();
    run.blobUrl = URL.createObjectURL(blob);
    await showResult(run, name, blob, logs);
    announce("Opération terminée");
  } catch (err) {
    area.replaceChildren(h("section", { class: "panel" }, h("div", { class: "banner error", role: "alert" }, err.message), logs));
  }
}

const PREVIEW_TEXT = new Set(["txt", "md", "html", "rst"]);

async function showResult(run, name, blob, logs) {
  const ext = extOf(name);
  let preview = null;
  if (ext === "pdf") {
    preview = h("iframe", { src: run.blobUrl, title: `Aperçu de ${name}` });
  } else if (["png", "jpg", "jpeg"].includes(ext)) {
    preview = h("img", { src: run.blobUrl, alt: `Aperçu de ${name}` });
  } else if (PREVIEW_TEXT.has(ext)) {
    const text = await blob.slice(0, 200_000).text();
    preview = h("pre", {}, text || "(fichier vide)");   // affiché comme TEXTE, même pour .html
  }
  const carryBtn = h("button", { type: "button", class: "btn", onclick: () => {
    state.carry = { blob, name };
    toast("Fichier prêt : choisissez l'outil suivant dans la liste.");
    $(".sidebar").classList.add("open");
    $("#search").focus();
  } }, "Continuer avec ce fichier ▸");

  $("#run-area").replaceChildren(h("section", { class: "panel", id: "result-panel" },
    h("div", { class: "result-ok" }, "✓ Terminé"),
    h("div", { class: "actions" },
      h("span", { class: "file-chip" }, name, h("small", {}, fmtSize(blob.size))),
      h("a", { class: "btn btn-primary", href: run.blobUrl, download: name }, "⬇ Télécharger"),
      carryBtn),
    preview ? h("div", { class: "preview" }, preview) : h("p", { class: "preview-note" }, "Pas d'aperçu pour ce format : téléchargez le fichier."),
    logs));
  $("#result-panel").scrollIntoView?.({ block: "nearest", behavior: "smooth" });
}

// ─── Démarrage ───────────────────────────────────────────────────────────────
async function init() {
  $("#search").addEventListener("input", renderNav);
  $("#menu-toggle").addEventListener("click", () => {
    const open = $(".sidebar").classList.toggle("open");
    $("#menu-toggle").setAttribute("aria-expanded", String(open));
  });
  window.addEventListener("hashchange", () => {
    const id = location.hash.slice(1);
    if (id && id !== state.specId && state.catalog?.specs[id]) selectSpec(id);
  });
  try {
    [state.catalog, state.tools] = await Promise.all([api("/catalog"), api("/tools")]);
  } catch (err) {
    $("#view").replaceChildren(h("div", { class: "banner error", role: "alert" }, err.message));
    return;
  }
  $("#version").textContent = `v${state.catalog.product.version}`;
  renderTools();
  const wanted = location.hash.slice(1);
  if (wanted && state.catalog.specs[wanted]) await selectSpec(wanted);
  else renderHome();
}

init();
