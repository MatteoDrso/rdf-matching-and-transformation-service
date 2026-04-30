# RDF Matching and Transformation Service

A FastAPI microservice that transforms tabular biodiversity records (CSV / JSON) into RDF triples (Turtle / JSON-LD) according to an expert-crafted mapping schema. Output is aligned with established biodiversity ontologies (Darwin Core RDF, ABCD, BiodivOntology).

This repository implements **WP8 / Requirement 7** of the BiodivPipeline SS26 project — a modular nf-core workflow for FAIR biodiversity data processing, developed in partnership between InfAI and the Botanischer Garten und Botanisches Museum Berlin (BGBM).

> Status: **scaffolding phase.** Reference scripts from InfAI (FU Berlin GitLab) will be integrated as the basis for the transformation engine.

---

## Goal

Build a production-grade, independently deployable microservice that:

1. Accepts a dataset (CSV / JSON) and a mapping schema (JSON-LD / Turtle, produced by the Schema Editor UI of WP7).
2. Matches each input field to the RDF property / class defined in the schema, applying SPARQL-based or programmatic alignment rules.
3. Produces valid RDF (Turtle or JSON-LD) compatible with Darwin Core RDF, ABCD, and BiodivOntology.
4. Exposes a REST API, ships as a Docker container, and is wrapped as a Nextflow module for the BiodivPipeline.

## Pipeline Context

```
Input Data ──► WP1 nf-core pipeline ──────────────────────────────────► Output Data (RDF)
                  ▲   ▲   ▲   ▲   ▲   ▲   ▲   ▲
                  │   │   │   │   │   │   │   │
                 WP2 WP3 WP4 WP5 WP6 WP7 WP8 (this repo)
```

The service consumes:
- the standardised, annotated, quality-checked dataset that has passed through WP2–WP6,
- the mapping schema produced by the WP7 Expert Schema Editor UI,

and emits FAIR RDF that downstream consumers can publish into the NFDI knowledge graph.

---

## Proposed Repository Layout

```
SP_WP8_SS26/
├── README.md
├── .gitignore
├── .env.example                  # OPENAI_API_KEY (if LLM-assisted alignment is used), SPARQL_ENDPOINT, …
├── requirements.txt              # fastapi, uvicorn, pydantic, rdflib, PyLD, pandas, pytest
├── Dockerfile                    # container definition for the REST service
├── docker-compose.yml            # local dev: service + (optional) triplestore
├── main.py                       # FastAPI entrypoint (uvicorn target)
│
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── routes.py             # endpoint handlers
│   │   └── models.py             # pydantic request/response schemas
│   ├── core/
│   │   ├── schema_loader.py      # parse JSON-LD / Turtle mapping schema
│   │   ├── mapper.py             # field → RDF property / class resolution
│   │   ├── transformer.py        # records → RDF graph
│   │   └── serializer.py         # graph → Turtle / JSON-LD
│   └── ontologies/               # cached reference ontologies (Darwin Core, ABCD, BiodivOntology)
│
├── examples/
│   ├── sample_dataset.csv
│   ├── sample_mapping.jsonld
│   └── expected_output.ttl
│
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   └── test_transformation.py
│
├── nextflow/
│   ├── main.nf                   # nf-core module wrapping the REST service
│   └── meta.yml                  # nf-core module metadata
│
└── docs/
    ├── api.md                    # extended API reference + sample transformation walkthrough
    └── architecture.md           # design decisions, ontology alignment notes
```

### Why this structure

- Mirrors the **flat, FastAPI-first style** of the reference [land-taxonomy-classifier](https://github.com/biodivportal/land-taxonomy-classifier) (single `main.py` entrypoint, `.env`-based config, `requirements.txt`).
- Adds a `src/` package because the transformation logic (schema parsing, mapping, serialisation) is non-trivial and benefits from separation — unlike the single-prompt land classifier.
- Splits `examples/`, `tests/`, `nextflow/`, and `docs/` to satisfy the deliverable list of Requirement 7: *source code, Dockerfile, REST API documentation, integration tests, sample transformation walkthrough.*
- Keeps `Dockerfile` and `nextflow/` at the top level so the nf-core module integration (WP1) and downstream consumers can find them easily.

---

## Planned API

| Method | Path           | Purpose                                                                |
| ------ | -------------- | ---------------------------------------------------------------------- |
| GET    | `/`            | Health check; returns service version and loaded ontologies.           |
| GET    | `/schemas`     | List schema formats accepted (JSON-LD, Turtle).                        |
| POST   | `/transform`   | Transform a dataset + mapping schema into RDF (Turtle or JSON-LD).     |
| POST   | `/validate`    | Validate a mapping schema against the loaded ontologies.               |

### `POST /transform` (sketch)

**Request (multipart/form-data):**
- `dataset`: CSV or JSON file
- `schema`: JSON-LD or Turtle mapping schema
- `output_format`: `turtle` (default) | `jsonld`

**Response:**
- `200 OK` with the generated RDF in the requested serialisation
- `400` on schema/dataset mismatch with a structured error explaining which field failed alignment

---

## Work Breakdown

The implementation will proceed roughly along the CRISP-DM iterations described in the Lastenheft. Concrete steps:

| # | Step                         | Output                                                          |
| - | ---------------------------- | --------------------------------------------------------------- |
| 1 | Repo scaffolding             | This README, `.gitignore`, `requirements.txt`, `main.py` stub   |
| 2 | Receive InfAI reference scripts | Imported into `src/core/` and refactored                     |
| 3 | Schema loader                | Parse JSON-LD / Turtle mapping documents                        |
| 4 | Transformation engine        | CSV/JSON record → RDF graph using the schema                    |
| 5 | Ontology alignment           | Validate against Darwin Core RDF, ABCD, BiodivOntology          |
| 6 | REST API                     | FastAPI endpoints listed above                                  |
| 7 | Containerisation             | `Dockerfile`, `docker-compose.yml`                              |
| 8 | Nextflow module              | `nextflow/main.nf` + `meta.yml` (consumed by WP1)               |
| 9 | Tests + sample walkthrough   | `tests/`, `examples/`, `docs/api.md`                            |

Open dependencies before development can fully start:
- Reference RDF mapping scripts from InfAI (FU Berlin GitLab access — request via karam@infai.org).
- Sample BGBM dataset and a sample mapping schema from WP7 for end-to-end testing.

---

## Setup (planned)

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
pip install -r requirements.txt

cp .env.example .env            # configure if LLM/SPARQL endpoints are used
uvicorn main:app --reload
```

Service available at `http://127.0.0.1:8000`; interactive Swagger UI at `/docs`.

### Docker

```bash
docker build -t sp-wp8-rdf-transform .
docker run --rm -p 8000:8000 --env-file .env sp-wp8-rdf-transform
```

---

## References

- [BiodivPipeline project context — nf-core / Nextflow](https://nf-co.re)
- [Reference service: Land Taxonomy Classifier](https://github.com/biodivportal/land-taxonomy-classifier) (architectural reference, WP3)
- [Darwin Core RDF Guide](https://dwc.tdwg.org/rdf/)
- [ABCD — Access to Biological Collection Data](https://www.tdwg.org/standards/abcd/)
- [RDFLib](https://rdflib.readthedocs.io/) · [PyLD](https://github.com/digitalbazaar/pyld) · [Apache Jena](https://jena.apache.org/)

## Contact

- Naouel Karam — karam@infai.org
- Jan Fillies — fillies@infai.org
