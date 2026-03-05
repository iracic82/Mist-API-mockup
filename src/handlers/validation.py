"""
Validation endpoint handler for Mock Mist API.

Handles:
- GET /api/v1/self
"""

import json
import logging
from typing import Any

from db.dynamodb import DynamoDBClient, ENTITY_USER_SELF

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


def get_self(topology: str) -> dict:
    """
    Get the authenticated user's profile and privileges.

    Returns user info with org privileges that contain org_id values
    needed for other endpoints.

    Args:
        topology: Active topology name

    Returns:
        API Gateway response with user self data
    """
    logger.info(f"Getting self for topology: {topology}")

    db = DynamoDBClient()
    users = db.get_entities(topology, ENTITY_USER_SELF)

    if not users:
        logger.warning(f"No user_self found for topology: {topology}")
        return _response(404, {"detail": "Not found"})

    # Return the first (and typically only) user
    return _response(200, users[0])
