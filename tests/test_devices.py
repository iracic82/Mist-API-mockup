"""
Tests for GET /api/v1/sites/{site_id}/stats/devices endpoint.
"""

import json
import pytest
from unittest.mock import patch

from app import lambda_handler


@pytest.fixture
def mock_db_client():
    with patch("handlers.devices.DynamoDBClient") as mock:
        yield mock


@pytest.fixture
def api_event():
    return {
        "httpMethod": "GET",
        "path": "/api/v1/sites/site-abc/stats/devices",
        "headers": {
            "Authorization": "Token test-api-key-12345",
        },
        "queryStringParameters": {"type": "all", "limit": "1000", "page": "1"},
        "pathParameters": {"site_id": "site-abc"},
        "body": None,
    }


class TestListDeviceStats:
    def test_returns_all_devices(self, mock_db_client, api_event):
        mock_site = {"id": "site-abc", "name": "HQ"}
        mock_devices = [
            {"id": "d1", "type": "ap", "model": "AP45", "status": "connected"},
            {"id": "d2", "type": "switch", "model": "EX4400-48T", "status": "connected"},
            {"id": "d3", "type": "gateway", "model": "SRX345", "status": "connected"},
        ]

        mock_db = mock_db_client.return_value
        mock_db.get_entity.return_value = mock_site
        mock_db.get_entities_by_parent.return_value = mock_devices

        response = lambda_handler(api_event, None)

        assert response["statusCode"] == 200
        assert response["headers"]["X-Page-Total"] == "3"
        body = json.loads(response["body"])
        assert len(body) == 3

    def test_filters_by_type(self, mock_db_client, api_event):
        api_event["queryStringParameters"]["type"] = "ap"
        mock_site = {"id": "site-abc", "name": "HQ"}
        mock_devices = [
            {"id": "d1", "type": "ap", "model": "AP45"},
            {"id": "d2", "type": "switch", "model": "EX4400-48T"},
        ]

        mock_db = mock_db_client.return_value
        mock_db.get_entity.return_value = mock_site
        mock_db.get_entities_by_parent.return_value = mock_devices

        response = lambda_handler(api_event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body) == 1
        assert body[0]["type"] == "ap"

    def test_returns_404_for_nonexistent_site(self, mock_db_client, api_event):
        mock_db_client.return_value.get_entity.return_value = None

        response = lambda_handler(api_event, None)

        assert response["statusCode"] == 404
