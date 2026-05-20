# Running the Service

How to run WP8 locally. **Docker is the default path** — no Java, no Maven,
no Python venv needed. The native setup at the bottom is only for
contributors who change Python code and want fast iteration.

---

## 1. Docker (recommended)

Prerequisites: Docker Desktop installed and running.

```bash
git clone https://github.com/MatteoDrso/rdf-matching-and-transformation-service.git
cd rdf-matching-and-transformation-service

docker build -t sp-wp8 .                                      # 10–15 min, one-time
docker run --rm -p 8000:8000 --name rdf-transform sp-wp8      # foreground
```

That's the whole setup. Service runs on http://127.0.0.1:8000. Stop with
**Ctrl+C** — `--rm` cleans up the container automatically.

Optional: pin Karma to a specific commit at build time.

```bash
docker build --build-arg KARMA_REF=<sha-or-branch> -t sp-wp8 .
```

---

## 2. Use the service

The same three options work regardless of how the service was started.

### Browser — Swagger UI

http://127.0.0.1:8000/docs

`POST /transform` → *Try it out* → upload the two files from `examples/` →
`delimiter=TAB` → Execute. Response is the generated RDF, downloadable.

### Terminal — curl

```bash
# Healthcheck
curl http://127.0.0.1:8000/

# Real transformation with the InfAI sample (run from repo root)
curl -X POST http://127.0.0.1:8000/transform \
  -F "dataset=@examples/plant_height_vegetative_raw_germany_20.csv" \
  -F "mapping_schema=@examples/plant_height_vegetative_raw-model_oboe.ttl" \
  -F "delimiter=TAB" \
  -F "output_format=turtle" \
  -o out.ttl

head -20 out.ttl
```

### Python — notebooks / scripts

```python
import requests

with open("examples/plant_height_vegetative_raw_germany_20.csv", "rb") as ds, \
     open("examples/plant_height_vegetative_raw-model_oboe.ttl", "rb") as mdl:
    r = requests.post(
        "http://127.0.0.1:8000/transform",
        files={"dataset": ds, "mapping_schema": mdl},
        data={"delimiter": "TAB", "output_format": "turtle"},
    )
print(r.status_code, r.text[:500])
```

### Output formats

| `output_format` | Content-Type            | How it's produced            |
| --------------- | ----------------------- | ---------------------------- |
| `turtle`, `ttl` | `text/turtle`           | rdflib reformats Karma's NT  |
| `nt`, `ntriples`| `application/n-triples` | pass-through (Karma's native)|
| `jsonld`        | `application/ld+json`   | rdflib reformats Karma's NT  |

---

## 3. Troubleshooting

| Symptom                                     | Likely cause                       | Fix                                              |
| ------------------------------------------- | ---------------------------------- | ------------------------------------------------ |
| `Cannot connect to Docker daemon`           | Docker Desktop not running         | Open Docker Desktop                              |
| `Address already in use`                    | Another process holds port 8000    | `-p 8001:8000` or stop the other process         |
| `400` with *"Karma transformation failed"*  | Mapping model and CSV mismatch     | Inspect `detail.stderr` in the response          |
| `400` with *"Unsupported output_format"*    | Typo in `output_format`            | Use one from the table above                     |
| Build fails downloading Maven deps          | Bad/blocked internet               | Retry; cached layers will skip what succeeded    |

Container introspection:

```bash
docker ps                              # is it running?
docker logs rdf-transform              # what is it saying?
docker exec -it rdf-transform sh       # shell inside the container
```

---

## 4. Native setup (contributors only)

Use this if you change Python code and want a sub-second iteration loop.
The Docker image rebuild is too slow for that.

### Prerequisites

- Python 3.11
- JDK 11 (`brew install openjdk@11` on macOS)
- The Karma JAR under `lib/karma-offline-*-shaded.jar` — see
  [`lib/README.md`](../lib/README.md) for how to build it once

### Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Activate the venv in every new terminal tab (`source venv/bin/activate`).

### Tests

```bash
pytest                                # all tests (~1 s)
pytest -v                             # verbose
pytest tests/test_transformation.py   # only the integration test
```

Expected: **4 passed**. The Karma integration test self-skips if the JAR
or a working Java runtime is missing.

### Run the service

```bash
uvicorn main:app --reload             # auto-reloads on code changes
```

Different port: `uvicorn main:app --reload --port 8001`.

### Native-only error cases

| Symptom                                     | Fix                                              |
| ------------------------------------------- | ------------------------------------------------ |
| `503` *"No Karma JAR found"*                | Build the JAR — see [`lib/README.md`](../lib/README.md) |
| `503` *"No working Java runtime"*           | `brew install openjdk@11`                        |
