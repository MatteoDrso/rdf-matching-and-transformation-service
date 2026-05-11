def test_health(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_schema_formats(client):
    response = client.get("/schemas")
    assert response.status_code == 200
    assert "karma-r2rml-ttl" in response.json()["formats"]


def test_transform_rejects_unknown_output_format(client):
    response = client.post(
        "/transform",
        files={
            "dataset": ("d.csv", b"a,b\n1,2\n", "text/csv"),
            "mapping_schema": ("m.ttl", b"@prefix ex: <http://example.org/> .", "text/turtle"),
        },
        data={"output_format": "rdfxml"},
    )
    assert response.status_code == 400
    assert "Unsupported output_format" in response.json()["detail"]
