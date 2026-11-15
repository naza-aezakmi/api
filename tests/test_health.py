from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_swagger_docs() -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    assert "Swagger UI" in response.text


def test_site_origin_can_call_health() -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": "https://nasa.aezakmi.org",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://nasa.aezakmi.org"


def test_other_origin_is_not_allowed() -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_terrain_search_is_documented() -> None:
    spec = client.get("/openapi.json").json()
    assert "post" in spec["paths"]["/terrain/search"]


def test_site_origin_can_submit_terrain_search() -> None:
    response = client.options(
        "/terrain/search",
        headers={
            "Origin": "https://nasa.aezakmi.org",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://nasa.aezakmi.org"


def test_search_rejects_unsupported_planets_and_invalid_coordinates() -> None:
    for payload in (
        {"planet": "earth", "lat": 0, "lon": 0},
        {"planet": "moon", "lat": 0, "lon": 226},
        {"planet": "mars", "lat": 91, "lon": 0},
    ):
        assert client.post("/terrain/search", json=payload).status_code == 422
