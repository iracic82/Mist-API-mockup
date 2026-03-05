"""
Organization endpoint handler for Mock Mist API.

Handles:
- GET /api/v1/orgs/{org_id}
"""

import json
import logging
from typing import Any

from db.dynamodb import DynamoDBClient, ENTITY_ORGANIZATION

logger = logging.getLogger(__name__)


def _response(status_code: int, body: Any, extra_headers: dict = None) -> dict:
    """Create API Gateway response."""
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
    }
    if extra_headers:
        headers.update(extra_headers)
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body) if body is not None else "",
    }


def get_organization(topology: str, org_id: str) -> dict:
    """
    Get organization details by ID.

    Args:
        topology: Active topology name
        org_id: Organization UUID

    Returns:
        API Gateway response with organization data
    """
    logger.info(f"Getting organization {org_id} for topology: {topology}")

    db = DynamoDBClient()
    org = db.get_entity(topology, ENTITY_ORGANIZATION, org_id)

    if not org:
        return _response(404, {"detail": f"Organization {org_id} not found"})

    return _response(200, org)
