"""Validate a Karma R2RML mapping model against the loaded ontologies.

Three checks, layered from cheap to substantive:

  L1 — Turtle syntactic validity (`rdflib.Graph().parse()` succeeds).
  L2 — Karma structural sanity (the file declares a `km-dev:R2RMLMapping`
       with a `km-dev:sourceName`; rules out random Turtle uploads).
  L3 — ontology-term alignment: every IRI the model references in a
       namespace owned by a loaded ontology must be a term declared by
       that ontology. Flags typos and references to renamed / removed
       upstream classes.

L1 and L2 failures set `valid=false` and short-circuit further checks
(no point doing alignment on a file we can't parse). L3 findings also
set `valid=false` so a single boolean answers "should I run /transform
against this model?".
"""
from __future__ import annotations

from dataclasses import dataclass, field

from rdflib import Graph, URIRef

from src.core.ontology_loader import LoadedOntologies, term_namespace

KARMA_R2RML_MAPPING = URIRef("http://isi.edu/integration/karma/dev#R2RMLMapping")
KARMA_SOURCE_NAME = URIRef("http://isi.edu/integration/karma/dev#sourceName")


@dataclass
class ValidationResult:
    valid: bool
    issues: list[str] = field(default_factory=list)


def validate_model(model_bytes: bytes, ontologies: LoadedOntologies) -> ValidationResult:
    """Run L1+L2+L3 over `model_bytes` and return a structured result."""
    # L1 — Turtle parse.
    graph = Graph()
    try:
        graph.parse(data=model_bytes, format="turtle")
    except Exception as exc:
        return ValidationResult(
            valid=False,
            issues=[f"[L1] Turtle parse failed: {exc}"],
        )

    issues: list[str] = []

    # L2 — Karma structural sanity. The model must declare exactly one
    # km-dev:R2RMLMapping resource (Karma puts one per file), and that
    # resource must carry a km-dev:sourceName.
    mappings = list(graph.subjects(predicate=URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                                   object=KARMA_R2RML_MAPPING))
    if not mappings:
        issues.append(
            "[L2] No `km-dev:R2RMLMapping` resource found — this does not "
            "look like a Karma R2RML mapping model."
        )
    else:
        without_source = [m for m in mappings if not any(graph.objects(m, KARMA_SOURCE_NAME))]
        if without_source:
            issues.append(
                f"[L2] {len(without_source)} `km-dev:R2RMLMapping` resource(s) "
                "have no `km-dev:sourceName` — Karma needs this to bind data."
            )

    # If L2 failed outright (no Karma mapping resource at all), L3 won't
    # yield anything useful — bail.
    if not mappings:
        return ValidationResult(valid=False, issues=issues)

    # L3 — ontology-term alignment. Walk every IRI referenced by the
    # model. For each IRI whose namespace is owned by a loaded ontology,
    # check it's declared there.
    if ontologies.is_empty:
        issues.append(
            "[L3] No ontologies are loaded; skipping ontology-alignment check. "
            "Set KARMA_ONTOLOGIES_DIR or drop .owl files into the configured "
            "directory to enable L3."
        )
        return ValidationResult(valid=not issues, issues=issues)

    unknown: list[str] = []
    seen: set[str] = set()
    for triple in graph:
        for node in triple:
            if not isinstance(node, URIRef):
                continue
            iri = str(node)
            if iri in seen:
                continue
            seen.add(iri)
            ns = term_namespace(iri)
            if ns is None or ns not in ontologies.namespaces:
                continue
            if iri not in ontologies.defined:
                unknown.append(iri)

    for iri in sorted(unknown):
        issues.append(
            f"[L3] `{iri}` is referenced but not declared by any loaded "
            f"ontology (namespace {term_namespace(iri)} is owned by "
            f"{', '.join(sorted(ontologies.sources))})."
        )

    return ValidationResult(valid=not issues, issues=issues)
