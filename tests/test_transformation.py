from rdflib import Graph
from rdflib.compare import to_isomorphic

from tests.conftest import EXAMPLES, requires_karma


@requires_karma
def test_transform_infai_sample_matches_ground_truth(client):
    """End-to-end: POST /transform with the InfAI sample, compare to ground truth.

    Karma's output is isomorphic to the expected RDF (same triple set
    modulo blank-node identity).
    """
    dataset = EXAMPLES / "plant_height_vegetative_raw_germany_20.csv"
    model = EXAMPLES / "plant_height_vegetative_raw-model_oboe.ttl"
    expected = EXAMPLES / "plant_height_vegetative_raw_germany_20_oboe.ttl"

    with dataset.open("rb") as ds, model.open("rb") as mdl:
        response = client.post(
            "/transform",
            files={
                "dataset": (dataset.name, ds, "text/csv"),
                "mapping_schema": (model.name, mdl, "text/turtle"),
            },
            data={
                "source_type": "CSV",
                "delimiter": "TAB",
                "source_name": "source",
                "output_format": "turtle",
            },
        )

    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/turtle")

    got = Graph().parse(data=response.text, format="turtle")
    want = Graph().parse(source=str(expected), format="nt")

    assert len(got) == len(want)
    assert to_isomorphic(got) == to_isomorphic(want)
