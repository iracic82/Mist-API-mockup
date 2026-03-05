"""
Sites endpoint handler for Mock Mist API.

Handles:
- GET /api/v1/orgs/{org_id}/sites
"""

import json
import logging
from typing import Any

from db.dynamodb import (
    DynamoDBClient,
    ENTITY_ORGANIZATION,
    ENTITY_SITE,
)

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


def list_sites(topology: str, org_id: str, query_params: dict) -> dict:
    """
    List all sites for an organization with page-based pagination.

    Pagination uses limit + page query params.
    Total count returned in X-Page-Total header.

    Args:
        topology: Active topology name
        org_id: Organization UUID
        query_params: Query parameters (limit, page)

    Returns:
        API Gateway response with list of sites
    """
    logger.info(f"Listing sites for org {org_id} in topology {topology}")

    db = DynamoDBClient()

    # Verify organization exists
    org = db.get_entity(topology, ENTITY_ORGANIZATION, org_id)
    if not org:
        return _response(404, {"detail": f"Organization {org_id} not found"})

    # Get all sites for this org
    all_sites = db.get_entities_by_parent(
        topology, ENTITY_ORGANIZATION, org_id, ENTITY_SITE
    )

    total = len(all_sites)

    # Apply pagination
    limit = int(query_params.get("limit", 1000))
    page = int(query_params.get("page", 1))
    start = (page - 1) * limit
    end = start + limit
    paginated = all_sites[start:end]

    logger.info(f"Returning {len(paginated)} of {total} sites (page {page})")
    return _response(200, paginated, {"X-Page-Total": str(total)})
