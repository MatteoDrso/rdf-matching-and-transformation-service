import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from rdflib import Graph

from src.api.models import HealthResponse, SchemasResponse, ValidateResponse
from src.core.karma_runner import KarmaError, run_karma

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


@router.get("/", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0", ontologies=[])


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
async def validate(mapping_schema: UploadFile = File(...)) -> ValidateResponse:
    raise HTTPException(status_code=501, detail="Not yet implemented")
