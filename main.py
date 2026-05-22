from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import router
from src.core.ontology_loader import load_ontologies_from_dir


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load reference ontologies once at startup and stash them on app.state
    # so /validate and / can read them without paying the parse cost per
    # request. ~1 s for OBOE alone.
    app.state.ontologies = load_ontologies_from_dir()
    yield


app = FastAPI(
    title="RDF Matching and Transformation Service",
    description=(
        "Transforms tabular biodiversity records into RDF triples per a "
        "mapping schema. WP8 of the BiodivPipeline SS26 project."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)
