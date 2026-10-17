# Tests de Mediakit

```bash
pip install -r src/workbench/products/docukit/requirements-dev.txt python-magic
python -m pytest src/workbench/products/mediakit      # ≈ 2 min : exécute les 83 actions et 17 pipelines pour de vrai
python -m pytest src/workbench/products/mediakit/tests/test_catalog.py   # < 1 s, aucun binaire requis
```

| Fichier | Contenu | Binaires |
| :--- | :--- | :--- |
| `test_catalog.py` | cohérence des 100 specs ; **propriété** : toute valeur offerte par un pipeline doit produire des entrées valides pour chaque étape | aucun |
| `test_utils.py` | détection de type (libmagic), texte de filigrane, régression `validate_args` | ffmpeg (médias) |
| `test_actions_real.py` | **chaque action est exécutée** ; le fichier produit est relu par `ffprobe` ; 15 vérifications sémantiques (hauteur, durée, rotation, codec…) | ffmpeg, sox, magick |
| `test_pipelines_real.py` | chaque pipeline avec ses défauts + régressions | ffmpeg, sox, magick |
| `test_api.py` | garde Host/Origin, traversée de chemin (ASGI brut), confinement des fichiers, mode manuel | ffmpeg, sox |

- Les médias d'exemple (vidéo, audio, image, GIF animé, sous-titres) sont **générés à la volée** par `harness.py`.
- Les entrées de test sont fabriquées **à partir des schémas Pydantic** : une action ajoutée au catalogue est testée sans écrire de test.
- Un binaire absent fait **sauter** le test (jamais échouer). Les tests `magick` exigent **ImageMagick 7** (un ImageMagick 6 est
  refusé par Mediakit, c'est voulu) : sans lui ils sont sautés.
- `test_svg_should_not_count_as_a_safe_image` est un `xfail(strict=True)` : il documente un problème **ouvert** et échouera le jour
  où il sera corrigé, pour te rappeler de retirer le marqueur.
