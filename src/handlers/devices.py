"""
Device stats endpoint handler for Mock Mist API.

Handles:
- GET /api/v1/sites/{site_id}/stats/devices
- GET /api/v1/orgs/{org_id}/stats/devices
"""

import json
import logging
from typing import Any

from db.dynamodb import (
    DynamoDBClient,
    ENTITY_ORGANIZATION,
    ENTITY_SITE,
    ENTITY_DEVICE_STATS,
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


def list_device_stats(topology: str, site_id: str, query_params: dict) -> dict:
    """
    List device stats for a site with type filtering and page-based pagination.

    Supports type filter: all, ap, switch, gateway
    Pagination uses limit + page query params.
    Total count returned in X-Page-Total header.

    Args:
        topology: Active topology name
        site_id: Site UUID
        query_params: Query parameters (type, limit, page, status)

    Returns:
        API Gateway response with list of device stats
    """
    logger.info(f"Listing device stats for site {site_id} in topology {topology}")

    db = DynamoDBClient()

    # Verify site exists
    site = db.get_entity(topology, ENTITY_SITE, site_id)
    if not site:
        return _response(404, {"detail": f"Site {site_id} not found"})

    # Get all device stats for this site
    all_devices = db.get_entities_by_parent(
        topology, ENTITY_SITE, site_id, ENTITY_DEVICE_STATS
    )

    # Apply type filter
    device_type = query_params.get("type", "all")
    if device_type and device_type != "all":
        all_devices = [d for d in all_devices if d.get("type") == device_type]

    # Apply status filter
    status_filter = query_params.get("status")
    if status_filter and status_filter != "all":
        all_devices = [d for d in all_devices if d.get("status") == status_filter]

    total = len(all_devices)

    # Apply pagination
    limit = int(query_params.get("limit", 1000))
    page = int(query_params.get("page", 1))
    start = (page - 1) * limit
    end = start + limit
    paginated = all_devices[start:end]

    logger.info(f"Returning {len(paginated)} of {total} devices (page {page}, type={device_type})")
    return _response(200, paginated, {"X-Page-Total": str(total)})


def list_org_device_stats(topology: str, org_id: str, query_params: dict) -> dict:
    """
    List device stats for an entire org (all sites).

    Fetches all sites for the org, then aggregates device stats across all sites.
    Supports the same type/status filtering and pagination as site-level endpoint.

    Args:
        topology: Active topology name
        org_id: Organization UUID
        query_params: Query parameters (type, limit, page, status)

    Returns:
        API Gateway response with list of device stats across all sites
    """
    logger.info(f"Listing org-level device stats for org {org_id} in topology {topology}")

    db = DynamoDBClient()

    # Verify org exists
    org = db.get_entity(topology, ENTITY_ORGANIZATION, org_id)
    if not org:
        return _response(404, {"detail": f"Organization {org_id} not found"})

    # Get all sites for this org
    all_sites = db.get_entities_by_parent(
        topology, ENTITY_ORGANIZATION, org_id, ENTITY_SITE
    )

    # Aggregate devices across all sites
    all_devices = []
    for site in all_sites:
        site_id = site.get("id")
        site_devices = db.get_entities_by_parent(
            topology, ENTITY_SITE, site_id, ENTITY_DEVICE_STATS
        )
        all_devices.extend(site_devices)

    # Apply type filter
    device_type = query_params.get("type", "all")
    if device_type and device_type != "all":
        all_devices = [d for d in all_devices if d.get("type") == device_type]

    # Apply status filter
    status_filter = query_params.get("status")
    if status_filter and status_filter != "all":
        all_devices = [d for d in all_devices if d.get("status") == status_filter]

    total = len(all_devices)

    # Apply pagination
    limit = int(query_params.get("limit", 1000))
    page = int(query_params.get("page", 1))
    start = (page - 1) * limit
    end = start + limit
    paginated = all_devices[start:end]

    logger.info(f"Returning {len(paginated)} of {total} org devices (page {page}, type={device_type})")
    return _response(200, paginated, {"X-Page-Total": str(total)})
