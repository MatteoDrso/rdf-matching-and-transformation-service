process RDF_TRANSFORM {
    tag "${meta.id}"
    label 'process_low'

    container "biodivpipeline/rdf-transform:0.1.0"

    input:
    tuple val(meta), path(dataset), path(schema)

    output:
    tuple val(meta), path("${meta.id}.ttl"), emit: rdf
    path "versions.yml",                     emit: versions

    script:
    def output_format = task.ext.output_format ?: 'turtle'
    """
    rdf-transform \\
        --dataset ${dataset} \\
        --schema ${schema} \\
        --output ${meta.id}.ttl \\
        --format ${output_format}

    cat <<-END_VERSIONS > versions.yml
    "${task.process}":
        rdf-transform: 0.1.0
    END_VERSIONS
    """
}
