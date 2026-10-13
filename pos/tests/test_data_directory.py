from pathlib import Path

from config.paths import data_dir


def test_data_dir_appends_hidden_directory_to_configured_root(monkeypatch, tmp_path):
    monkeypatch.setenv("DJPOS_DATA_DIR", str(tmp_path))

    result = data_dir()

    assert isinstance(result, Path)
    assert result == tmp_path / ".djpos"


def test_data_dir_uses_home_directory_when_unconfigured(monkeypatch, tmp_path):
    monkeypatch.delenv("DJPOS_DATA_DIR", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    assert data_dir() == tmp_path / ".djpos"
