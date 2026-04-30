# API Reference

> Status: scaffolded. Endpoints respond with `501 Not Implemented` until the transformation engine is wired up.

## `GET /`

Health check. Returns service version and the list of loaded ontologies.

```json
{ "status": "ok", "version": "0.1.0", "ontologies": [] }
```

## `GET /schemas`

List supported mapping schema formats.

```json
{ "formats": ["jsonld", "turtle"] }
```

## `POST /transform`

Transform a dataset + mapping schema into RDF.

**Request (multipart/form-data):**

| Field            | Type | Required | Notes                                |
| ---------------- | ---- | -------- | ------------------------------------ |
| `dataset`        | file | yes      | CSV or JSON                          |
| `mapping_schema` | file | yes      | JSON-LD or Turtle mapping schema     |
| `output_format`  | str  | no       | `turtle` (default) or `jsonld`       |

**Response:** the generated RDF in the requested serialisation, or `400` with a structured error if a field cannot be aligned.

## `POST /validate`

Validate a mapping schema against the loaded ontologies.

```json
{ "valid": true, "issues": [] }
```
