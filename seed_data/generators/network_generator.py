"""
Network data generator for Mock Mist API.

Generates org networks and derived (site-level) networks.
"""

import random
import uuid
from datetime import datetime
from typing import Optional


# Standard org network templates
ORG_NETWORK_TEMPLATES = [
    {"name": "Corporate", "vlan_id": 10, "subnet": "10.10.0.0/16", "gateway": "10.10.0.1"},
    {"name": "Guest", "vlan_id": 20, "subnet": "10.20.0.0/16", "gateway": "10.20.0.1"},
    {"name": "IoT", "vlan_id": 30, "subnet": "10.30.0.0/16", "gateway": "10.30.0.1"},
    {"name": "Voice", "vlan_id": 40, "subnet": "10.40.0.0/16", "gateway": "10.40.0.1"},
    {"name": "Server", "vlan_id": 50, "subnet": "10.50.0.0/16", "gateway": "10.50.0.1"},
    {"name": "DMZ", "vlan_id": 60, "subnet": "10.60.0.0/16", "gateway": "10.60.0.1"},
    {"name": "Management", "vlan_id": 99, "subnet": "10.99.0.0/16", "gateway": "10.99.0.1"},
]


class NetworkGenerator:
    """Generator for Mist network data."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def generate_org_network(
        self,
        network_id: str,
        org_id: str,
        name: str,
        subnet: str,
        vlan_id: int,
        gateway: str,
    ) -> dict:
        """
        Generate an org-level network matching Mist API format.

        Key fields: id, org_id, name, subnet, vlan_id, gateway,
        disallow_mist_services, internet_access, vpn_access, tenants,
        created_time, modified_time
        """
        now = int(datetime.utcnow().timestamp())
        created = now - random.randint(86400 * 30, 86400 * 365)

        return {
            "id": network_id,
            "org_id": org_id,
            "name": name,
            "subnet": subnet,
            "vlan_id": vlan_id,
            "gateway": gateway,
            "disallow_mist_services": False,
            "internet_access": {
                "enabled": True,
                "restricted": name in ["IoT", "Guest"],
            },
            "vpn_access": {},
            "tenants": {},
            "created_time": float(created),
            "modified_time": float(now - random.randint(0, 86400 * 7)),
        }

    def generate_org_networks(self, org_id: str, seed: int = 42) -> list[dict]:
        """Generate all standard org networks."""
        networks = []
        for template in ORG_NETWORK_TEMPLATES:
            network_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{org_id}-net-{template['name']}-{seed}"))
            network = self.generate_org_network(
                network_id=network_id,
                org_id=org_id,
                name=template["name"],
                subnet=template["subnet"],
                vlan_id=template["vlan_id"],
                gateway=template["gateway"],
            )
            networks.append(network)
        return networks

    def generate_derived_network(
        self,
        network_id: str,
        site_id: str,
        org_id: str,
        name: str,
        subnet: str,
        vlan_id: int,
        gateway: str,
        site_index: int = 0,
    ) -> dict:
        """
        Generate a site-level derived network.

        Derived networks are site-resolved versions of org networks.
        The subnet is adjusted per site for uniqueness.
        """
        now = int(datetime.utcnow().timestamp())
        created = now - random.randint(86400 * 30, 86400 * 365)

        # Adjust subnet per site (e.g., 10.10.0.0/16 -> 10.10.{site_index}.0/24)
        parts = subnet.split("/")
        base = parts[0].split(".")
        site_subnet = f"{base[0]}.{base[1]}.{site_index}.0/24"
        site_gateway = f"{base[0]}.{base[1]}.{site_index}.1"

        return {
            "id": network_id,
            "org_id": org_id,
            "name": name,
            "subnet": site_subnet,
            "vlan_id": vlan_id,
            "gateway": site_gateway,
            "disallow_mist_services": False,
            "internet_access": {
                "enabled": True,
                "restricted": name in ["IoT", "Guest"],
            },
            "vpn_access": {},
            "tenants": {},
            "created_time": float(created),
            "modified_time": float(now - random.randint(0, 86400 * 7)),
        }

    def generate_derived_networks_for_site(
        self, site_id: str, org_id: str, org_networks: list[dict], site_index: int, seed: int = 42
    ) -> list[dict]:
        """Generate derived networks for a site from org network templates."""
        derived = []
        for org_net in org_networks:
            derived_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{site_id}-derived-{org_net['name']}-{seed}"))
            d = self.generate_derived_network(
                network_id=derived_id,
                site_id=site_id,
                org_id=org_id,
                name=org_net["name"],
                subnet=org_net["subnet"],
                vlan_id=org_net["vlan_id"],
                gateway=org_net["gateway"],
                site_index=site_index,
            )
            # Internal field for seeding - tracks parent site
            d["_site_id"] = site_id
            derived.append(d)
        return derived
