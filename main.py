from fastapi import FastAPI

from src.api.routes import router

app = FastAPI(
    title="RDF Matching and Transformation Service",
    description=(
        "Transforms tabular biodiversity records into RDF triples per a "
        "mapping schema. WP8 of the BiodivPipeline SS26 project."
    ),
    version="0.1.0",
)

app.include_router(router)
