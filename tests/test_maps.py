"""
Tests for GET /api/v1/sites/{site_id}/maps endpoint.
"""

import json
import pytest
from unittest.mock import patch

from app import lambda_handler


@pytest.fixture
def mock_db_client():
    with patch("handlers.maps.DynamoDBClient") as mock:
        yield mock


@pytest.fixture
def api_event():
    return {
        "httpMethod": "GET",
        "path": "/api/v1/sites/site-abc/maps",
        "headers": {"Authorization": "Token test-api-key-12345"},
        "queryStringParameters": {"limit": "1000", "page": "1"},
        "pathParameters": {"site_id": "site-abc"},
        "body": None,
    }


class TestListSiteMaps:
    def test_returns_site_maps(self, mock_db_client, api_event):
        mock_site = {"id": "site-abc", "name": "HQ"}
        mock_maps = [
            {"id": "map-1", "name": "Ground Floor", "type": "image", "width": 1000, "height": 800},
            {"id": "map-2", "name": "1st Floor", "type": "image", "width": 1200, "height": 900},
        ]

        mock_db = mock_db_client.return_value
        mock_db.get_entity.return_value = mock_site
        mock_db.get_entities_by_parent.return_value = mock_maps

        response = lambda_handler(api_event, None)

        assert response["statusCode"] == 200
        assert response["headers"]["X-Page-Total"] == "2"
        body = json.loads(response["body"])
        assert len(body) == 2

    def test_returns_404_for_nonexistent_site(self, mock_db_client, api_event):
        mock_db_client.return_value.get_entity.return_value = None

        response = lambda_handler(api_event, None)

        assert response["statusCode"] == 404
