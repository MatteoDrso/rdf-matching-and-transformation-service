"""Load ontology files on service startup and index their declared IRIs.

The index backs `/validate` (L3): for each IRI a mapping model references,
we look it up against the union of terms declared by the loaded ontologies.
An IRI in a known ontology namespace but not in the declared set is a
likely typo or stale reference, which is exactly what /validate flags.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from rdflib import OWL, RDF, Graph, URIRef

logger = logging.getLogger(__name__)

_TERM_TYPES: tuple[URIRef, ...] = (
    OWL.Class,
    OWL.DatatypeProperty,
    OWL.ObjectProperty,
    OWL.AnnotationProperty,
    OWL.NamedIndividual,
    RDF.Property,
)

# Standard / meta vocabularies. We trust these IRIs unconditionally and
# never validate user models against them — and we don't want them in the
# "namespaces this service owns" set either.
_STD_NAMESPACES: frozenset[str] = frozenset({
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "http://www.w3.org/2000/01/rdf-schema#",
    "http://www.w3.org/2002/07/owl#",
    "http://www.w3.org/2001/XMLSchema#",
    "http://www.w3.org/2004/02/skos/core#",
    "http://purl.org/dc/elements/1.1/",
    "http://purl.org/dc/terms/",
    "http://xmlns.com/foaf/0.1/",
    "http://www.w3.org/2003/11/swrl#",
    "http://www.w3.org/2003/11/swrlb#",
    "http://www.w3.org/ns/r2rml#",
    "http://isi.edu/integration/karma/dev#",
})


@dataclass(frozen=True)
class LoadedOntologies:
    """In-memory index built once at startup.

    `defined` — every IRI declared as a class / property / individual by
        any loaded file.
    `namespaces` — the IRI prefixes (split at `#` or trailing `/`) those
        files own. An IRI in one of these but not in `defined` is the
        signal /validate uses to flag a typo.
    `sources` — filenames loaded, in load order.
    """
    defined: frozenset[str] = field(default_factory=frozenset)
    namespaces: frozenset[str] = field(default_factory=frozenset)
    sources: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_empty(self) -> bool:
        return not self.sources


def term_namespace(iri: str) -> str | None:
    """Split an IRI at the last `#` (preferred) or trailing `/` to get its
    namespace. Returns None for IRIs without either separator."""
    if "#" in iri:
        return iri.rsplit("#", 1)[0] + "#"
    if "/" in iri:
        return iri.rsplit("/", 1)[0] + "/"
    return None


def _default_dir() -> Path:
    explicit = os.environ.get("KARMA_ONTOLOGIES_DIR")
    if explicit:
        return Path(explicit)
    return Path(__file__).resolve().parents[2] / "examples" / "ontologies"


def load_ontologies_from_dir(path: Path | str | None = None) -> LoadedOntologies:
    """Read every .owl / .ttl / .rdf / .nt file in `path` and build the
    index. Per-file parse failures are logged but do not abort the load —
    we'd rather keep the service usable with whatever loaded successfully.
    """
    directory = Path(path) if path is not None else _default_dir()
    if not directory.is_dir():
        logger.warning(
            "Ontology directory %s does not exist; /validate L3 will be a no-op",
            directory,
        )
        return LoadedOntologies()

    sources: list[str] = []
    defined: set[str] = set()
    namespaces: set[str] = set()

    for file in sorted(directory.iterdir()):
        if file.suffix.lower() not in (".owl", ".ttl", ".rdf", ".nt"):
            continue
        graph = Graph()
        try:
            graph.parse(str(file))
        except Exception as exc:  # rdflib raises a zoo of parse errors
            logger.warning("Skipped %s: %s", file.name, exc)
            continue

        before = len(defined)
        for subject, _, obj in graph.triples((None, RDF.type, None)):
            if obj not in _TERM_TYPES or not isinstance(subject, URIRef):
                continue
            iri = str(subject)
            ns = term_namespace(iri)
            if ns is None or ns in _STD_NAMESPACES:
                continue
            defined.add(iri)
            namespaces.add(ns)
        sources.append(file.name)
        logger.info("Loaded %s: %d new terms", file.name, len(defined) - before)

    return LoadedOntologies(
        defined=frozenset(defined),
        namespaces=frozenset(namespaces),
        sources=tuple(sources),
    )
