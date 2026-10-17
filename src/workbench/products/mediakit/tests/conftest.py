"""
Mediakit — fixtures de test.

Les tests d'intégration lancent les VRAIS binaires (ffmpeg, sox, magick) à travers
l'application complète ; un test dont le binaire manque est SAUTÉ, pas en échec.
`magick` doit être ImageMagick 7 : un ImageMagick 6 est refusé par le contrôle de version
de Mediakit (c'est voulu), donc ces tests sont sautés plutôt que faux.
"""

import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from workbench.products.mediakit.tests import harness as H


def has_binary(name: str) -> bool:
    return shutil.which(name) is not None


def _magick_is_v7() -> bool:
    if not has_binary("magick"):
        return False
    out = subprocess.run(["magick", "--version"], capture_output=True, text=True).stdout
    return "ImageMagick 7" in out


def need(*binaries: str):
    """`pytestmark = need("ffmpeg")` : saute si un binaire manque (ou si magick n'est pas en v7)."""
    missing = [b for b in binaries if not (_magick_is_v7() if b == "magick" else has_binary(b))]
    return pytest.mark.skipif(bool(missing), reason=f"binaire(s) absent(s) ou incompatible(s) : {', '.join(missing)}")


@pytest.fixture(scope="session")
def media(tmp_path_factory):
    if not (has_binary("ffmpeg") and has_binary("convert") or has_binary("magick")):
        pytest.skip("ffmpeg et ImageMagick requis pour générer les médias d'exemple")
    return H.build_media(tmp_path_factory.mktemp("media"))


@pytest.fixture(scope="module")
def client():
    from workbench.products.mediakit.api.main_api import app
    with TestClient(app, base_url=f"http://{H.HOST}") as c:
        yield c


@pytest.fixture
def api(client) -> H.Api:
    return H.Api(client)
