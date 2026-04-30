from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from src.api.models import HealthResponse, SchemasResponse, ValidateResponse

router = APIRouter()


@router.get("/", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version="0.1.0", ontologies=[])


@router.get("/schemas", response_model=SchemasResponse)
def list_schema_formats() -> SchemasResponse:
    return SchemasResponse(formats=["jsonld", "turtle"])


@router.post("/transform")
async def transform(
    dataset: UploadFile = File(...),
    mapping_schema: UploadFile = File(...),
    output_format: str = Form("turtle"),
):
    raise HTTPException(status_code=501, detail="Not yet implemented")


@router.post("/validate", response_model=ValidateResponse)
async def validate(mapping_schema: UploadFile = File(...)) -> ValidateResponse:
    raise HTTPException(status_code=501, detail="Not yet implemented")
