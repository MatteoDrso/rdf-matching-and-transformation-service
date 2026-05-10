# RDF Matching and Transformation Service

A FastAPI microservice that transforms tabular biodiversity / trait records
(CSV / TSV / JSON) into RDF triples (Turtle / N-Triples / JSON-LD) using a
**Karma R2RML-style mapping model** produced by the WP7 Schema Editor. The
output is aligned primarily with the **OBOE 1.2** observation ontology, with
support for additional reference ontologies (Darwin Core RDF, ABCD,
BiodivOntology) for downstream interoperability.

This repository implements **WP8 / Requirement 7** of the BiodivPipeline SS26
project — a modular nf-core workflow for FAIR biodiversity data processing,
developed in partnership between InfAI and the Botanischer Garten und
Botanisches Museum Berlin (BGBM).

> **Status:** integration phase. The transformation engine is the open-source
> [Web-Karma](https://github.com/usc-isi-i2/Web-Karma) `OfflineRdfGenerator`
> (USC ISI). This service wraps the Karma JAR behind a REST API and a
> Nextflow module.

---

## Goal

Build a production-grade, independently deployable microservice that:

1. Accepts a dataset (CSV / TSV / JSON) and a Karma R2RML mapping model
   (`*-model.ttl`, produced by the Schema Editor UI of WP7).
2. Runs the Karma offline RDF generator to produce RDF aligned with the
   ontology referenced in the model (OBOE 1.2 by default).
3. Returns the generated RDF (Turtle / N-Triples / JSON-LD).
4. Exposes a REST API, ships as a Docker container, and is wrapped as a
   Nextflow module for the BiodivPipeline.

## Pipeline Context

```
Input Data ──► WP1 nf-core pipeline ──────────────────────────────────► Output Data (RDF)
                  ▲   ▲   ▲   ▲   ▲   ▲   ▲   ▲
                  │   │   │   │   │   │   │   │
                 WP2 WP3 WP4 WP5 WP6 WP7 WP8 (this repo)
```

The service consumes:
- the standardised, annotated, quality-checked dataset that has passed
  through WP2–WP6,
- the Karma R2RML mapping model produced by the WP7 Expert Schema Editor UI,

and emits FAIR RDF that downstream consumers can publish into the NFDI
knowledge graph.

---

## Transformation Engine — Karma

The transformation is performed by the `OfflineRdfGenerator` class shipped
with [Web-Karma](https://github.com/usc-isi-i2/Web-Karma). The reference
command from InfAI is:

```bash
java -cp karma-spark-0.0.1-SNAPSHOT-shaded.jar \
  edu.isi.karma.rdf.OfflineRdfGenerator \
  --sourcetype CSV \
  --filepath "plant_height_vegetative_raw_germany_20.csv" \
  --delimiter TAB \
  --modelfilepath "plant_height_vegetative_raw-model.ttl" \
  --sourcename source \
  --outputfile plant_height_vegetative_raw_germany_20.ttl
```

| Argument           | Meaning                                                  |
| ------------------ | -------------------------------------------------------- |
| `--sourcetype`     | `CSV`, `JSON`, etc.                                      |
| `--filepath`       | Tabular input file                                       |
| `--delimiter`      | `TAB` for TSV (note: filename ends `.csv` but is TSV)    |
| `--modelfilepath`  | Karma R2RML mapping model (the WP7 artefact)             |
| `--sourcename`     | Logical source name referenced in the model              |
| `--outputfile`     | Generated RDF (default Turtle / N-Triples)               |

### Obtaining the JAR

The `karma-spark-*-shaded.jar` is **not** distributed via GitHub releases —
the upstream `usc-isi-i2/Web-Karma` repository was archived on 16 April 2025.
Build it from source once and place it under `lib/` locally:

```bash
git clone https://github.com/usc-isi-i2/Web-Karma.git
cd Web-Karma
mvn -DskipTests package
cp karma-spark/target/karma-spark-*-shaded.jar /path/to/SP_WP8_SS26/lib/
```

`lib/*.jar` is git-ignored. See [lib/README.md](lib/README.md).

---

## Ontology Strategy

The favoured ontology for the BGBM trait data is **OBOE 1.2** (Extensible
Observation Ontology, [oboe-core](http://ecoinformatics.org/oboe/oboe.1.2/)).
Each row of a TraitBank-style table becomes an
`oboe-core:ObservationCollection` containing one or more
`oboe-core:Observation`s, each with a typed
`oboe-core:Measurement` of an `oboe-core:Entity` (taxon) for an
`oboe-core:Characteristic` (trait), expressed as an
`oboe-core:MeasuredValue` `usesStandard` an `oboe-core:Unit` (QUDT).

The Lastenheft also lists the following ontologies as required for
interoperability; they are kept as **secondary alignment targets**:

- [Darwin Core RDF](https://dwc.tdwg.org/rdf/) — for occurrence / taxonomic data
- [ABCD](https://www.tdwg.org/standards/abcd/) — for collection metadata
- BiodivOntology — for higher-level biodiversity concepts

Cross-walk mappings (OBOE ↔ Darwin Core / ABCD / BiodivOntology) will be
modelled in WP7 and validated in WP8 via the `/validate` endpoint.

External vocabularies referenced by the example model:

- [QUDT](https://qudt.org/vocab/unit/) — units of measurement
- [Catalogue of Life](https://www.catalogueoflife.org/) — taxon URIs
- [TOP Thesaurus](http://top-thesaurus.org/) — trait identifiers

---

## Repository Layout

```
SP_WP8_SS26/
├── README.md
├── .gitignore                      # ignores .DS_Store, ~$*, lib/*.jar
├── .env.example                    # OPENAI_API_KEY (optional), KARMA_JAR_PATH, JAVA_HOME, …
├── requirements.txt                # fastapi, uvicorn, pydantic, rdflib, …
├── Dockerfile                      # Python + JRE + Karma JAR
├── docker-compose.yml              # local dev: service (+ optional triplestore)
├── main.py                         # FastAPI entrypoint (uvicorn target)
│
├── src/
│   ├── api/
│   │   ├── routes.py               # endpoint handlers
│   │   └── models.py               # pydantic request/response schemas
│   ├── core/
│   │   ├── karma_runner.py         # subprocess wrapper around the Karma JAR (planned)
│   │   └── serializer.py           # rdflib-based reformatting (TTL → JSON-LD, etc.)
│   └── ontologies/                 # cached reference ontologies (OBOE, DwC, ABCD, BiodivOntology)
│
├── lib/                            # Karma JAR placement (git-ignored)
│   └── README.md
│
├── examples/
│   ├── plant_height_vegetative_raw_germany_20.csv          # InfAI sample dataset (TSV)
│   ├── plant_height_vegetative_raw-model_oboe.ttl          # Karma R2RML model (OBOE-aligned)
│   ├── plant_height_vegetative_raw_germany_20_oboe.ttl     # Expected RDF output (ground truth)
│   └── ontologies/
│       └── README.md               # placement of OBOE OWL etc. for offline tests
│
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   └── test_transformation.py
│
├── nextflow/
│   ├── main.nf                     # nf-core module wrapping the service / Karma
│   └── meta.yml                    # nf-core module metadata
│
└── docs/
    ├── api.md                      # extended API reference + sample walkthrough
    └── architecture.md             # design decisions, ontology alignment notes
```

---

## Planned API

| Method | Path           | Purpose                                                                |
| ------ | -------------- | ---------------------------------------------------------------------- |
| GET    | `/`            | Health check; returns service version, JAR version, loaded ontologies. |
| GET    | `/schemas`     | List supported mapping schema formats (Karma R2RML model).             |
| POST   | `/transform`   | Transform a dataset + Karma model into RDF.                            |
| POST   | `/validate`    | Validate a Karma model against the loaded ontologies.                  |

### `POST /transform` (sketch)

**Request (multipart/form-data):**

| Field            | Type | Required | Notes                                          |
| ---------------- | ---- | -------- | ---------------------------------------------- |
| `dataset`        | file | yes      | CSV / TSV / JSON                               |
| `mapping_schema` | file | yes      | Karma R2RML model (`*-model.ttl`)              |
| `source_type`    | str  | no       | `CSV` (default), `JSON`, …                     |
| `delimiter`      | str  | no       | `COMMA` (default), `TAB`, `;`                  |
| `output_format`  | str  | no       | `turtle` (default), `ntriples`, `jsonld`       |

**Response:**
- `200 OK` with the generated RDF in the requested serialisation
- `400` with a structured error if Karma reports a mapping/parse failure

---

## Sample Walkthrough

The `examples/` directory contains a complete InfAI-supplied example:

| File                                                | Role                              |
| --------------------------------------------------- | --------------------------------- |
| `plant_height_vegetative_raw_germany_20.csv`        | Input — 20 rows of TRY-style trait data (TSV) |
| `plant_height_vegetative_raw-model_oboe.ttl`        | Karma R2RML model (OBOE-aligned)  |
| `plant_height_vegetative_raw_germany_20_oboe.ttl`   | Expected RDF output (ground truth) |

End-to-end reproduction with the JAR in `lib/`:

```bash
cd examples
java -cp ../lib/karma-spark-*-shaded.jar \
  edu.isi.karma.rdf.OfflineRdfGenerator \
  --sourcetype CSV \
  --filepath plant_height_vegetative_raw_germany_20.csv \
  --delimiter TAB \
  --modelfilepath plant_height_vegetative_raw-model_oboe.ttl \
  --sourcename source \
  --outputfile out.ttl

diff <(sort out.ttl) <(sort plant_height_vegetative_raw_germany_20_oboe.ttl)
```

---

## Work Breakdown

| # | Step                              | Output                                                                  |
| - | --------------------------------- | ----------------------------------------------------------------------- |
| 1 | Repo scaffolding                  | This README, `.gitignore`, `requirements.txt`, `main.py` stub           |
| 2 | InfAI reference imported          | Example CSV / model / expected output in `examples/`                    |
| 3 | Build & vendor Karma JAR          | `lib/karma-spark-*-shaded.jar`                                          |
| 4 | Local reproduction of the InfAI command | Verified diff against expected output                             |
| 5 | Karma subprocess wrapper          | `src/core/karma_runner.py`                                              |
| 6 | REST API wired up                 | `/transform`, `/validate` no longer 501                                 |
| 7 | Containerisation                  | `Dockerfile` (Python + JRE + JAR), `docker-compose.yml`                 |
| 8 | Nextflow module                   | `nextflow/main.nf` aligned with the wrapper / direct JAR call           |
| 9 | Tests + sample walkthrough        | `tests/`, `docs/api.md`                                                 |

Open dependencies / clarifications:

- OBOE OWL file (`oboe-core.owl`) — needed for `/validate` and offline alignment tests.
- Confirmation from InfAI on the expected Karma version / commit, so the
  build above is reproducible.
- Confirmation that the WP7 Schema Editor emits Karma-compatible models
  directly (or whether a converter is needed).

---

## Setup (planned)

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
pip install -r requirements.txt

cp .env.example .env            # configure JAR path, optional endpoints
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

- [Web-Karma (USC ISI)](https://github.com/usc-isi-i2/Web-Karma) — transformation engine (archived 2025-04-16)
- [BiodivPipeline project context — nf-core / Nextflow](https://nf-co.re)
- [Reference service: Land Taxonomy Classifier](https://github.com/biodivportal/land-taxonomy-classifier) (architectural reference, WP3)
- [OBOE 1.2 — Extensible Observation Ontology](http://ecoinformatics.org/oboe/oboe.1.2/)
- [Darwin Core RDF Guide](https://dwc.tdwg.org/rdf/)
- [ABCD — Access to Biological Collection Data](https://www.tdwg.org/standards/abcd/)
- [QUDT Units of Measurement](https://qudt.org/vocab/unit/)
- [RDFLib](https://rdflib.readthedocs.io/) · [PyLD](https://github.com/digitalbazaar/pyld) · [Apache Jena](https://jena.apache.org/)

## Contact

- Naouel Karam — karam@infai.org
- Jan Fillies — fillies@infai.org
