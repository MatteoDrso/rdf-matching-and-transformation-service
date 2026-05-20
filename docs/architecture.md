# Architecture Notes

## Decisions

### D1 — Transformation engine: Web-Karma `OfflineRdfGenerator`

We wrap the open-source [Web-Karma](https://github.com/usc-isi-i2/Web-Karma)
`edu.isi.karma.rdf.OfflineRdfGenerator` (USC ISI) as a subprocess.

*Why:* InfAI already uses Karma for the reference transformation, so wrapping
it gives us reproducibility against InfAI's pipeline for free and avoids
reimplementing R2RML semantics in Python.

*Cost:* the runtime image must ship a JRE plus the shaded JAR
(`karma-offline-*-shaded.jar`). Web-Karma was archived on 16 April 2025; we
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

### D4 — Build `karma-offline`, not `karma-spark`

`OfflineRdfGenerator` lives in the `karma-offline` module. The InfAI
reference command names `karma-spark-*-shaded.jar`, but that is just the
same class re-bundled inside `karma-spark`'s fat-JAR along with Spark,
Hadoop and Scala — none of which we use, since we invoke the class
directly via `java -cp` rather than driving it from a Spark cluster.

*Why:* building `karma-offline` instead drops Spark + Hadoop + Scala from
the artefact (~252 MB → ~40–80 MB), removes both upstream-POM patches
(no `karma-mr`, no parent-POM module toggle), and cuts the Maven build
from ~10–15 min to ~2–4 min. The JAR is byte-incompatible with the InfAI
filename but produces identical RDF — verified by isomorphism against the
ground-truth `examples/*_oboe.ttl`.

## Build Notes — Karma JAR

The detailed, validated build recipe lives in [`lib/README.md`](../lib/README.md).
Two things still bite every fresh developer:

1. **JDK 11 only.** Newer JDKs (17+) fail at compile time on parts of the
   Karma reactor. Maven also picks up the newest JDK on PATH unless
   `JAVA_HOME` is set explicitly.
2. **Use the `shaded` profile.** Plain `mvn package` produces only the
   thin 42 kB JAR; we need the fat
   `karma-offline-0.0.1-SNAPSHOT-shaded.jar` (the `shaded` classifier is
   configured inside `karma-offline/pom.xml`, so `-P shaded` alone is
   sufficient — no `-Denv=shaded` hack needed).

The local build is validated isomorphic (via `rdflib.compare`) to the
InfAI-provided ground-truth RDF for the sample dataset, so we have a
reproducible reference rather than depending on InfAI to ship binaries.

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
