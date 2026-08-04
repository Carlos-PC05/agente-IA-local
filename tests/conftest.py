"""Fixtures compartidas: aíslan los sandbox de archivos y notas a carpetas temporales."""
import pytest

import agent.config as config
from agent.tools import files as files_mod
from agent.tools import notes as notes_mod


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """Redirige WORKSPACE_DIR (sandbox de archivos) a una carpeta temporal por test."""
    monkeypatch.setattr(files_mod, "WORKSPACE_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def notes_dir(tmp_path, monkeypatch):
    """Redirige NOTES_DIR (directorio de notas) a una carpeta temporal por test."""
    monkeypatch.setattr(config, "NOTES_DIR", tmp_path)
    monkeypatch.setattr(notes_mod, "NOTES_DIR", tmp_path)
    return tmp_path
