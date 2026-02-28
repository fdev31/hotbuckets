"""Tests for hotbuckets.cli — CLI argument parsing and end-to-end."""

import subprocess
import sys
from pathlib import Path

import pytest

from hotbuckets.cli import main

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestCliArgParsing:
    """Test CLI argument handling."""

    def test_missing_config_exits(self):
        with pytest.raises(SystemExit):
            main([])

    def test_version_flag(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_check_flag(self, capsys):
        toml_path = str(FIXTURES_DIR / "basic.toml")
        main(["--check", toml_path])
        captured = capsys.readouterr()
        assert "valid" in captured.out.lower()

    def test_nonexistent_file(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["/nonexistent/file.toml"])
        assert exc_info.value.code == 1

    def test_stdout_output(self, capsys):
        toml_path = str(FIXTURES_DIR / "basic.toml")
        main([toml_path])
        captured = capsys.readouterr()
        assert "#!/bin/bash" in captured.out
        assert "tbf" in captured.out

    def test_output_to_file(self, tmp_path):
        toml_path = str(FIXTURES_DIR / "basic.toml")
        out_file = tmp_path / "output.sh"
        main(["-o", str(out_file), toml_path])
        content = out_file.read_text()
        assert "#!/bin/bash" in content
        assert "tbf" in content


class TestCliEntryPoint:
    """Test the htb entry point works via subprocess."""

    def test_htb_command_exists(self):
        """The 'htb' console_scripts entry point should be installed."""
        result = subprocess.run(
            [sys.executable, "-m", "hotbuckets", "--version"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_python_m_hotbuckets(self):
        toml_path = str(FIXTURES_DIR / "basic.toml")
        result = subprocess.run(
            [sys.executable, "-m", "hotbuckets", toml_path],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "tbf" in result.stdout
