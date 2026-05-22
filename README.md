# RDF Matching and Transformation Service

A FastAPI microservice that turns tabular biodiversity records (CSV /
TSV / JSON) into RDF using a Karma R2RML mapping model produced by the
WP7 Schema Editor. Output aligns with OBOE 1.2 by default. Part of the
BiodivPipeline WP8 work-package, developed with InfAI and the BGBM.

## Quick start

```bash
git clone https://github.com/MatteoDrso/rdf-matching-and-transformation-service.git
cd rdf-matching-and-transformation-service
docker build -t sp-wp8 .                                  # ~30 s
docker run --rm -p 8000:8000 --name rdf-transform sp-wp8
```

Swagger UI at http://127.0.0.1:8000/docs.

## `POST /transform`

Multipart form. Required: `dataset` (file), `mapping_schema` (file).
Optional:

| field            | default  | notes                                  |
| ---------------- | -------- | -------------------------------------- |
| `source_type`    | `CSV`    | `CSV`, `JSON`, `XML`, `DB`             |
| `delimiter`      | `COMMA`  | `COMMA`, `TAB`, `;`                    |
| `source_name`    | `source` | matches the model's logical source     |
| `output_format`  | `turtle` | `turtle`, `ntriples`, `jsonld`         |
| `encoding`       | —        | e.g. `UTF-8`                           |
| `text_qualifier` | —        | CSV quote char                         |
| `header_index`   | —        | 1-based                                |
| `data_index`     | —        | 1-based                                |
| `selection`      | —        | named selection inside the Karma model |

The five optional fields mirror the Karma OfflineRdfGenerator CLI flags
from the [Batch Mode wiki](https://github.com/usc-isi-i2/Web-Karma/wiki/Batch-Mode-for-RDF-Generation)
and are only forwarded when set.

Example against the InfAI sample under `examples/`:

```bash
curl -X POST http://127.0.0.1:8000/transform \
  -F "dataset=@examples/plant_height_vegetative_raw_germany_20.csv" \
  -F "mapping_schema=@examples/plant_height_vegetative_raw-model_oboe.ttl" \
  -F "delimiter=TAB" \
  -o out.ttl
```

Other endpoints: `GET /` (health, also reports loaded ontologies),
`GET /schemas` (lists supported model formats), `POST /validate`.

## `POST /validate`

Pre-flight check for a mapping model. Catches three classes of problem
*before* `/transform` produces RDF that points into the void:

- **L1** — does the file parse as Turtle?
- **L2** — is it actually a Karma R2RML model (`km-dev:R2RMLMapping`
  resource with a `km-dev:sourceName`)?
- **L3** — does every IRI the model references in a loaded ontology's
  namespace (OBOE today) actually exist there? Catches typos like
  `oboe-core:Observatoin` and references to renamed/removed upstream
  classes.

```bash
curl -X POST http://127.0.0.1:8000/validate \
  -F "mapping_schema=@examples/plant_height_vegetative_raw-model_oboe.ttl"
# → {"valid": true, "issues": []}
```

Any finding sets `valid: false` and lists the issues with an `[L1]` /
`[L2]` / `[L3]` prefix. Reference ontologies are loaded once at
service start from `$KARMA_ONTOLOGIES_DIR` (default
`/app/ontologies` in the container, `examples/ontologies/` locally);
drop additional `.owl` / `.ttl` files in there to extend L3 coverage
(e.g. Darwin Core, ABCD, BiodivOntology once the upstream artefacts
are available).

## Karma

The transformation runs [Web-Karma's](https://github.com/usc-isi-i2/Web-Karma)
`OfflineRdfGenerator` as a JVM subprocess. Upstream was archived
2025-04-16, so we build the shaded JAR ourselves. Upstream's bundling
ships ~250 MB of payload (Spark, Hadoop, POI, JDBC, …) the CSV→RDF code
path never touches; the Dockerfile post-trims that down to ~166 MB,
verified isomorphic against the InfAI ground-truth sample.

## Docker build modes

Default — build the JAR inline:

```bash
docker build -t sp-wp8 .
```

Once the `Build Karma JAR` workflow has run at least once, the JAR can
be downloaded instead (~5 s, no JDK needed in the build env):

```bash
docker build -t sp-wp8 \
  --build-arg KARMA_BUILD_STAGE=karma-from-url \
  --build-arg KARMA_JAR_URL=https://github.com/MatteoDrso/rdf-matching-and-transformation-service/releases/download/karma-jar-latest/karma-offline-shaded.jar \
  .
```

## Karma JAR via GitHub Actions

`.github/workflows/build-karma-jar.yml` builds the trimmed JAR on demand
and publishes it as a GitHub Release asset. Trigger from the GitHub UI:
**Actions → Build Karma JAR → Run workflow**. Inputs are `karma_ref`
(default `master`) and `release_tag_suffix` (default = today's date in
UTC).

After ~2–3 min two Releases appear under the **Releases** tab:
`karma-jar-<date>` (immutable) and `karma-jar-latest` (floating alias —
its asset URL stays constant across reruns, which is what the URL build
mode above consumes). The workflow references `${{ github.repository }}`,
so moving this repo into another GitHub org (e.g. the nf-core pipeline)
needs no changes inside the workflow file itself — only the sample URL
above and the Dockerfile comment.

## Local development

```bash
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pytest                                    # 7 tests, ~1 s
uvicorn main:app --reload                 # local server on :8000
```

The integration test `test_transform_infai_sample_matches_ground_truth`
self-skips unless either `KARMA_JAR` is set or
`lib/karma-offline-*-shaded.jar` exists. To populate `lib/`, either
clone Web-Karma and run `mvn -P shaded -pl karma-offline -am package`,
or download the published JAR asset.

## Pipeline context

```
Input data ──► WP1 nf-core pipeline ──────────────────► Output (RDF)
                                  ▲   ▲   ▲   ▲   ▲   ▲
                                 WP2 WP3 WP4 WP5 WP6 WP7 WP8 (this repo)
```

WP8 consumes the standardised, quality-checked dataset from WP2–WP6 and
a Karma R2RML mapping model from the WP7 Schema Editor, and emits RDF
for downstream consumers (NFDI knowledge graph).

## Ontologies

Primary: [OBOE 1.2](http://ecoinformatics.org/oboe/oboe.1.2/) — each row
becomes an `ObservationCollection` with `Observation` → `Measurement` →
`MeasuredValue` of an `Entity` (taxon, Catalogue of Life URI) for a
`Characteristic` (trait, TOP Thesaurus) in a `Unit` (QUDT). Secondary
alignment targets per the Lastenheft — Darwin Core RDF, ABCD,
BiodivOntology — are modelled in the WP7 cross-walks and will be
validated by `/validate` once wired up.

## Repo layout

```
.
├── .github/workflows/build-karma-jar.yml   # JAR build + release workflow
├── Dockerfile                              # two build modes (source / url)
├── main.py                                 # uvicorn entrypoint
├── src/
│   ├── api/                                # routes + pydantic models
│   └── core/karma_runner.py                # Karma subprocess wrapper
├── examples/                               # InfAI sample + ground truth
├── tests/                                  # pytest (mocks subprocess)
└── nextflow/                               # nf-core module (planned)
```

## References

- [Web-Karma](https://github.com/usc-isi-i2/Web-Karma) (archived 2025-04-16)
- [Batch Mode for RDF Generation](https://github.com/usc-isi-i2/Web-Karma/wiki/Batch-Mode-for-RDF-Generation) — Karma CLI flag reference
- [OBOE 1.2](http://ecoinformatics.org/oboe/oboe.1.2/)
- [BiodivPipeline (nf-core)](https://nf-co.re)

## Contact

InfAI — Naouel Karam (`karam@infai.org`), Jan Fillies (`fillies@infai.org`).
