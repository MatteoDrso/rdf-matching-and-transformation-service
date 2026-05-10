# Architecture Notes

## Decisions

### D1 — Transformation engine: Web-Karma `OfflineRdfGenerator`

We wrap the open-source [Web-Karma](https://github.com/usc-isi-i2/Web-Karma)
`edu.isi.karma.rdf.OfflineRdfGenerator` (USC ISI) as a subprocess.

*Why:* InfAI already uses Karma for the reference transformation, so wrapping
it gives us reproducibility against InfAI's pipeline for free and avoids
reimplementing R2RML semantics in Python.

*Cost:* the runtime image must ship a JRE plus the shaded JAR
(`karma-spark-*-shaded.jar`). Web-Karma was archived on 16 April 2025; we
build the JAR from source once and vendor it under `lib/`.

### D2 — Mapping format: Karma R2RML model (`*-model.ttl`)

The mapping schema is a Karma-flavoured R2RML document produced by the WP7
Schema Editor. We do not invent our own JSON-LD mapping format.

*Why:* the format already encodes everything Karma needs (subject maps,
predicate-object maps, Python pre-transformations, namePrefixes for blank
nodes, base URI). Anything else would require a converter.

### D3 — Primary ontology: OBOE 1.2

Each tabular row produces an OBOE `ObservationCollection` →
`Observation` → `Measurement` → `MeasuredValue` subgraph, with `Entity`
(taxon, Catalogue of Life URI), `Characteristic` (trait, TOP Thesaurus URI)
and `Unit` (QUDT URI).

*Why:* OBOE is the favoured ontology for the BGBM trait data (per BGBM /
InfAI). It models *measurements of characteristics of entities* directly,
which matches TraitBank-style tables one-to-one.

Darwin Core RDF, ABCD and BiodivOntology remain on the reference list from
the Lastenheft and act as **secondary alignment targets**: cross-walks are
modelled in WP7 and validated by `/validate` in WP8.

## Open Questions

- Should `/validate` load OBOE + DwC + ABCD + BiodivOntology into a single
  in-memory rdflib graph, or call out to an external SPARQL endpoint?
  (Embedded for v0.1; revisit when ontology size hurts startup.)
- Streaming vs. batch transformation for large BGBM datasets — Karma's
  offline generator is a one-shot batch process. Out-of-process batching
  per request seems sufficient for now.
- Per-row error reporting: Karma emits Java stack traces; we want to surface
  them as structured JSON for the WP1 pipeline.
- Should the Nextflow module call the JAR directly, or HTTP-call the FastAPI
  service? Direct JAR call is simpler in pipelines; the REST surface remains
  for ad-hoc and UI-driven use.

## Pending Inputs

- `oboe-core.owl` (OBOE 1.2) — for `/validate` and offline alignment tests.
- Karma source revision used by InfAI, so our `mvn package` build is
  byte-equivalent.
- A WP7 Schema Editor sample export, to confirm it emits Karma-compatible
  models without a conversion layer.
