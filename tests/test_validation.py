"""
Tests for GET /api/v1/self endpoint.
"""

import json
import pytest
from unittest.mock import patch

from app import lambda_handler


@pytest.fixture
def mock_db_client():
    with patch("handlers.validation.DynamoDBClient") as mock:
        yield mock


@pytest.fixture
def api_event():
    return {
        "httpMethod": "GET",
        "path": "/api/v1/self",
        "headers": {
            "Authorization": "Token test-api-key-12345",
            "user-agent": "AssetInsights/1.0 Infoblox",
        },
        "queryStringParameters": None,
        "pathParameters": None,
        "body": None,
    }


class TestGetSelf:
    def test_returns_self_successfully(self, mock_db_client, api_event):
        mock_user = {
            "email": "admin@acme.com",
            "first_name": "Admin",
            "last_name": "User",
            "privileges": [
                {"scope": "org", "org_id": "abc-123", "org_name": "Acme", "role": "admin"}
            ],
        }
        mock_db_client.return_value.get_entities.return_value = [mock_user]

        response = lambda_handler(api_event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["email"] == "admin@acme.com"
        assert len(body["privileges"]) == 1

    def test_returns_404_when_no_user(self, mock_db_client, api_event):
        mock_db_client.return_value.get_entities.return_value = []

        response = lambda_handler(api_event, None)

        assert response["statusCode"] == 404

    def test_requires_auth_token(self, api_event):
        api_event["headers"] = {"user-agent": "AssetInsights/1.0 Infoblox"}

        response = lambda_handler(api_event, None)

        assert response["statusCode"] == 401

    def test_uses_topology_from_header(self, mock_db_client, api_event):
        api_event["headers"]["X-Mock-Topology"] = "test_topo"
        mock_db_client.return_value.get_entities.return_value = [{"email": "test"}]

        lambda_handler(api_event, None)

        mock_db_client.return_value.get_entities.assert_called_with("test_topo", "user_self")
