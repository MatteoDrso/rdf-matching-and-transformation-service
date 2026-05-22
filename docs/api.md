# API Reference

## `GET /`

Health check.

```json
{ "status": "ok", "version": "0.1.0", "ontologies": [] }
```

## `GET /schemas`

List supported mapping schema formats.

```json
{ "formats": ["karma-r2rml-ttl"] }
```

## `POST /transform`

Transform a dataset + mapping schema into RDF using the Karma
`OfflineRdfGenerator` under the hood.

**Request (multipart/form-data):**

| Field            | Type | Required | Default | Notes                                       |
| ---------------- | ---- | -------- | ------- | ------------------------------------------- |
| `dataset`        | file | yes      | —       | CSV / TSV / JSON / XML                      |
| `mapping_schema` | file | yes      | —       | Karma R2RML model (`*-model.ttl`)           |
| `source_type`    | str  | no       | `CSV`   | `CSV`, `JSON`, `XML`, `DB`                  |
| `delimiter`      | str  | no       | `COMMA` | `COMMA`, `TAB`, `;`, …                      |
| `source_name`    | str  | no       | `source`| Logical source name referenced in the model |
| `output_format`  | str  | no       | `turtle`| `turtle`, `ntriples`, `jsonld`              |
| `encoding`       | str  | no       | —       | File encoding, e.g. `UTF-8`, `ISO-8859-1`   |
| `text_qualifier` | str  | no       | —       | CSV quote char (e.g. `"`)                   |
| `header_index`   | int  | no       | —       | 1-based row where CSV header lives          |
| `data_index`     | int  | no       | —       | 1-based row where CSV data begins           |
| `selection`      | str  | no       | —       | Named selection inside the Karma model      |

The five optional fields mirror Karma's `--encoding`, `--textqualifier`,
`--headerindex`, `--dataindex`, and `--selection` CLI flags from the
[Batch-Mode wiki](https://github.com/usc-isi-i2/Web-Karma/wiki/Batch-Mode-for-RDF-Generation).
They are forwarded to the JAR only when set; otherwise Karma uses its
built-in defaults.

**Response:**
- `200 OK` with the generated RDF (`Content-Type` matches `output_format`)
- `400` with a structured `{ "message", "returncode", "stderr" }` if Karma
  reports a mapping or parse failure, or an unsupported `output_format`
- `503` if the Karma JAR or a working Java runtime cannot be located
- `504` if the Karma subprocess exceeds the 300 s timeout

## `POST /validate`

Validate a mapping schema against the loaded ontologies.
Currently `501 Not Implemented` — see WP8 work-item 9.
