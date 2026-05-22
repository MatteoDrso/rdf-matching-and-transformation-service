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


def test_strip_placeholder_normalises_swagger_defaults():
    """Swagger UI submits literal 'string' and 0 for unset optional fields.
    The route handler must collapse those to None before calling Karma."""
    from src.api.routes import _strip_placeholder, _strip_int_placeholder

    assert _strip_placeholder(None) is None
    assert _strip_placeholder("") is None
    assert _strip_placeholder("string") is None
    assert _strip_placeholder("UTF-8") == "UTF-8"
    assert _strip_placeholder("string ") == "string "  # real value with trailing space, leave alone

    assert _strip_int_placeholder(None) is None
    assert _strip_int_placeholder(0) is None
    assert _strip_int_placeholder(1) == 1
    assert _strip_int_placeholder(42) == 42


def test_transform_does_not_forward_swagger_placeholders_to_karma(client, monkeypatch):
    """End-to-end: a POST that mirrors the curl block Swagger UI generates
    when the user only edits the file inputs must not pass --encoding=string
    etc. through to the Karma subprocess."""
    captured: dict = {}

    def fake_run_karma(**kwargs):
        captured.update(kwargs)
        from src.core.karma_runner import KarmaResult
        return KarmaResult(rdf="", stdout="", stderr="")

    monkeypatch.setattr("src.api.routes.run_karma", fake_run_karma)

    response = client.post(
        "/transform",
        files={
            "dataset": ("d.csv", b"a\tb\n1\t2\n", "text/csv"),
            "mapping_schema": ("m.ttl", b"@prefix ex: <http://example.org/> .", "text/turtle"),
        },
        data={
            "delimiter": "TAB",
            "source_name": "source",
            "source_type": "CSV",
            "output_format": "turtle",
            "encoding": "string",
            "text_qualifier": "string",
            "selection": "string",
            "header_index": "0",
            "data_index": "0",
        },
    )
    assert response.status_code == 200
    assert captured["encoding"] is None
    assert captured["text_qualifier"] is None
    assert captured["selection"] is None
    assert captured["header_index"] is None
    assert captured["data_index"] is None
