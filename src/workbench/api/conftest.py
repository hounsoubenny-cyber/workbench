"""
pytest — configuration du dossier api/.

`test_cli_frontend.py` et `test_live_client.py` sont des OUTILS INTERACTIFS
(menus Rich, serveur uvicorn en sous-processus) qui demandent des dépendances
de développement optionnelles (rich, aiohttp). Ils se lancent à la main
(`python3 -m workbench.api.test_live_client`) et ne doivent pas casser la
collecte de pytest quand ces dépendances sont absentes.
"""

import importlib.util

collect_ignore = []

if importlib.util.find_spec("rich") is None:
    collect_ignore.append("test_live_client.py")
if importlib.util.find_spec("aiohttp") is None or importlib.util.find_spec("rich") is None:
    collect_ignore.append("test_cli_frontend.py")
