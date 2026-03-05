"""
Admin endpoint handlers for topology management.

Handles:
- GET /admin/topologies
- GET /admin/topology/active
- PUT /admin/topology/{name}/activate
- POST /admin/topology
"""

import json
import logging
from typing import Any

from db.dynamodb import DynamoDBClient

logger = logging.getLogger(__name__)


def _response(status_code: int, body: Any) -> dict:
    """Create API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body) if body is not None else "",
    }


def list_topologies() -> dict:
    """List all available topologies."""
    logger.info("Listing available topologies")

    db = DynamoDBClient()
    topologies = db.list_topologies()
    active = db.get_active_topology()

    result = {
        "topologies": topologies,
        "active": active,
        "count": len(topologies)
    }

    return _response(200, result)


def get_active_topology() -> dict:
    """Get the currently active topology."""
    logger.info("Getting active topology")

    db = DynamoDBClient()
    active = db.get_active_topology()

    if not active:
        return _response(200, {
            "active": None,
            "message": "No active topology set. Using default from environment."
        })

    return _response(200, {"active": active})


def activate_topology(topology_name: str) -> dict:
    """Set the active topology."""
    logger.info(f"Activating topology: {topology_name}")

    db = DynamoDBClient()

    topologies = db.list_topologies()
    if topology_name not in topologies:
        return _response(404, {
            "errors": [f"Topology '{topology_name}' not found"],
            "available": topologies
        })

    success = db.set_active_topology(topology_name)

    if success:
        return _response(200, {
            "message": f"Topology '{topology_name}' is now active",
            "active": topology_name
        })
    else:
        return _response(500, {
            "errors": ["Failed to activate topology"]
        })


def create_topology(body: str) -> dict:
    """Register a new topology."""
    logger.info("Creating new topology")

    try:
        if body:
            data = json.loads(body)
        else:
            return _response(400, {"errors": ["Request body required"]})
    except json.JSONDecodeError:
        return _response(400, {"errors": ["Invalid JSON in request body"]})

    topology_name = data.get("name")
    description = data.get("description", "")

    if not topology_name:
        return _response(400, {"errors": ["Topology 'name' is required"]})

    if not topology_name.replace("_", "").replace("-", "").isalnum():
        return _response(400, {
            "errors": ["Topology name must be alphanumeric with optional underscores/hyphens"]
        })

    db = DynamoDBClient()

    existing = db.list_topologies()
    if topology_name in existing:
        return _response(409, {
            "errors": [f"Topology '{topology_name}' already exists"]
        })

    success = db.register_topology(topology_name, description)

    if success:
        return _response(201, {
            "message": f"Topology '{topology_name}' created",
            "name": topology_name,
            "description": description
        })
    else:
        return _response(500, {
            "errors": ["Failed to create topology"]
        })
