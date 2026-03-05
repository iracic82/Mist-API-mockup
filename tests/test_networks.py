"""
Tests for network endpoints.
"""

import json
import pytest
from unittest.mock import patch

from app import lambda_handler


@pytest.fixture
def mock_db_client_org():
    with patch("handlers.networks.DynamoDBClient") as mock:
        yield mock


@pytest.fixture
def org_networks_event():
    return {
        "httpMethod": "GET",
        "path": "/api/v1/orgs/abc-123/networks",
        "headers": {"Authorization": "Token test-api-key-12345"},
        "queryStringParameters": {"limit": "1000", "page": "1"},
        "pathParameters": {"org_id": "abc-123"},
        "body": None,
    }


@pytest.fixture
def derived_networks_event():
    return {
        "httpMethod": "GET",
        "path": "/api/v1/sites/site-abc/networks/derived",
        "headers": {"Authorization": "Token test-api-key-12345"},
        "queryStringParameters": {"resolve": "true"},
        "pathParameters": {"site_id": "site-abc"},
        "body": None,
    }


class TestListOrgNetworks:
    def test_returns_org_networks(self, mock_db_client_org, org_networks_event):
        mock_org = {"id": "abc-123", "name": "Acme"}
        mock_nets = [
            {"id": "net-1", "name": "Corporate", "vlan_id": 10, "subnet": "10.10.0.0/16"},
            {"id": "net-2", "name": "Guest", "vlan_id": 20, "subnet": "10.20.0.0/16"},
        ]

        mock_db = mock_db_client_org.return_value
        mock_db.get_entity.return_value = mock_org
        mock_db.get_entities_by_parent.return_value = mock_nets

        response = lambda_handler(org_networks_event, None)

        assert response["statusCode"] == 200
        assert response["headers"]["X-Page-Total"] == "2"


class TestListDerivedNetworks:
    def test_returns_derived_networks(self, mock_db_client_org, derived_networks_event):
        mock_site = {"id": "site-abc", "name": "HQ"}
        mock_derived = [
            {"id": "dn-1", "name": "Corporate", "vlan_id": 10, "subnet": "10.10.1.0/24"},
        ]

        mock_db = mock_db_client_org.return_value
        mock_db.get_entity.return_value = mock_site
        mock_db.get_entities_by_parent.return_value = mock_derived

        response = lambda_handler(derived_networks_event, None)

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert len(body) == 1
