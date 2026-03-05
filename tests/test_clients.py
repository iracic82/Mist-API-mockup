"""
Tests for client endpoints.
"""

import json
import pytest
from unittest.mock import patch

from app import lambda_handler


@pytest.fixture
def mock_db_client():
    with patch("handlers.clients.DynamoDBClient") as mock:
        yield mock


@pytest.fixture
def wireless_event():
    return {
        "httpMethod": "GET",
        "path": "/api/v1/sites/site-abc/stats/clients",
        "headers": {"Authorization": "Token test-api-key-12345"},
        "queryStringParameters": {"wired": "false", "limit": "1000"},
        "pathParameters": {"site_id": "site-abc"},
        "body": None,
    }


@pytest.fixture
def wired_event():
    return {
        "httpMethod": "GET",
        "path": "/api/v1/sites/site-abc/wired_clients/search",
        "headers": {"Authorization": "Token test-api-key-12345"},
        "queryStringParameters": {"limit": "100"},
        "pathParameters": {"site_id": "site-abc"},
        "body": None,
    }


class TestListWirelessClients:
    def test_returns_wireless_clients(self, mock_db_client, wireless_event):
        mock_site = {"id": "site-abc", "name": "HQ"}
        mock_clients = [
            {"mac": "aabbccddeeff", "hostname": "LAPTOP-001", "ssid": "Corporate"},
            {"mac": "112233445566", "hostname": "IPHONE-002", "ssid": "Guest"},
        ]

        mock_db = mock_db_client.return_value
        mock_db.get_entity.return_value = mock_site
        mock_db.get_entities_by_parent.return_value = mock_clients

        response = lambda_handler(wireless_event, None)

        assert response["statusCode"] == 200
        assert response["headers"]["X-Page-Total"] == "2"
        body = json.loads(response["body"])
        assert len(body) == 2

    def test_returns_404_for_nonexistent_site(self, mock_db_client, wireless_event):
        mock_db_client.return_value.get_entity.return_value = None

        response = lambda_handler(wireless_event, None)

        assert response["statusCode"] == 404


class TestSearchWiredClients:
    def test_returns_wired_clients_envelope(self, mock_db_client, wired_event):
        mock_site = {"id": "site-abc", "name": "HQ"}
        mock_clients = [
            {"mac": "aabbccddeeff", "ip": ["10.10.0.5"], "site_id": "site-abc"},
        ]

        mock_db = mock_db_client.return_value
        mock_db.get_entity.return_value = mock_site
        mock_db.get_entities_by_parent.return_value = mock_clients

        response = lambda_handler(wired_event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert "results" in body
        assert "total" in body
        assert "limit" in body
        assert "next" in body
        assert "start" in body
        assert "end" in body
        assert body["total"] == 1
        assert len(body["results"]) == 1

    def test_pagination_next_url(self, mock_db_client, wired_event):
        """When more results than limit, next URL should be present."""
        mock_site = {"id": "site-abc", "name": "HQ"}
        # Create more clients than limit
        wired_event["queryStringParameters"]["limit"] = "2"
        mock_clients = [
            {"mac": f"aabbccddee{i:02x}", "ip": [f"10.10.0.{i}"], "site_id": "site-abc"}
            for i in range(5)
        ]

        mock_db = mock_db_client.return_value
        mock_db.get_entity.return_value = mock_site
        mock_db.get_entities_by_parent.return_value = mock_clients

        response = lambda_handler(wired_event, None)

        body = json.loads(response["body"])
        assert body["total"] == 5
        assert body["next"] is not None
        assert "_offset=2" in body["next"]
