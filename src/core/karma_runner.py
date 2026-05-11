"""Subprocess wrapper around the Web-Karma OfflineRdfGenerator."""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


class KarmaError(RuntimeError):
    """Raised when the Karma JAR exits non-zero or produces no output."""

    def __init__(self, returncode: int, stderr: str, stdout: str = ""):
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout
        msg = f"Karma exited with code {returncode}: {stderr.strip()[:500]}"
        super().__init__(msg)


@dataclass(frozen=True)
class KarmaResult:
    rdf: str
    stdout: str
    stderr: str


def _resolve_jar() -> Path:
    explicit = os.environ.get("KARMA_JAR")
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(f"KARMA_JAR points to a missing file: {path}")
        return path

    pattern = str(_REPO_ROOT / "lib" / "karma-spark-*-shaded.jar")
    candidates = sorted(glob.glob(pattern))
    if not candidates:
        raise FileNotFoundError(
            "No Karma JAR found. Set KARMA_JAR or place "
            "karma-spark-*-shaded.jar under lib/."
        )
    return Path(candidates[-1])


def _resolve_java() -> str:
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidate = Path(java_home) / "bin" / "java"
        if candidate.is_file():
            return str(candidate)
    found = shutil.which("java")
    if not found:
        raise FileNotFoundError(
            "No Java runtime found on PATH and JAVA_HOME is unset."
        )
    return found


def run_karma(
    *,
    dataset_path: Path | str,
    model_path: Path | str,
    output_path: Path | str,
    source_type: str = "CSV",
    delimiter: str = "COMMA",
    source_name: str = "source",
    jar_path: Path | str | None = None,
    java_path: str | None = None,
    timeout_seconds: float | None = 300,
) -> KarmaResult:
    """Invoke Karma's OfflineRdfGenerator and return the generated RDF.

    The caller owns the lifecycle of `dataset_path`, `model_path`, and the
    parent directory of `output_path` — typically a `tempfile.TemporaryDirectory`.

    Raises:
        KarmaError: the JAR exited non-zero or produced no output file.
        FileNotFoundError: the JAR or a Java runtime could not be located.
        subprocess.TimeoutExpired: `timeout_seconds` was exceeded.
    """
    dataset = Path(dataset_path).resolve()
    model = Path(model_path).resolve()
    output = Path(output_path).resolve()
    jar = Path(jar_path).resolve() if jar_path else _resolve_jar()
    java = java_path or _resolve_java()

    cmd = [
        java,
        "-cp", str(jar),
        "edu.isi.karma.rdf.OfflineRdfGenerator",
        "--sourcetype", source_type,
        "--filepath", str(dataset),
        "--delimiter", delimiter,
        "--modelfilepath", str(model),
        "--sourcename", source_name,
        "--outputfile", str(output),
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        cwd=output.parent,
    )

    if proc.returncode != 0:
        raise KarmaError(proc.returncode, proc.stderr, proc.stdout)

    if not output.is_file():
        raise KarmaError(
            proc.returncode,
            f"Karma exited 0 but no output file at {output}\n{proc.stderr}",
            proc.stdout,
        )

    return KarmaResult(rdf=output.read_text(), stdout=proc.stdout, stderr=proc.stderr)
