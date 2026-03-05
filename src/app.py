"""
Mock Juniper Mist API - Main Lambda Handler

Routes incoming API Gateway requests to appropriate handlers based on path and method.
Supports topology switching via header or query parameter.
"""

import json
import logging
import os
import re
from typing import Any

from middleware.auth import validate_api_key
from handlers import validation, organizations, sites, devices, networks, clients, maps, admin

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

# CORS headers for Mist API
CORS_HEADERS = "Authorization,Content-Type,X-Mock-Topology"


def lambda_handler(event: dict, context: Any) -> dict:
    """
    Main Lambda handler for all API requests.

    Routes requests based on HTTP method and path to appropriate handlers.
    Extracts topology from header or query parameter.
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        http_method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        headers = event.get("headers") or {}
        query_params = event.get("queryStringParameters") or {}
        path_params = event.get("pathParameters") or {}
        body = event.get("body")

        # Normalize headers to lowercase keys
        headers = {k.lower(): v for k, v in headers.items()}

        # Health check - no auth required
        if path == "/health":
            return _response(200, {"status": "healthy", "service": "mock-mist-api"})

        # Admin endpoints - no Mist auth required
        if path.startswith("/admin"):
            return _route_admin(http_method, path, path_params, query_params, body, headers)

        # Validate Mist API key for all other endpoints
        auth_result = validate_api_key(headers)
        if not auth_result["valid"]:
            return _response(401, {"errors": [auth_result["error"]]})

        # Extract topology selection
        topology = _get_topology(headers, query_params)

        logger.warning(f"API Call: {http_method} {path}")

        # Route to appropriate handler
        return _route_request(http_method, path, path_params, query_params, topology)

    except Exception as e:
        logger.exception(f"Unhandled error: {str(e)}")
        return _response(500, {"errors": [f"Internal server error: {str(e)}"]})


def _get_topology(headers: dict, query_params: dict) -> str:
    """Extract topology from header or query parameter, with fallback to default."""
    topology = headers.get("x-mock-topology")
    if not topology:
        topology = query_params.get("topology")
    if not topology:
        topology = os.environ.get("DEFAULT_TOPOLOGY", "campus")
    return topology


def _route_request(method: str, path: str, path_params: dict, query_params: dict, topology: str) -> dict:
    """Route API v1 requests to appropriate handlers."""

    # GET /api/v1/self
    if path == "/api/v1/self":
        return validation.get_self(topology)

    # GET /api/v1/orgs/{org_id}/sites
    org_sites_match = re.match(r"/api/v1/orgs/([^/]+)/sites", path)
    if org_sites_match:
        org_id = path_params.get("org_id") or org_sites_match.group(1)
        return sites.list_sites(topology, org_id, query_params)

    # GET /api/v1/orgs/{org_id}/networks
    org_networks_match = re.match(r"/api/v1/orgs/([^/]+)/networks", path)
    if org_networks_match:
        org_id = path_params.get("org_id") or org_networks_match.group(1)
        return networks.list_org_networks(topology, org_id, query_params)

    # GET /api/v1/orgs/{org_id}
    org_match = re.match(r"/api/v1/orgs/([^/]+)$", path)
    if org_match:
        org_id = path_params.get("org_id") or org_match.group(1)
        return organizations.get_organization(topology, org_id)

    # GET /api/v1/sites/{site_id}/stats/devices
    site_devices_match = re.match(r"/api/v1/sites/([^/]+)/stats/devices", path)
    if site_devices_match:
        site_id = path_params.get("site_id") or site_devices_match.group(1)
        return devices.list_device_stats(topology, site_id, query_params)

    # GET /api/v1/sites/{site_id}/stats/clients
    site_wireless_match = re.match(r"/api/v1/sites/([^/]+)/stats/clients", path)
    if site_wireless_match:
        site_id = path_params.get("site_id") or site_wireless_match.group(1)
        return clients.list_wireless_clients(topology, site_id, query_params)

    # GET /api/v1/sites/{site_id}/wired_clients/search
    site_wired_match = re.match(r"/api/v1/sites/([^/]+)/wired_clients/search", path)
    if site_wired_match:
        site_id = path_params.get("site_id") or site_wired_match.group(1)
        return clients.search_wired_clients(topology, site_id, query_params)

    # GET /api/v1/sites/{site_id}/networks/derived
    site_derived_match = re.match(r"/api/v1/sites/([^/]+)/networks/derived", path)
    if site_derived_match:
        site_id = path_params.get("site_id") or site_derived_match.group(1)
        return networks.list_derived_networks(topology, site_id, query_params)

    # GET /api/v1/sites/{site_id}/maps
    site_maps_match = re.match(r"/api/v1/sites/([^/]+)/maps", path)
    if site_maps_match:
        site_id = path_params.get("site_id") or site_maps_match.group(1)
        return maps.list_site_maps(topology, site_id, query_params)

    # Not found
    return _response(404, {"errors": [f"Endpoint not found: {path}"]})


def _route_admin(method: str, path: str, path_params: dict, query_params: dict, body: str, headers: dict) -> dict:
    """Route admin endpoints for topology management."""

    if path == "/admin/topologies" and method == "GET":
        return admin.list_topologies()

    if path == "/admin/topology/active" and method == "GET":
        return admin.get_active_topology()

    topology_activate_match = re.match(r"/admin/topology/([^/]+)/activate", path)
    if topology_activate_match and method == "PUT":
        topology_name = path_params.get("name") or topology_activate_match.group(1)
        return admin.activate_topology(topology_name)

    if path == "/admin/topology" and method == "POST":
        return admin.create_topology(body)

    return _response(404, {"errors": [f"Admin endpoint not found: {path}"]})


def _response(status_code: int, body: Any, extra_headers: dict = None) -> dict:
    """Create API Gateway response with proper headers."""
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": CORS_HEADERS,
    }
    if extra_headers:
        headers.update(extra_headers)
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body) if body else "",
    }
