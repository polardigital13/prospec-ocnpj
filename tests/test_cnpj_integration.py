import requests

import pytest

from tests.test_cnpj_scraper import make_response


def test_fetch_offices_rate_limit(monkeypatch):
    fake_resp = make_response(429, {"error": "no credits"}, "no credits")

    def fake_get(url, headers, params, timeout):
        return fake_resp

    captured = {}

    def fake_log_event(t, p):
        captured["type"] = t
        captured["payload"] = p

    monkeypatch.setattr("cnpj_scraper.requests.get", fake_get)
    monkeypatch.setattr("cnpj_scraper.log_event", fake_log_event)

    from cnpj_scraper import fetch_offices_by_founded_range

    with pytest.raises(requests.exceptions.HTTPError):
        fetch_offices_by_founded_range("2020-01-01", "2020-01-01")

    assert captured.get("type") == "error"
    assert "429" in captured.get("payload", "")
