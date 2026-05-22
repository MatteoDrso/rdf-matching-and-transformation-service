"""Unit tests for `karma_runner.run_karma` — exercise CLI flag wiring
without invoking the JAR or a JVM."""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core import karma_runner


@pytest.fixture
def stub_resolvers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    jar = tmp_path / "karma-offline-shaded.jar"
    jar.write_bytes(b"")
    monkeypatch.setattr(karma_runner, "_resolve_jar", lambda: jar)
    monkeypatch.setattr(karma_runner, "_resolve_java", lambda: "/usr/bin/java")
    return jar


def _stub_subprocess_run(captured: list[list[str]], output_path: Path):
    def _fake_run(cmd, **_kwargs):
        captured.append(list(cmd))
        output_path.write_text("# stub n-triples output\n")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    return _fake_run


def test_required_flags_passed_through(stub_resolvers, tmp_path: Path):
    output = tmp_path / "out.nt"
    captured: list[list[str]] = []
    with patch.object(subprocess, "run", _stub_subprocess_run(captured, output)):
        karma_runner.run_karma(
            dataset_path=tmp_path / "in.csv",
            model_path=tmp_path / "m.ttl",
            output_path=output,
            source_type="CSV",
            delimiter="TAB",
            source_name="src",
        )

    cmd = captured[0]
    assert "--sourcetype" in cmd and cmd[cmd.index("--sourcetype") + 1] == "CSV"
    assert "--delimiter" in cmd and cmd[cmd.index("--delimiter") + 1] == "TAB"
    assert "--sourcename" in cmd and cmd[cmd.index("--sourcename") + 1] == "src"
    # Optional flags must not appear unless explicitly set.
    for absent in ("--encoding", "--textqualifier", "--headerindex",
                   "--dataindex", "--selection"):
        assert absent not in cmd, f"{absent} should not be in cmd"


def test_optional_flags_passed_when_set(stub_resolvers, tmp_path: Path):
    output = tmp_path / "out.nt"
    captured: list[list[str]] = []
    with patch.object(subprocess, "run", _stub_subprocess_run(captured, output)):
        karma_runner.run_karma(
            dataset_path=tmp_path / "in.csv",
            model_path=tmp_path / "m.ttl",
            output_path=output,
            encoding="UTF-8",
            text_qualifier='"',
            header_index=1,
            data_index=2,
            selection="DEFAULT_TEST",
        )

    cmd = captured[0]
    assert cmd[cmd.index("--encoding") + 1] == "UTF-8"
    assert cmd[cmd.index("--textqualifier") + 1] == '"'
    assert cmd[cmd.index("--headerindex") + 1] == "1"
    assert cmd[cmd.index("--dataindex") + 1] == "2"
    assert cmd[cmd.index("--selection") + 1] == "DEFAULT_TEST"


def test_only_explicitly_set_optional_flags_are_forwarded(stub_resolvers, tmp_path: Path):
    output = tmp_path / "out.nt"
    captured: list[list[str]] = []
    with patch.object(subprocess, "run", _stub_subprocess_run(captured, output)):
        karma_runner.run_karma(
            dataset_path=tmp_path / "in.csv",
            model_path=tmp_path / "m.ttl",
            output_path=output,
            encoding="ISO-8859-1",
        )

    cmd = captured[0]
    assert "--encoding" in cmd
    for absent in ("--textqualifier", "--headerindex", "--dataindex", "--selection"):
        assert absent not in cmd
