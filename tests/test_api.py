def test_health(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_schema_formats(client):
    response = client.get("/schemas")
    assert response.status_code == 200
    assert "turtle" in response.json()["formats"]
