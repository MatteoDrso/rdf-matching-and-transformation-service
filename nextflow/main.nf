// nf-core module: transform a tabular dataset + Karma R2RML model into RDF
// via the WP8 RDF Matching and Transformation Service.
//
// We use the service's own container image (published to GHCR by the
// `Build Service Image` workflow). Inside the container we start the
// FastAPI app on localhost:8000, hit /validate as a pre-flight check
// (refusing to transform if the model is broken or drifted from OBOE),
// then call /transform for the actual work. The REST detour is
// intentional: it's the same path the WP7 Schema Editor and external
// pipeline consumers use, so /transform errors look identical no matter
// who's calling.
//
// Tunables via `task.ext`:
//   output_format    'turtle' (default) | 'ntriples' | 'jsonld'
//   delimiter        'COMMA' (default) | 'TAB' | ';' | …
//   source_type      'CSV' (default) | 'JSON' | 'XML'
//   source_name      'source' (default)
//   skip_validate    false (default). Set true to bypass /validate.

process RDF_TRANSFORM {
    tag "${meta.id}"
    label 'process_low'

    container "ghcr.io/matteodrso/rdf-matching-and-transformation-service:latest"

    input:
    tuple val(meta), path(dataset), path(schema)

    output:
    tuple val(meta), path("${meta.id}.${ext}"), emit: rdf
    path "validate.json",                       emit: validate
    path "versions.yml",                        emit: versions

    script:
    def output_format = task.ext.output_format ?: 'turtle'
    def delimiter     = task.ext.delimiter     ?: 'COMMA'
    def source_type   = task.ext.source_type   ?: 'CSV'
    def source_name   = task.ext.source_name   ?: 'source'
    def skip_validate = task.ext.skip_validate ?: false
    ext = output_format == 'jsonld'
            ? 'jsonld'
            : (output_format == 'ntriples' ? 'nt' : 'ttl')
    """
    # ── Start the service on localhost (it owns the JVM lifecycle) ────────
    uvicorn main:app --host 127.0.0.1 --port 8000 \\
        --app-dir /app --log-level warning &
    SERVICE_PID=\$!
    trap "kill \$SERVICE_PID 2>/dev/null" EXIT

    # Wait until the service answers /. 30 s ceiling for OBOE-ontology
    # load on cold start.
    for i in \$(seq 1 60); do
        if curl -sf http://127.0.0.1:8000/ > /dev/null 2>&1; then break; fi
        sleep 0.5
    done

    # ── Pre-flight: /validate the model against the loaded ontologies ─────
    curl -sf -X POST http://127.0.0.1:8000/validate \\
        -F "mapping_schema=@${schema}" \\
        -o validate.json

    if [ "${skip_validate}" != "true" ]; then
        python3 -c "import json,sys; r=json.load(open('validate.json')); \\
sys.exit(0 if r['valid'] else (print('Model validation failed:', file=sys.stderr) \\
or [print(f'  {i}', file=sys.stderr) for i in r['issues']] or 1))"
    fi

    # ── Transform ─────────────────────────────────────────────────────────
    curl -sf -X POST http://127.0.0.1:8000/transform \\
        -F "dataset=@${dataset}" \\
        -F "mapping_schema=@${schema}" \\
        -F "source_type=${source_type}" \\
        -F "delimiter=${delimiter}" \\
        -F "source_name=${source_name}" \\
        -F "output_format=${output_format}" \\
        -o "${meta.id}.${ext}"

    # ── Version stamp ─────────────────────────────────────────────────────
    SERVICE_VERSION=\$(curl -sf http://127.0.0.1:8000/ | python3 -c "import json,sys;print(json.load(sys.stdin)['version'])")
    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        rdf-matching-and-transformation-service: \$SERVICE_VERSION
    END_VERSIONS
    """
}
