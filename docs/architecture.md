# Architecture Notes

> Placeholder — to be filled in as design decisions are made.

## Open Questions

- Embedded triplestore (rdflib in-memory) vs. external SPARQL endpoint for ontology alignment?
- Rule-based mapping only, or LLM-assisted alignment for ambiguous cases?
- Streaming vs. batch transformation for large BGBM datasets?
- How to surface mapping errors back to the WP1 pipeline (per-record reports vs. fail-fast)?

## Pending Inputs

- Reference RDF mapping scripts from InfAI (FU Berlin GitLab).
- Sample mapping schemas produced by the WP7 Schema Editor.
- BGBM real-world dataset for end-to-end validation.
