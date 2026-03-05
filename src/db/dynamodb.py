"""
DynamoDB client wrapper for Mock Mist API.

Provides convenient methods for querying and managing mock data
using single-table design patterns.
"""

import os
import logging
from typing import Any, Optional
from functools import lru_cache

import boto3
from botocore.config import Config

logger = logging.getLogger(__name__)

# Entity type constants
ENTITY_USER_SELF = "user_self"
ENTITY_ORGANIZATION = "organization"
ENTITY_SITE = "site"
ENTITY_DEVICE_STATS = "device_stats"
ENTITY_ORG_NETWORK = "org_network"
ENTITY_WIRELESS_CLIENT = "wireless_client"
ENTITY_WIRED_CLIENT = "wired_client"
ENTITY_DERIVED_NETWORK = "derived_network"
ENTITY_MAP = "map"


@lru_cache(maxsize=1)
def get_dynamodb_client():
    """Get cached DynamoDB client with appropriate configuration."""
    local_endpoint = os.environ.get("DYNAMODB_LOCAL_ENDPOINT")

    config = Config(
        retries={"max_attempts": 3, "mode": "standard"},
        connect_timeout=5,
        read_timeout=10,
    )

    if local_endpoint:
        logger.info(f"Using local DynamoDB endpoint: {local_endpoint}")
        return boto3.client(
            "dynamodb",
            endpoint_url=local_endpoint,
            region_name="eu-west-1",
            config=config,
        )
    else:
        return boto3.client("dynamodb", config=config)


class DynamoDBClient:
    """High-level DynamoDB client for Mock Mist data operations."""

    def __init__(self):
        self.client = get_dynamodb_client()
        self.config_table = os.environ.get("CONFIG_TABLE", "MistMock_Config_prod")
        self.data_table = os.environ.get("DATA_TABLE", "MistMock_Data_prod")

    # ========================================
    # Configuration Operations
    # ========================================

    def get_active_topology(self) -> Optional[str]:
        """Get the currently active topology name."""
        try:
            response = self.client.get_item(
                TableName=self.config_table,
                Key={
                    "PK": {"S": "CONFIG"},
                    "SK": {"S": "ACTIVE_TOPOLOGY"}
                }
            )
            if "Item" in response:
                return response["Item"].get("topology_name", {}).get("S")
            return None
        except Exception as e:
            logger.error(f"Error getting active topology: {e}")
            return None

    def set_active_topology(self, topology_name: str) -> bool:
        """Set the active topology."""
        try:
            from datetime import datetime
            self.client.put_item(
                TableName=self.config_table,
                Item={
                    "PK": {"S": "CONFIG"},
                    "SK": {"S": "ACTIVE_TOPOLOGY"},
                    "topology_name": {"S": topology_name},
                    "updated_at": {"S": datetime.utcnow().isoformat()}
                }
            )
            return True
        except Exception as e:
            logger.error(f"Error setting active topology: {e}")
            return False

    def list_topologies(self) -> list[str]:
        """List all available topology names."""
        try:
            response = self.client.query(
                TableName=self.config_table,
                KeyConditionExpression="PK = :pk",
                ExpressionAttributeValues={
                    ":pk": {"S": "TOPOLOGY"}
                }
            )
            return [item["SK"]["S"] for item in response.get("Items", [])]
        except Exception as e:
            logger.error(f"Error listing topologies: {e}")
            return []

    def register_topology(self, topology_name: str, description: str = "") -> bool:
        """Register a new topology in the config table."""
        try:
            from datetime import datetime
            self.client.put_item(
                TableName=self.config_table,
                Item={
                    "PK": {"S": "TOPOLOGY"},
                    "SK": {"S": topology_name},
                    "description": {"S": description},
                    "created_at": {"S": datetime.utcnow().isoformat()}
                }
            )
            return True
        except Exception as e:
            logger.error(f"Error registering topology: {e}")
            return False

    # ========================================
    # Data Query Operations
    # ========================================

    def get_entities(self, topology: str, entity_type: str) -> list[dict]:
        """
        Get all entities of a given type for a topology.

        Args:
            topology: Topology name (e.g., 'campus')
            entity_type: Entity type (e.g., 'organization', 'site')

        Returns:
            List of entity data dictionaries
        """
        try:
            pk = f"{topology}#{entity_type}"
            response = self.client.query(
                TableName=self.data_table,
                KeyConditionExpression="PK = :pk",
                ExpressionAttributeValues={
                    ":pk": {"S": pk}
                }
            )
            return [self._deserialize_item(item) for item in response.get("Items", [])]
        except Exception as e:
            logger.error(f"Error getting entities: {e}")
            return []

    def get_entity(self, topology: str, entity_type: str, entity_id: str) -> Optional[dict]:
        """
        Get a specific entity by ID.

        Args:
            topology: Topology name
            entity_type: Entity type
            entity_id: Entity ID

        Returns:
            Entity data dictionary or None
        """
        try:
            pk = f"{topology}#{entity_type}"
            response = self.client.get_item(
                TableName=self.data_table,
                Key={
                    "PK": {"S": pk},
                    "SK": {"S": entity_id}
                }
            )
            if "Item" in response:
                return self._deserialize_item(response["Item"])
            return None
        except Exception as e:
            logger.error(f"Error getting entity: {e}")
            return None

    def get_entities_by_parent(
        self, topology: str, parent_type: str, parent_id: str, entity_type: str
    ) -> list[dict]:
        """
        Get entities filtered by parent relationship using GSI.

        Args:
            topology: Topology name
            parent_type: Parent entity type (e.g., 'organization')
            parent_id: Parent entity ID
            entity_type: Child entity type (e.g., 'site')

        Returns:
            List of child entity data dictionaries
        """
        try:
            gsi1pk = f"{topology}#{parent_type}#{parent_id}"
            response = self.client.query(
                TableName=self.data_table,
                IndexName="GSI1",
                KeyConditionExpression="GSI1PK = :gsi1pk AND begins_with(GSI1SK, :prefix)",
                ExpressionAttributeValues={
                    ":gsi1pk": {"S": gsi1pk},
                    ":prefix": {"S": f"{entity_type}#"}
                }
            )
            return [self._deserialize_item(item) for item in response.get("Items", [])]
        except Exception as e:
            logger.error(f"Error getting entities by parent: {e}")
            return []

    def put_entity(
        self,
        topology: str,
        entity_type: str,
        entity_id: str,
        data: dict,
        parent_type: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> bool:
        """
        Store an entity in the data table.

        Args:
            topology: Topology name
            entity_type: Entity type
            entity_id: Entity ID
            data: Entity data dictionary
            parent_type: Optional parent entity type for GSI
            parent_id: Optional parent entity ID for GSI

        Returns:
            True if successful
        """
        try:
            import json

            pk = f"{topology}#{entity_type}"
            item = {
                "PK": {"S": pk},
                "SK": {"S": entity_id},
                "data": {"S": json.dumps(data)},
                "entity_type": {"S": entity_type},
                "topology": {"S": topology}
            }

            if parent_type and parent_id:
                item["GSI1PK"] = {"S": f"{topology}#{parent_type}#{parent_id}"}
                item["GSI1SK"] = {"S": f"{entity_type}#{entity_id}"}
                item["parent_id"] = {"S": parent_id}
                item["parent_type"] = {"S": parent_type}

            self.client.put_item(TableName=self.data_table, Item=item)
            return True
        except Exception as e:
            logger.error(f"Error putting entity: {e}")
            return False

    def batch_put_entities(
        self,
        topology: str,
        entity_type: str,
        entities: list[dict],
        id_field: str = "id",
        parent_type: Optional[str] = None,
        parent_id_field: Optional[str] = None
    ) -> int:
        """
        Batch write multiple entities.

        Args:
            topology: Topology name
            entity_type: Entity type
            entities: List of entity dictionaries
            id_field: Field name for entity ID
            parent_type: Optional parent entity type
            parent_id_field: Optional field name for parent ID in entity

        Returns:
            Number of entities written
        """
        import json

        pk = f"{topology}#{entity_type}"
        written = 0

        batch_size = 25

        for i in range(0, len(entities), batch_size):
            batch = entities[i:i + batch_size]
            request_items = []

            for entity in batch:
                entity_id = str(entity.get(id_field, ""))
                if not entity_id:
                    continue

                item = {
                    "PK": {"S": pk},
                    "SK": {"S": entity_id},
                    "data": {"S": json.dumps(entity)},
                    "entity_type": {"S": entity_type},
                    "topology": {"S": topology}
                }

                if parent_type and parent_id_field:
                    parent_id = str(entity.get(parent_id_field, ""))
                    if parent_id:
                        item["GSI1PK"] = {"S": f"{topology}#{parent_type}#{parent_id}"}
                        item["GSI1SK"] = {"S": f"{entity_type}#{entity_id}"}
                        item["parent_id"] = {"S": parent_id}
                        item["parent_type"] = {"S": parent_type}

                request_items.append({"PutRequest": {"Item": item}})

            if request_items:
                try:
                    self.client.batch_write_item(
                        RequestItems={self.data_table: request_items}
                    )
                    written += len(request_items)
                except Exception as e:
                    logger.error(f"Error in batch write: {e}")

        return written

    def delete_topology_data(self, topology: str) -> int:
        """
        Delete all data for a topology.

        Args:
            topology: Topology name

        Returns:
            Number of items deleted
        """
        deleted = 0

        try:
            paginator = self.client.get_paginator("scan")
            for page in paginator.paginate(
                TableName=self.data_table,
                FilterExpression="topology = :t",
                ExpressionAttributeValues={":t": {"S": topology}},
                ProjectionExpression="PK, SK"
            ):
                items = page.get("Items", [])
                if not items:
                    continue

                for i in range(0, len(items), 25):
                    batch = items[i:i + 25]
                    delete_requests = [
                        {"DeleteRequest": {"Key": {"PK": item["PK"], "SK": item["SK"]}}}
                        for item in batch
                    ]
                    self.client.batch_write_item(
                        RequestItems={self.data_table: delete_requests}
                    )
                    deleted += len(batch)

        except Exception as e:
            logger.error(f"Error deleting topology data: {e}")

        return deleted

    def _deserialize_item(self, item: dict) -> dict:
        """Deserialize a DynamoDB item to a plain dictionary."""
        import json

        if "data" in item and "S" in item["data"]:
            return json.loads(item["data"]["S"])
        return {}
