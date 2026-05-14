# Running Tests and the Service Locally

Quick reference for running WP8 locally. Assumes the Karma JAR is built and
placed under `lib/` (see [`lib/README.md`](../lib/README.md)) and the
project's `venv` is set up.

## One-time setup

```bash
cd ~/Projects/SP_WP8_SS26
source venv/bin/activate
pip install -r requirements.txt
```

Keep the terminal tab open — re-activating the venv only matters in new
tabs.

## Tests

```bash
pytest                                # all tests (~1 s)
pytest -v                             # verbose, shows test names
pytest tests/test_transformation.py   # just the integration test
```

Expected: **4 passed**. The Karma integration test self-skips if the JAR
or a working Java is missing, so CI without those stays green.

## Start the service

```bash
uvicorn main:app --reload
```

- Runs on http://127.0.0.1:8000
- `--reload` auto-restarts on code changes
- Stop with **Ctrl+C**

Different port: `uvicorn main:app --reload --port 8765`.

## Use the service

### Browser — Swagger UI

http://127.0.0.1:8000/docs

Click `POST /transform` → *Try it out* → pick the two files from
`examples/` → set `delimiter=TAB` → Execute. Response body is the
generated RDF.

### Terminal — curl

```bash
# Healthcheck
curl http://127.0.0.1:8000/

# Supported mapping schema formats
curl http://127.0.0.1:8000/schemas

# Real transformation with the InfAI sample
curl -X POST http://127.0.0.1:8000/transform \
  -F "dataset=@examples/plant_height_vegetative_raw_germany_20.csv" \
  -F "mapping_schema=@examples/plant_height_vegetative_raw-model_oboe.ttl" \
  -F "delimiter=TAB" \
  -F "output_format=turtle" \
  -o out.ttl

head -20 out.ttl
```

### Output formats

| `output_format` | Content-Type           | How it's produced              |
| --------------- | ---------------------- | ------------------------------ |
| `turtle`, `ttl` | `text/turtle`          | rdflib reformats Karma's NT    |
| `nt`, `ntriples`| `application/n-triples`| pass-through (Karma's native)  |
| `jsonld`        | `application/ld+json`  | rdflib reformats Karma's NT    |

## Troubleshooting

| Symptom                                     | Likely cause                       | Fix                                              |
| ------------------------------------------- | ---------------------------------- | ------------------------------------------------ |
| `503` with *"No Karma JAR found"*           | `lib/karma-spark-*-shaded.jar` missing | Build the JAR — see [`lib/README.md`](../lib/README.md) |
| `503` with *"No working Java runtime"*      | No usable JDK on the machine       | `brew install openjdk@11`                        |
| `400` with *"Karma transformation failed"*  | Mapping model and CSV don't match  | Inspect `detail.stderr` in the response          |
| `400` with *"Unsupported output_format"*    | Typo in `output_format`            | Use one from the table above                     |
| `Address already in use`                    | Another process holds port 8000    | `--port 8765` or `lsof -i :8000` → `kill <pid>`  |

## Docker

The whole stack (Karma JAR + service) lives in a single image. No local
Java / Maven needed.

```bash
# Build (one-time, ~10-15 min the first time — pulls Karma deps from Maven)
docker build -t sp-wp8 .

# Run
docker run --rm -p 8000:8000 --name rdf-transform sp-wp8

# Same curl as above against http://127.0.0.1:8000
```

Pin Karma to a specific commit by overriding the build arg:
`docker build --build-arg KARMA_REF=<sha-or-branch> -t sp-wp8 .`.

## TL;DR

```bash
source venv/bin/activate
pytest                          # run tests
uvicorn main:app --reload       # run service
# new tab:
curl -X POST http://127.0.0.1:8000/transform \
  -F "dataset=@examples/plant_height_vegetative_raw_germany_20.csv" \
  -F "mapping_schema=@examples/plant_height_vegetative_raw-model_oboe.ttl" \
  -F "delimiter=TAB" -o out.ttl
```
