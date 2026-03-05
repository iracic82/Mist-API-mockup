"""
Tests for GET /api/v1/orgs/{org_id}/sites endpoint.
"""

import json
import pytest
from unittest.mock import patch

from app import lambda_handler


@pytest.fixture
def mock_db_client():
    with patch("handlers.sites.DynamoDBClient") as mock:
        yield mock


@pytest.fixture
def api_event():
    return {
        "httpMethod": "GET",
        "path": "/api/v1/orgs/abc-123/sites",
        "headers": {
            "Authorization": "Token test-api-key-12345",
        },
        "queryStringParameters": {"limit": "5", "page": "1"},
        "pathParameters": {"org_id": "abc-123"},
        "body": None,
    }


class TestListSites:
    def test_returns_sites_with_pagination(self, mock_db_client, api_event):
        mock_org = {"id": "abc-123", "name": "Acme"}
        mock_sites = [
            {"id": f"site-{i}", "name": f"Site {i}", "org_id": "abc-123"}
            for i in range(10)
        ]

        mock_db = mock_db_client.return_value
        mock_db.get_entity.return_value = mock_org
        mock_db.get_entities_by_parent.return_value = mock_sites

        response = lambda_handler(api_event, None)

        assert response["statusCode"] == 200
        assert response["headers"]["X-Page-Total"] == "10"
        body = json.loads(response["body"])
        assert len(body) == 5  # limit=5

    def test_returns_404_for_nonexistent_org(self, mock_db_client, api_event):
        mock_db_client.return_value.get_entity.return_value = None

        response = lambda_handler(api_event, None)

        assert response["statusCode"] == 404
