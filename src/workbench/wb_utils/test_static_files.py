"""Tests de resolve_static_file : aucune sortie de `root`, jamais."""

import os

import pytest

from workbench.wb_utils.static_files import resolve_static_file


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<html/>")
    (root / "assets" / "app.js").write_text("1")
    (tmp_path / "secret.txt").write_text("secret")      # HORS de root
    return root


def test_serves_files_under_root(tree):
    assert resolve_static_file(tree, "index.html") == (tree / "index.html").resolve()
    assert resolve_static_file(tree, "assets/app.js").name == "app.js"


@pytest.mark.parametrize("bad", [
    "../secret.txt", "assets/../../secret.txt", "../../../../../../etc/passwd",
    "/etc/passwd", "index.html\x00.png", "", "assets", "absent.html",
])
def test_refuses_escapes_and_non_files(tree, bad):
    assert resolve_static_file(tree, bad) is None


@pytest.mark.skipif(os.name == "nt", reason="symlinks : droits spécifiques sous Windows")
def test_refuses_symlink_pointing_outside(tree):
    (tree / "leak.txt").symlink_to(tree.parent / "secret.txt")
    assert resolve_static_file(tree, "leak.txt") is None
