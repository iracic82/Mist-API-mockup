"""
Maps endpoint handler for Mock Mist API.

Handles:
- GET /api/v1/sites/{site_id}/maps
"""

import json
import logging
from typing import Any

from db.dynamodb import (
    DynamoDBClient,
    ENTITY_SITE,
    ENTITY_MAP,
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


def list_site_maps(topology: str, site_id: str, query_params: dict) -> dict:
    """
    List maps for a site with page-based pagination.

    Args:
        topology: Active topology name
        site_id: Site UUID
        query_params: Query parameters (limit, page)

    Returns:
        API Gateway response with list of site maps
    """
    logger.info(f"Listing maps for site {site_id} in topology {topology}")

    db = DynamoDBClient()

    site = db.get_entity(topology, ENTITY_SITE, site_id)
    if not site:
        return _response(404, {"detail": f"Site {site_id} not found"})

    all_maps = db.get_entities_by_parent(
        topology, ENTITY_SITE, site_id, ENTITY_MAP
    )

    total = len(all_maps)

    limit = int(query_params.get("limit", 1000))
    page = int(query_params.get("page", 1))
    start = (page - 1) * limit
    end = start + limit
    paginated = all_maps[start:end]

    logger.info(f"Returning {len(paginated)} of {total} maps")
    return _response(200, paginated, {"X-Page-Total": str(total)})
