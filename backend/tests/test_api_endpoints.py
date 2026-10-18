"""Integration tests for FastAPI endpoints."""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data


def test_schema_endpoint():
    response = client.get("/v1/schema")
    assert response.status_code == 200
    data = response.json()
    assert "tables" in data
    table_names = [t["name"] for t in data["tables"]]
    assert "organizations" in table_names
    assert "subscriptions" in table_names


def test_query_endpoint_success():
    response = client.post("/v1/query", json={"question": "What are the top 5 organizations by revenue?"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["sql"] is not None
    assert data["confidence"] is not None
    assert data["confidence"]["percentage"] > 70
    assert len(data["rows"]) > 0


def test_query_endpoint_clarification():
    response = client.post("/v1/query", json={"question": "revenue"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "clarification"
    assert len(data["clarification_options"]) > 0


def test_query_endpoint_unanswerable():
    response = client.post("/v1/query", json={"question": "What is the weather forecast for London?"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unanswerable"
    assert data["unanswerable_reason"] is not None


def test_query_history_endpoint():
    response = client.get("/v1/history")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
