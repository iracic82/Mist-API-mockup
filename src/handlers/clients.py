"""
Client endpoint handlers for Mock Mist API.

Handles:
- GET /api/v1/sites/{site_id}/stats/clients (wireless)
- GET /api/v1/sites/{site_id}/wired_clients/search
"""

import json
import logging
import time
from typing import Any

from db.dynamodb import (
    DynamoDBClient,
    ENTITY_SITE,
    ENTITY_WIRELESS_CLIENT,
    ENTITY_WIRED_CLIENT,
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


def list_wireless_clients(topology: str, site_id: str, query_params: dict) -> dict:
    """
    List wireless client stats for a site.

    Returns a bare JSON array. Pagination uses limit param.
    Total count returned in X-Page-Total header.

    Args:
        topology: Active topology name
        site_id: Site UUID
        query_params: Query parameters (wired, limit)

    Returns:
        API Gateway response with list of wireless client stats
    """
    logger.info(f"Listing wireless clients for site {site_id} in topology {topology}")

    db = DynamoDBClient()

    site = db.get_entity(topology, ENTITY_SITE, site_id)
    if not site:
        return _response(404, {"detail": f"Site {site_id} not found"})

    all_clients = db.get_entities_by_parent(
        topology, ENTITY_SITE, site_id, ENTITY_WIRELESS_CLIENT
    )

    total = len(all_clients)

    # Apply limit (wireless clients use limit only, no page param per API spec)
    limit = int(query_params.get("limit", 1000))
    paginated = all_clients[:limit]

    logger.info(f"Returning {len(paginated)} of {total} wireless clients")
    return _response(200, paginated, {"X-Page-Total": str(total)})


def search_wired_clients(topology: str, site_id: str, query_params: dict) -> dict:
    """
    Search wired clients at a site.

    Uses link-based pagination with `next` field in response body.
    Response envelope: {results, total, limit, next, start, end}

    Args:
        topology: Active topology name
        site_id: Site UUID
        query_params: Query parameters (limit, start, end, etc.)

    Returns:
        API Gateway response with wired client search results
    """
    logger.info(f"Searching wired clients for site {site_id} in topology {topology}")

    db = DynamoDBClient()

    site = db.get_entity(topology, ENTITY_SITE, site_id)
    if not site:
        return _response(404, {"detail": f"Site {site_id} not found"})

    all_clients = db.get_entities_by_parent(
        topology, ENTITY_SITE, site_id, ENTITY_WIRED_CLIENT
    )

    total = len(all_clients)
    limit = int(query_params.get("limit", 1000))

    # Link-based pagination using start/end epoch timestamps as opaque tokens
    # For the mock, we use a simple offset encoded in the 'start' param
    offset = int(query_params.get("_offset", 0))
    paginated = all_clients[offset:offset + limit]

    now = int(time.time())
    start_ts = now - 86400  # 24h ago
    end_ts = now

    # Build next URL if there are more results
    next_url = None
    if offset + limit < total:
        next_offset = offset + limit
        next_url = f"/api/v1/sites/{site_id}/wired_clients/search?limit={limit}&_offset={next_offset}"

    response_body = {
        "results": paginated,
        "total": total,
        "limit": limit,
        "next": next_url,
        "start": start_ts,
        "end": end_ts,
    }

    logger.info(f"Returning {len(paginated)} of {total} wired clients")
    return _response(200, response_body)
