from fastapi.testclient import TestClient

from app.main import create_app


def test_health_does_not_claim_database_readiness(tmp_path):
    client = TestClient(create_app(tmp_path / 'absent'))
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'service': 'kpc-api'}


def test_built_frontend_does_not_swallow_api_errors(tmp_path):
    (tmp_path / 'index.html').write_text('<h1>KPC</h1>')
    client = TestClient(create_app(tmp_path))
    response = client.get('/api/unknown')
    assert response.status_code == 404
    assert response.headers['content-type'].startswith('application/json')


def test_spa_route_fallback_but_missing_asset_stays_missing(tmp_path):
    (tmp_path / 'index.html').write_text('<h1>KPC</h1>')
    client = TestClient(create_app(tmp_path))
    assert client.get('/workspace').status_code == 200
    assert client.get('/missing.js').status_code == 404
