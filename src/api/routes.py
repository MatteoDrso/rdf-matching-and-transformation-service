import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from rdflib import Graph

from src.api.models import HealthResponse, SchemasResponse, ValidateResponse
from src.core.karma_runner import KarmaError, run_karma
from src.core.model_validator import validate_model
from src.core.ontology_loader import LoadedOntologies

router = APIRouter()

_FORMAT_TO_MEDIA = {
    "turtle": "text/turtle",
    "ttl": "text/turtle",
    "nt": "application/n-triples",
    "ntriples": "application/n-triples",
    "jsonld": "application/ld+json",
}

# Karma writes N-Triples to the output file regardless of extension. Map our
# requested output_format to an rdflib serialization name; None means
# pass-through (no reformat).
_FORMAT_TO_RDFLIB = {
    "turtle": "turtle",
    "ttl": "turtle",
    "nt": None,
    "ntriples": None,
    "jsonld": "json-ld",
}


def _strip_placeholder(value: Optional[str]) -> Optional[str]:
    """Treat Swagger UI's auto-filled "string" and empty input as missing."""
    if value is None or value == "" or value == "string":
        return None
    return value


def _strip_int_placeholder(value: Optional[int]) -> Optional[int]:
    """Treat Swagger UI's auto-filled 0 as missing — Karma uses 1-based row
    indexes, so 0 carries no useful meaning here."""
    if value is None or value == 0:
        return None
    return value


def get_ontologies(request: Request) -> LoadedOntologies:
    """Pull the LoadedOntologies index attached by main.py's lifespan event.
    Declared as a FastAPI dependency so tests can override it without
    needing a real startup cycle."""
    return request.app.state.ontologies


@router.get("/", response_model=HealthResponse)
def health(ontologies: LoadedOntologies = Depends(get_ontologies)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="0.1.0",
        ontologies=list(ontologies.sources),
    )


@router.get("/schemas", response_model=SchemasResponse)
def list_schema_formats() -> SchemasResponse:
    return SchemasResponse(formats=["karma-r2rml-ttl"])


@router.post("/transform")
async def transform(
    dataset: UploadFile = File(...),
    mapping_schema: UploadFile = File(...),
    source_type: str = Form("CSV"),
    delimiter: str = Form("COMMA"),
    source_name: str = Form("source"),
    output_format: str = Form("turtle"),
    # Optional pass-through of Karma OfflineRdfGenerator flags documented in
    # https://github.com/usc-isi-i2/Web-Karma/wiki/Batch-Mode-for-RDF-Generation.
    # `None` means: do not forward the flag, let Karma use its built-in default.
    encoding: Optional[str] = Form(None),
    text_qualifier: Optional[str] = Form(None),
    header_index: Optional[int] = Form(None),
    data_index: Optional[int] = Form(None),
    selection: Optional[str] = Form(None),
) -> Response:
    fmt = output_format.lower()
    if fmt not in _FORMAT_TO_MEDIA:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported output_format: {output_format!r}. "
                f"Supported: {sorted(set(_FORMAT_TO_MEDIA))}"
            ),
        )

    dataset_bytes = await dataset.read()
    model_bytes = await mapping_schema.read()
    # The Karma model references the dataset by basename via rr:tableName,
    # so preserve the upload's original filename inside the temp dir.
    dataset_name = Path(dataset.filename or "dataset.csv").name

    with tempfile.TemporaryDirectory(prefix="karma_") as tmp:
        tmp_dir = Path(tmp)
        dataset_path = tmp_dir / dataset_name
        model_path = tmp_dir / "mapping-model.ttl"
        output_path = tmp_dir / "output.nt"
        dataset_path.write_bytes(dataset_bytes)
        model_path.write_bytes(model_bytes)

        # Swagger UI auto-fills Optional[str] form fields with the literal
        # placeholder "string" and Optional[int] fields with 0. Users who
        # don't manually clear those values end up sending nonsensical
        # input (e.g. --encoding=string, --headerindex=0) which makes
        # Karma silently produce no row-bound triples. Normalise both
        # placeholders, and the empty string, back to "not provided".
        encoding = _strip_placeholder(encoding)
        text_qualifier = _strip_placeholder(text_qualifier)
        selection = _strip_placeholder(selection)
        header_index = _strip_int_placeholder(header_index)
        data_index = _strip_int_placeholder(data_index)

        try:
            result = await asyncio.to_thread(
                run_karma,
                dataset_path=dataset_path,
                model_path=model_path,
                output_path=output_path,
                source_type=source_type,
                delimiter=delimiter,
                source_name=source_name,
                encoding=encoding,
                text_qualifier=text_qualifier,
                header_index=header_index,
                data_index=data_index,
                selection=selection,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(
                status_code=504,
                detail=f"Karma transformation timed out after {exc.timeout}s",
            ) from exc
        except KarmaError as exc:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Karma transformation failed",
                    "returncode": exc.returncode,
                    "stderr": exc.stderr[-2000:],
                },
            ) from exc

    rdflib_format = _FORMAT_TO_RDFLIB[fmt]
    if rdflib_format is None:
        content = result.rdf
    else:
        graph = Graph()
        graph.parse(data=result.rdf, format="nt")
        content = graph.serialize(format=rdflib_format)

    return Response(content=content, media_type=_FORMAT_TO_MEDIA[fmt])


@router.post("/validate", response_model=ValidateResponse)
async def validate(
    mapping_schema: UploadFile = File(...),
    ontologies: LoadedOntologies = Depends(get_ontologies),
) -> ValidateResponse:
    """Pre-flight check of a Karma R2RML mapping model:

    - L1 — the file parses as Turtle
    - L2 — the file declares a `km-dev:R2RMLMapping` with a `sourceName`
    - L3 — every IRI in a known ontology namespace is actually declared
      there (catches typos and stale model references)

    See `src/core/model_validator.py` for the implementation. A clean
    model returns `{"valid": true, "issues": []}`; any finding flips
    `valid` to false and lists the specific issues.
    """
    model_bytes = await mapping_schema.read()
    result = validate_model(model_bytes, ontologies)
    return ValidateResponse(valid=result.valid, issues=result.issues)
