"""
Network endpoint handlers for Mock Mist API.

Handles:
- GET /api/v1/orgs/{org_id}/networks
- GET /api/v1/sites/{site_id}/networks/derived
"""

import json
import logging
from typing import Any

from db.dynamodb import (
    DynamoDBClient,
    ENTITY_ORGANIZATION,
    ENTITY_SITE,
    ENTITY_ORG_NETWORK,
    ENTITY_DERIVED_NETWORK,
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


def list_org_networks(topology: str, org_id: str, query_params: dict) -> dict:
    """
    List organization-level networks with page-based pagination.

    Args:
        topology: Active topology name
        org_id: Organization UUID
        query_params: Query parameters (limit, page)

    Returns:
        API Gateway response with list of org networks
    """
    logger.info(f"Listing org networks for org {org_id} in topology {topology}")

    db = DynamoDBClient()

    org = db.get_entity(topology, ENTITY_ORGANIZATION, org_id)
    if not org:
        return _response(404, {"detail": f"Organization {org_id} not found"})

    all_networks = db.get_entities_by_parent(
        topology, ENTITY_ORGANIZATION, org_id, ENTITY_ORG_NETWORK
    )

    total = len(all_networks)

    limit = int(query_params.get("limit", 1000))
    page = int(query_params.get("page", 1))
    start = (page - 1) * limit
    end = start + limit
    paginated = all_networks[start:end]

    logger.info(f"Returning {len(paginated)} of {total} org networks")
    return _response(200, paginated, {"X-Page-Total": str(total)})


def list_derived_networks(topology: str, site_id: str, query_params: dict) -> dict:
    """
    List derived networks for a site.

    Derived networks apply site-level variables to the org network definitions.

    Args:
        topology: Active topology name
        site_id: Site UUID
        query_params: Query parameters (resolve)

    Returns:
        API Gateway response with list of derived networks
    """
    logger.info(f"Listing derived networks for site {site_id} in topology {topology}")

    db = DynamoDBClient()

    site = db.get_entity(topology, ENTITY_SITE, site_id)
    if not site:
        return _response(404, {"detail": f"Site {site_id} not found"})

    derived = db.get_entities_by_parent(
        topology, ENTITY_SITE, site_id, ENTITY_DERIVED_NETWORK
    )

    logger.info(f"Returning {len(derived)} derived networks")
    return _response(200, derived)
