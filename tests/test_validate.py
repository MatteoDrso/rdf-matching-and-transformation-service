"""Tests for the /validate endpoint and its building blocks.

Layered:
- ontology_loader against the real OBOE file in examples/ontologies/
- model_validator on synthetic + real inputs
- POST /validate end-to-end through TestClient
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.core.model_validator import validate_model
from src.core.ontology_loader import LoadedOntologies, load_ontologies_from_dir
from tests.conftest import EXAMPLES


@pytest.fixture(scope="module")
def real_ontologies() -> LoadedOntologies:
    return load_ontologies_from_dir(EXAMPLES / "ontologies")


@pytest.fixture
def real_model_bytes() -> bytes:
    return (EXAMPLES / "plant_height_vegetative_raw-model_oboe.ttl").read_bytes()


# ─── ontology_loader ─────────────────────────────────────────────────────

def test_loader_picks_up_oboe(real_ontologies):
    assert "oboe.owl" in real_ontologies.sources
    assert "http://ecoinformatics.org/oboe/oboe.1.2/oboe-core.owl#" in real_ontologies.namespaces
    assert "http://ecoinformatics.org/oboe/oboe.1.2/oboe-core.owl#Observation" in real_ontologies.defined


def test_loader_returns_empty_for_missing_dir(tmp_path):
    loaded = load_ontologies_from_dir(tmp_path / "does-not-exist")
    assert loaded.is_empty
    assert loaded.sources == ()


def test_loader_filters_non_ontology_files(tmp_path):
    (tmp_path / "README.md").write_text("not an ontology")
    (tmp_path / "notes.txt").write_text("also not")
    loaded = load_ontologies_from_dir(tmp_path)
    assert loaded.is_empty


# ─── model_validator: L1 / L2 / L3 ───────────────────────────────────────

def test_validator_accepts_real_infai_model(real_ontologies, real_model_bytes):
    result = validate_model(real_model_bytes, real_ontologies)
    assert result.valid, result.issues
    assert result.issues == []


def test_validator_flags_broken_turtle(real_ontologies):
    result = validate_model(b"@prefix this is broken", real_ontologies)
    assert not result.valid
    assert any("[L1]" in i for i in result.issues)


def test_validator_flags_non_karma_turtle(real_ontologies):
    """Valid Turtle, but not a Karma R2RML mapping model."""
    result = validate_model(
        b"@prefix ex: <http://example.org/> .\nex:s ex:p ex:o .",
        real_ontologies,
    )
    assert not result.valid
    assert any("[L2]" in i and "km-dev:R2RMLMapping" in i for i in result.issues)


def test_validator_flags_oboe_typo(real_ontologies, real_model_bytes):
    """A typo in an OBOE class name must surface as an [L3] issue."""
    bad = real_model_bytes.replace(
        b"oboe-core:Observation",
        b"oboe-core:Observatoin",
    )
    result = validate_model(bad, real_ontologies)
    assert not result.valid
    l3 = [i for i in result.issues if i.startswith("[L3]")]
    assert l3, result.issues
    assert any("Observatoin" in i for i in l3)


def test_validator_warns_when_no_ontologies_loaded(real_model_bytes):
    """If the operator forgot to mount ontologies, L3 should surface a clear
    info message rather than silently passing the model."""
    empty = LoadedOntologies()
    result = validate_model(real_model_bytes, empty)
    assert not result.valid  # the info note still flips valid → false
    assert any("[L3]" in i and "No ontologies are loaded" in i for i in result.issues)


# ─── route smoke: POST /validate end-to-end ──────────────────────────────

def test_validate_route_returns_valid_for_real_model(client, real_model_bytes):
    response = client.post(
        "/validate",
        files={"mapping_schema": ("model.ttl", real_model_bytes, "text/turtle")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["issues"] == []


def test_validate_route_surfaces_l1_error_for_broken_turtle(client):
    response = client.post(
        "/validate",
        files={"mapping_schema": ("m.ttl", b"@prefix nope", "text/turtle")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert any("[L1]" in i for i in body["issues"])


def test_health_lists_loaded_ontologies(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    # In the test harness the lifespan runs against the real examples/ontologies/
    # dir, so OBOE must appear.
    assert "oboe.owl" in body["ontologies"]
