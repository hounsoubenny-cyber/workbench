# 📄 Docukit — boîte à outils PDF & documents

Docukit rend `qpdf`, `poppler`, `tesseract` et `pandoc` utilisables **sans terminal** : fusionner,
extraire, pivoter, protéger par mot de passe, lire un scan (OCR), convertir en Word/Markdown…
Tout se passe **sur l'ordinateur de l'utilisateur** : aucun document n'est envoyé sur Internet.

C'est le deuxième produit construit sur le socle Workbench. Il montre le principe du framework :
**une action = un modèle Pydantic + une fonction qui construit les arguments**. Le formulaire de
l'interface est généré automatiquement à partir du modèle.

## Fonctionnalités (21 outils)

| Catégorie | Outils |
| :--- | :--- |
| 📑 Organiser | Fusionner · Extraire des pages · Supprimer des pages · Inverser l'ordre |
| ✏️ Éditer | Pivoter des pages · Tampon / filigrane (PDF) |
| 🔒 Sécuriser | Protéger par mot de passe (AES-256) · Retirer le mot de passe |
| 🔍 Lire & extraire | Texte du PDF · Page → image PNG/JPEG · Infos du PDF · Liste des images |
| 🧾 OCR | Image → texte · Image → PDF recherchable |
| 🔄 Convertir | Markdown / HTML / Word / OpenDocument / EPUB / reST / LaTeX |
| 🛠️ Réparer & optimiser | Vérifier l'intégrité · Réparer · Optimiser (sans perte) |
| ⚡ Workflows | Fusionner puis optimiser · Lire une page scannée (OCR) · Extrait protégé |

## Installation

Binaires requis (l'interface indique lesquels manquent, et grise les outils concernés) :

```bash
# Debian / Ubuntu
sudo apt install qpdf poppler-utils tesseract-ocr tesseract-ocr-fra pandoc
# macOS
brew install qpdf poppler tesseract tesseract-lang pandoc
```

> ⚠️ **pandoc** : le paquet d'Ubuntu/Debian ne sait pas produire `docx`/`odt`/`epub` en mode
> `--sandbox` (voir *Sécurité*). Installez le [binaire officiel](https://pandoc.org/installing.html)
> pour ces trois formats ; les autres fonctionnent partout.

```bash
pip install -r src/workbench/products/docukit/requirements.txt
pip install -e .
python -m workbench.products.docukit        # ouvre http://127.0.0.1:<port libre>
```

| Variable | Rôle | Défaut |
| :--- | :--- | :--- |
| `DOCUKIT_HOST` | interface d'écoute | `127.0.0.1` |
| `DOCUKIT_PORT` | port (`0` = port libre) | `0` |
| `DOCUKIT_MAX_UPLOAD_MB` | taille maximale d'une requête | `200` |
| `DOCUKIT_CONFIG_FILE` | fichier de config TOML | dossier de config de l'utilisateur |
| `DOCUKIT_ALLOWED_HOSTS` | hôtes `Host` acceptés en plus du local (si `HOST` n'est pas local) | — |
| `DOCUKIT_OPEN_BROWSER` | ouvrir le navigateur au démarrage | `1` |

Le lanceur imprime `WORKBENCH_PORT=<port>` (même protocole que Mediakit) pour une coquille Tauri.

## Ajouter une action

Exemple complet : « Compter les pages » (`qpdf --show-npages`).

```python
# specs/common.py → dans la classe Out :  PAGE_COUNT = "pages.txt"
# specs/qpdf/actions/actions_maintenance.py
class PageCountInput(PdfSourceInput):          # le formulaire = ce modèle
    pass

count_pages_spec = QpdfSpec[PageCountInput](
    id="qpdf_count_pages",
    label="Compter les pages",
    description="Indique le nombre de pages du document.",
    input_cls=PageCountInput,
    output_filename_template=Out.PAGE_COUNT,
    capture_stdout=True,                       # stdout → fichier de sortie
    build_args=lambda u: [flag("--show-npages"), PathArg(value=u.input_file, must_exist=True)],
)
# puis l'ajouter dans `ordered(...)` de la catégorie, et mettre à jour le compte attendu dans tests/test_unit.py
```

Aucune ligne de JavaScript à écrire : l'interface lit `/api/spec/<id>/info`.

## Architecture

```
docukit/
├── api/            app.py (fabrique FastAPI) · env.py · limits.py · run_api.py
├── specs/          common.py (validateurs) · base.py · qpdf/ poppler/ tesseract/ pandoc/ · pipelines.py · utils.py (catalogue)
├── dk_utils/       files.py (type réel par signature) · tools.py (binaires, langues OCR, sonde pandoc)
├── frontend/       index.html · style.css · app.js (JS pur, sans build) · tests/smoke.mjs
└── tests/          unitaires · API/sécurité · intégration (vrais binaires)
```

## Sécurité

Docukit ouvre des documents **non fiables** : chaque entrée est traitée comme hostile.

| Menace | Défense |
| :--- | :--- |
| Injection d'options (`--password=…`, `--evil`) | Arguments **typés** (jamais de shell) ; pages/mots de passe validés par expression régulière avant d'être passés ; `attached_option` valide la chaîne finale |
| Fichier déguisé (`virus.exe` renommé `.pdf`) | Type réel contrôlé **par signature**, pas par extension |
| Écraser un fichier de sortie | Les noms de sortie (`merged.pdf`…) sont **réservés** : refusés comme noms d'upload |
| pandoc : lecture de fichier local / SSRF via `![x](/etc/passwd)` | `--sandbox` **toujours** ; s'il est incompatible avec le format demandé : refus explicite, jamais de repli |
| Page PDF géante (bombe de rendu) | `pdftoppm -scale-to` borne le plus grand côté (≤ 6000 px) quelle que soit la page |
| Page web malveillante → `127.0.0.1` (CSRF, DNS rebinding, WebSocket cross-site) | `LocalOnlyGuard` : `Host` et `Origin` doivent être locaux |
| Drapeaux libres via le mode manuel | `enable_advanced_jobs=False` |
| XSS dans l'interface | CSP stricte (aucun script/style inline), DOM sans `innerHTML`, aperçus texte non rendus, noms de fichiers d'origine jamais envoyés |
| Upload géant | Plafond (Content-Length **et** flux réel) → `413` |
| Fuite de secrets | Les mots de passe n'apparaissent ni dans les logs, ni dans `job_result`, ni dans les erreurs |

**Limites connues**
- Les mots de passe passent par la ligne de commande de `qpdf` : visibles par les *autres utilisateurs locaux* via `ps`.
  Acceptable sur un poste personnel ; **à ne pas utiliser** sur un serveur partagé multi-utilisateurs.
- Le moteur du socle ne cherche les binaires que dans `/usr/local/bin`, `/usr/bin`, `/bin` (Linux/macOS).
- L'OCR traite **une page** à la fois ; seuls les modèles de langue installés sont proposés.

## Tests

```bash
pip install -r src/workbench/products/docukit/requirements-dev.txt
python -m pytest src/workbench/products/docukit          # unitaires + API + vrais binaires (sautés si absents)
cd src/workbench/products/docukit/frontend/tests && npm install && node smoke.mjs   # interface (jsdom)
```

## Licence

Produit propriétaire — voir [`LICENSE`](LICENSE).
