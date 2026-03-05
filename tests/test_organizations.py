"""
Tests for GET /api/v1/orgs/{org_id} endpoint.
"""

import json
import pytest
from unittest.mock import patch

from app import lambda_handler


@pytest.fixture
def mock_db_client():
    with patch("handlers.organizations.DynamoDBClient") as mock:
        yield mock


@pytest.fixture
def api_event():
    return {
        "httpMethod": "GET",
        "path": "/api/v1/orgs/abc-123-def",
        "headers": {
            "Authorization": "Token test-api-key-12345",
        },
        "queryStringParameters": None,
        "pathParameters": {"org_id": "abc-123-def"},
        "body": None,
    }


class TestGetOrganization:
    def test_returns_organization(self, mock_db_client, api_event):
        mock_org = {
            "id": "abc-123-def",
            "name": "Acme Corporation",
            "created_time": 1700000000,
        }
        mock_db_client.return_value.get_entity.return_value = mock_org

        response = lambda_handler(api_event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["id"] == "abc-123-def"
        assert body["name"] == "Acme Corporation"

    def test_returns_404_for_nonexistent_org(self, mock_db_client, api_event):
        mock_db_client.return_value.get_entity.return_value = None

        response = lambda_handler(api_event, None)

        assert response["statusCode"] == 404

    def test_requires_auth(self, api_event):
        api_event["headers"] = {}

        response = lambda_handler(api_event, None)

        assert response["statusCode"] == 401
