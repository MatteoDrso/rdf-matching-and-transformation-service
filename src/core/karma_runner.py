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

    # karma-offline is the lean module that actually contains OfflineRdfGenerator;
    # karma-spark is the legacy Spark-bundled variant we no longer build but may
    # still be present from older local checkouts, so accept either.
    pattern = str(_REPO_ROOT / "lib" / "karma-*-shaded.jar")
    candidates = sorted(glob.glob(pattern))
    if not candidates:
        raise FileNotFoundError(
            "No Karma JAR found. Set KARMA_JAR or place "
            "karma-offline-*-shaded.jar under lib/."
        )
    return Path(candidates[-1])


_HOMEBREW_JAVA_HINTS = (
    "/opt/homebrew/opt/openjdk@11/libexec/openjdk.jdk/Contents/Home/bin/java",
    "/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home/bin/java",
    "/usr/local/opt/openjdk@11/libexec/openjdk.jdk/Contents/Home/bin/java",
)


def _java_works(candidate: str) -> bool:
    try:
        result = subprocess.run(
            [candidate, "-version"], capture_output=True, timeout=10
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _resolve_java() -> str:
    # On macOS, /usr/bin/java is a non-functional shim if no JDK is installed;
    # `shutil.which` returns it anyway. Verify each candidate actually runs.
    candidates: list[str] = []
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidates.append(str(Path(java_home) / "bin" / "java"))
    found = shutil.which("java")
    if found:
        candidates.append(found)
    candidates.extend(_HOMEBREW_JAVA_HINTS)

    for candidate in candidates:
        if _java_works(candidate):
            return candidate

    raise FileNotFoundError(
        "No working Java runtime found. Set JAVA_HOME or install a JDK "
        "(macOS: `brew install openjdk@11`)."
    )


def run_karma(
    *,
    dataset_path: Path | str,
    model_path: Path | str,
    output_path: Path | str,
    source_type: str = "CSV",
    delimiter: str = "COMMA",
    source_name: str = "source",
    encoding: str | None = None,
    text_qualifier: str | None = None,
    header_index: int | None = None,
    data_index: int | None = None,
    selection: str | None = None,
    jar_path: Path | str | None = None,
    java_path: str | None = None,
    timeout_seconds: float | None = 300,
) -> KarmaResult:
    """Invoke Karma's OfflineRdfGenerator and return the generated RDF.

    The caller owns the lifecycle of `dataset_path`, `model_path`, and the
    parent directory of `output_path` — typically a `tempfile.TemporaryDirectory`.

    Optional CSV/JSON-source parameters mirror Karma's CLI flags documented at
    https://github.com/usc-isi-i2/Web-Karma/wiki/Batch-Mode-for-RDF-Generation:
    `encoding` → `--encoding`, `text_qualifier` → `--textqualifier`,
    `header_index` → `--headerindex`, `data_index` → `--dataindex`,
    `selection` → `--selection`. They are only forwarded when set.

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
    if encoding is not None:
        cmd += ["--encoding", encoding]
    if text_qualifier is not None:
        cmd += ["--textqualifier", text_qualifier]
    if header_index is not None:
        cmd += ["--headerindex", str(header_index)]
    if data_index is not None:
        cmd += ["--dataindex", str(data_index)]
    if selection is not None:
        cmd += ["--selection", selection]

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
