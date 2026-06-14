"""Tests for config loading behavior."""

import pytest

from server.config import AppConfig, load_config


class TestMissingConfigIsHardError:
    def test_missing_config_raises(self, tmp_path):
        """A missing config file must raise rather than silently using defaults
        (which would disable auth and serve mock data)."""
        missing = tmp_path / "nope.yaml"
        with pytest.raises(FileNotFoundError):
            load_config(str(missing))


class TestValidConfigLoads:
    def test_valid_config_loads(self, tmp_path):
        """A well-formed config file parses into AppConfig with the given values."""
        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            "server:\n  host: '127.0.0.1'\n  port: 9000\n  token: 'secret'\n"
        )
        loaded = load_config(str(cfg))
        assert isinstance(loaded, AppConfig)
        assert loaded.server.host == "127.0.0.1"
        assert loaded.server.port == 9000
        assert loaded.server.token == "secret"
