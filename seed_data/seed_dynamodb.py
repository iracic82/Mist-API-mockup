#!/usr/bin/env python3
"""
DynamoDB Seed Script for Mock Mist API

Populates DynamoDB tables with mock data for all topologies.

Usage:
    # Local DynamoDB
    python seed_dynamodb.py --local

    # AWS DynamoDB
    python seed_dynamodb.py --profile okta-sso --region eu-west-1

    # Specific topology only
    python seed_dynamodb.py --topology campus --profile okta-sso
"""

import argparse
import json
import sys
import os
from datetime import datetime

import boto3
from botocore.config import Config

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seed_data.topologies.campus import generate_campus_topology

# Entity type constants (matching src/db/dynamodb.py)
ENTITY_USER_SELF = "user_self"
ENTITY_ORGANIZATION = "organization"
ENTITY_SITE = "site"
ENTITY_DEVICE_STATS = "device_stats"
ENTITY_ORG_NETWORK = "org_network"
ENTITY_WIRELESS_CLIENT = "wireless_client"
ENTITY_WIRED_CLIENT = "wired_client"
ENTITY_DERIVED_NETWORK = "derived_network"
ENTITY_MAP = "map"


def get_dynamodb_client(local: bool = False, profile: str = None, region: str = "eu-west-1"):
    """Create DynamoDB client with appropriate configuration."""
    config = Config(
        retries={"max_attempts": 3, "mode": "standard"},
    )

    if local:
        return boto3.client(
            "dynamodb",
            endpoint_url="http://localhost:8000",
            region_name=region,
            aws_access_key_id="local",
            aws_secret_access_key="local",
            config=config,
        )
    elif profile:
        session = boto3.Session(profile_name=profile)
        return session.client("dynamodb", region_name=region, config=config)
    else:
        return boto3.client("dynamodb", region_name=region, config=config)


def create_tables_if_not_exist(client, config_table: str, data_table: str):
    """Create DynamoDB tables if they don't exist (for local development)."""
    existing_tables = client.list_tables()["TableNames"]

    if config_table not in existing_tables:
        print(f"Creating table: {config_table}")
        client.create_table(
            TableName=config_table,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        print(f"Created table: {config_table}")

    if data_table not in existing_tables:
        print(f"Creating table: {data_table}")
        client.create_table(
            TableName=data_table,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        print(f"Created table: {data_table}")


def batch_write_items(client, table_name: str, items: list, batch_size: int = 25):
    """Write items to DynamoDB in batches."""
    seen_keys = set()
    unique_items = []
    for item in items:
        key = (item["PK"]["S"], item["SK"]["S"])
        if key not in seen_keys:
            seen_keys.add(key)
            unique_items.append(item)

    if len(unique_items) < len(items):
        print(f"    (Removed {len(items) - len(unique_items)} duplicate items)")

    written = 0
    for i in range(0, len(unique_items), batch_size):
        batch = unique_items[i:i + batch_size]
        request_items = [{"PutRequest": {"Item": item}} for item in batch]

        response = client.batch_write_item(
            RequestItems={table_name: request_items}
        )

        unprocessed = response.get("UnprocessedItems", {}).get(table_name, [])
        while unprocessed:
            response = client.batch_write_item(
                RequestItems={table_name: unprocessed}
            )
            unprocessed = response.get("UnprocessedItems", {}).get(table_name, [])

        written += len(batch)

    return written


def clear_table(client, table_name: str) -> int:
    """Delete all items from a DynamoDB table."""
    deleted = 0
    paginator = client.get_paginator('scan')

    for page in paginator.paginate(
        TableName=table_name,
        ProjectionExpression='PK, SK'
    ):
        items = page.get('Items', [])
        if not items:
            continue

        for i in range(0, len(items), 25):
            batch = items[i:i + 25]
            delete_requests = [
                {'DeleteRequest': {'Key': {'PK': item['PK'], 'SK': item['SK']}}}
                for item in batch
            ]
            response = client.batch_write_item(
                RequestItems={table_name: delete_requests}
            )
            unprocessed = response.get('UnprocessedItems', {}).get(table_name, [])
            while unprocessed:
                response = client.batch_write_item(
                    RequestItems={table_name: unprocessed}
                )
                unprocessed = response.get('UnprocessedItems', {}).get(table_name, [])
            deleted += len(batch)

    return deleted


def create_item(
    topology: str,
    entity_type: str,
    entity_id: str,
    data: dict,
    parent_type: str = None,
    parent_id: str = None
) -> dict:
    """Create a DynamoDB item dictionary."""
    pk = f"{topology}#{entity_type}"
    item = {
        "PK": {"S": pk},
        "SK": {"S": str(entity_id)},
        "data": {"S": json.dumps(data)},
        "entity_type": {"S": entity_type},
        "topology": {"S": topology},
    }

    if parent_type and parent_id:
        item["GSI1PK"] = {"S": f"{topology}#{parent_type}#{parent_id}"}
        item["GSI1SK"] = {"S": f"{entity_type}#{entity_id}"}
        item["parent_id"] = {"S": str(parent_id)}
        item["parent_type"] = {"S": parent_type}

    return item


def seed_topology(client, data_table: str, topology_data: dict):
    """Seed a topology's data into DynamoDB."""
    topology_name = topology_data["topology_name"]
    print(f"\nSeeding topology: {topology_name}")
    print(f"  Stats: {topology_data['stats']}")

    items = []

    # User selfs
    for user in topology_data["user_selfs"]:
        items.append(create_item(
            topology=topology_name,
            entity_type=ENTITY_USER_SELF,
            entity_id=user["email"],
            data=user,
        ))

    # Organizations
    for org in topology_data["organizations"]:
        items.append(create_item(
            topology=topology_name,
            entity_type=ENTITY_ORGANIZATION,
            entity_id=org["id"],
            data=org,
        ))

    # Sites
    for site in topology_data["sites"]:
        items.append(create_item(
            topology=topology_name,
            entity_type=ENTITY_SITE,
            entity_id=site["id"],
            data=site,
            parent_type=ENTITY_ORGANIZATION,
            parent_id=site["org_id"],
        ))

    # Device stats
    for device in topology_data["device_stats"]:
        items.append(create_item(
            topology=topology_name,
            entity_type=ENTITY_DEVICE_STATS,
            entity_id=device["id"],
            data=device,
            parent_type=ENTITY_SITE,
            parent_id=device["site_id"],
        ))

    # Org networks
    for network in topology_data["org_networks"]:
        items.append(create_item(
            topology=topology_name,
            entity_type=ENTITY_ORG_NETWORK,
            entity_id=network["id"],
            data=network,
            parent_type=ENTITY_ORGANIZATION,
            parent_id=network["org_id"],
        ))

    # Wireless clients
    for wc in topology_data["wireless_clients"]:
        # Extract and remove internal _site_id field
        site_id = wc.pop("_site_id", "")
        items.append(create_item(
            topology=topology_name,
            entity_type=ENTITY_WIRELESS_CLIENT,
            entity_id=wc["mac"],
            data=wc,
            parent_type=ENTITY_SITE,
            parent_id=site_id,
        ))

    # Wired clients
    for wc in topology_data["wired_clients"]:
        items.append(create_item(
            topology=topology_name,
            entity_type=ENTITY_WIRED_CLIENT,
            entity_id=wc["mac"],
            data=wc,
            parent_type=ENTITY_SITE,
            parent_id=wc["site_id"],
        ))

    # Derived networks
    for network in topology_data["derived_networks"]:
        # Extract and remove internal _site_id field
        site_id = network.pop("_site_id", "")
        items.append(create_item(
            topology=topology_name,
            entity_type=ENTITY_DERIVED_NETWORK,
            entity_id=network["id"],
            data=network,
            parent_type=ENTITY_SITE,
            parent_id=site_id,
        ))

    # Maps
    for m in topology_data["maps"]:
        items.append(create_item(
            topology=topology_name,
            entity_type=ENTITY_MAP,
            entity_id=m["id"],
            data=m,
            parent_type=ENTITY_SITE,
            parent_id=m["site_id"],
        ))

    # Write all items
    print(f"  Writing {len(items)} items to DynamoDB...")
    written = batch_write_items(client, data_table, items)
    print(f"  Written {written} items")

    return written


def register_topology(client, config_table: str, topology_name: str, description: str):
    """Register a topology in the config table."""
    client.put_item(
        TableName=config_table,
        Item={
            "PK": {"S": "TOPOLOGY"},
            "SK": {"S": topology_name},
            "description": {"S": description},
            "created_at": {"S": datetime.utcnow().isoformat()},
        }
    )


def set_active_topology(client, config_table: str, topology_name: str):
    """Set the active topology."""
    client.put_item(
        TableName=config_table,
        Item={
            "PK": {"S": "CONFIG"},
            "SK": {"S": "ACTIVE_TOPOLOGY"},
            "topology_name": {"S": topology_name},
            "updated_at": {"S": datetime.utcnow().isoformat()},
        }
    )


def main():
    parser = argparse.ArgumentParser(description="Seed DynamoDB with mock Mist data")
    parser.add_argument("--local", action="store_true", help="Use local DynamoDB")
    parser.add_argument("--profile", type=str, default=None, help="AWS profile name")
    parser.add_argument("--region", type=str, default="eu-west-1", help="AWS region")
    parser.add_argument("--topology", type=str, choices=["campus", "all"], default="all",
                        help="Which topology to seed")
    parser.add_argument("--config-table", type=str, default="MistMock_Config_prod", help="Config table name")
    parser.add_argument("--data-table", type=str, default="MistMock_Data_prod", help="Data table name")
    parser.add_argument("--default-topology", type=str, default="campus", help="Default active topology")
    parser.add_argument("--clear", action="store_true", help="Clear all data from tables before seeding")

    args = parser.parse_args()

    print("=" * 60)
    print("Mock Mist API - DynamoDB Seed Script")
    print("=" * 60)

    client = get_dynamodb_client(
        local=args.local,
        profile=args.profile,
        region=args.region
    )

    print(f"\nConfiguration:")
    print(f"  Mode: {'Local' if args.local else 'AWS'}")
    print(f"  Profile: {args.profile or 'default'}")
    print(f"  Region: {args.region}")
    print(f"  Config Table: {args.config_table}")
    print(f"  Data Table: {args.data_table}")
    print(f"  Topology: {args.topology}")

    if args.local:
        print("\nCreating tables (if needed)...")
        create_tables_if_not_exist(client, args.config_table, args.data_table)

    if args.clear:
        print("\nClearing existing data...")
        config_deleted = clear_table(client, args.config_table)
        print(f"  Deleted {config_deleted} items from {args.config_table}")
        data_deleted = clear_table(client, args.data_table)
        print(f"  Deleted {data_deleted} items from {args.data_table}")

    topologies_to_seed = []

    if args.topology in ["campus", "all"]:
        print("\nGenerating campus topology...")
        topologies_to_seed.append(generate_campus_topology())

    total_items = 0
    for topology_data in topologies_to_seed:
        register_topology(
            client,
            args.config_table,
            topology_data["topology_name"],
            topology_data["description"]
        )
        items = seed_topology(client, args.data_table, topology_data)
        total_items += items

    print(f"\nSetting active topology to: {args.default_topology}")
    set_active_topology(client, args.config_table, args.default_topology)

    print("\n" + "=" * 60)
    print(f"Seeding complete! Total items: {total_items}")
    print("=" * 60)


if __name__ == "__main__":
    main()
