"""
Workbench — tests de config_manager (chargement / sauvegarde TOML).

Lancer :  pytest workbench/api/test_config_manager.py
"""


from workbench.api.config import WbConfig
from workbench.api.config_manager import load_config, save_config


class ProductConfig(WbConfig):
    theme: str = "clair"


def test_missing_file_returns_defaults_not_none(tmp_path):
    """Premier lancement : pas de fichier -> configuration par défaut (pas None)."""
    conf = load_config(str(tmp_path / "absent.toml"), ProductConfig)
    assert isinstance(conf, ProductConfig)
    assert conf.theme == "clair" and conf.max_concurrent_job == 10


def test_load_honors_config_cls_and_ignores_unknown_keys(tmp_path):
    path = tmp_path / "c.toml"
    path.write_text('max_concurrent_job = 3\ntheme = "sombre"\ninconnu = 1\n')
    conf = load_config(str(path), ProductConfig)
    assert type(conf) is ProductConfig          # avant : WbConfig (champs perdus)
    assert conf.theme == "sombre" and conf.max_concurrent_job == 3


def test_save_creates_parent_dirs_and_roundtrips(tmp_path):
    path = tmp_path / "nouveau" / "dossier" / "c.toml"
    assert save_config(ProductConfig(theme="sombre", buffer_max_lines=None), str(path))
    assert path.is_file()
    assert not list(path.parent.glob("*.tmp")), "pas de fichier temporaire résiduel"
    conf = load_config(str(path), ProductConfig)
    assert conf.theme == "sombre" and conf.buffer_max_lines == WbConfig().buffer_max_lines
