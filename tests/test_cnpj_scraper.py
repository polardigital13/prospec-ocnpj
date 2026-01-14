import os
import requests

import pytest


def make_response(status_code=200, json_data=None, text=""):
    class FakeResponse:
        def __init__(self, status_code, json_data, text):
            self.status_code = status_code
            self._json = json_data
            self.text = text

        def json(self):
            return self._json

        def raise_for_status(self):
            if self.status_code != 200:
                raise requests.exceptions.HTTPError(f"{self.status_code} error")

    return FakeResponse(status_code, json_data, text)


def test_extract_items_variants():
    from cnpj_scraper import extract_items

    assert extract_items([1, 2, 3]) == [1, 2, 3]
    assert extract_items({"items": [4, 5]}) == [4, 5]
    assert extract_items({"data": [6]}) == [6]
    assert extract_items({"results": [7, 8]}) == [7, 8]
    assert extract_items({}) == []


def test_normalize_office_minimal():
    from cnpj_scraper import normalize_office

    item = {
        "taxId": "12345678000195",
        "company": {"name": "ACME Ltda"},
        "address": {
            "city": "São Paulo",
            "state": "SP",
            "street": "Rua A",
            "number": "100",
            "district": "Centro",
        },
        "mainActivity": {"id": 1234},
        "founded": "2020-01-01",
        "phone": "(11) 99999-0000",
        "email": "contato@acme.com",
    }

    normalized = normalize_office(item)

    assert normalized["cnpj"] == "12345678000195"
    assert normalized["razao_social"] == "ACME Ltda"
    assert "São Paulo" in normalized["endereco"]
    assert normalized["cnae_principal"] == 1234


def test_fetch_offices_success(monkeypatch):
    # Arrange
    fake_payload = {"items": [{"taxId": "1"}]}

    fake_resp = make_response(200, fake_payload, "ok")

    def fake_get(url, headers, params, timeout):
        assert "Authorization" in headers
        return fake_resp

    monkeypatch.setattr("cnpj_scraper.requests.get", fake_get)

    # Act
    from cnpj_scraper import fetch_offices_by_founded_range

    result = fetch_offices_by_founded_range("2020-01-01", "2020-01-01", page=1)

    # Assert
    assert result == fake_payload


def test_fetch_offices_raises_on_unauthorized(monkeypatch):
    fake_resp = make_response(401, {"error": "Unauthorized"}, "unauth")

    def fake_get(url, headers, params, timeout):
        return fake_resp

    monkeypatch.setattr("cnpj_scraper.requests.get", fake_get)

    # Patch log_event to avoid DB side effect
    monkeypatch.setattr("cnpj_scraper.log_event", lambda t, p: None)

    from cnpj_scraper import fetch_offices_by_founded_range

    with pytest.raises(requests.exceptions.HTTPError):
        fetch_offices_by_founded_range("2020-01-01", "2020-01-01")


def test_fetch_offices_no_api_key(monkeypatch, tmp_path):
    # Remove env var and reload module to pick the change
    monkeypatch.delenv("CNPJA_API_KEY", raising=False)
    import cnpj_scraper as cs
    import importlib

    importlib.reload(cs)

    with pytest.raises(RuntimeError):
        cs.fetch_offices_by_founded_range("2020-01-01", "2020-01-01")

    # Restore module state for other tests
    monkeypatch.setenv("CNPJA_API_KEY", os.getenv("CNPJA_API_KEY", "dummy-key"))
    importlib.reload(cs)
