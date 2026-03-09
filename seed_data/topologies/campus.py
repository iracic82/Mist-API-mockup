"""
Campus Topology Generator for Mock Mist API.

Generates a realistic enterprise campus topology with:
- 1 Organization ("Acme Corporation")
- 13 Sites across US locations
- ~100 devices (APs, switches, gateways)
- ~500 wireless clients, ~500 wired clients
- 7 org networks, derived per site
- ~25 maps (floor plans)
"""

import uuid

from seed_data.generators.organization_generator import OrganizationGenerator
from seed_data.generators.site_generator import SiteGenerator, US_LOCATIONS
from seed_data.generators.device_generator import DeviceGenerator
from seed_data.generators.network_generator import NetworkGenerator
from seed_data.generators.client_generator import ClientGenerator
from seed_data.generators.map_generator import MapGenerator


def generate_campus_topology(seed: int = 42) -> dict:
    """
    Generate complete campus topology data.

    Returns:
        Dictionary with all topology data organized by entity type
    """
    org_gen = OrganizationGenerator(seed=seed)
    site_gen = SiteGenerator(seed=seed)
    device_gen = DeviceGenerator(seed=seed)
    network_gen = NetworkGenerator(seed=seed)
    client_gen = ClientGenerator(seed=seed)
    map_gen = MapGenerator(seed=seed)

    # Result containers
    user_selfs = []
    organizations = []
    sites = []
    device_stats = []
    org_networks = []
    wireless_clients = []
    wired_clients = []
    derived_networks = []
    maps = []

    # ====================================
    # Organization
    # ====================================
    org_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"acme-corp-{seed}"))
    org = org_gen.generate_organization(org_id=org_id, name="Acme Corporation")
    organizations.append(org)

    # User self
    user_self = org_gen.generate_user_self(
        email="admin@acme.com",
        first_name="Admin",
        last_name="User",
        org_id=org_id,
        org_name="Acme Corporation",
    )
    user_selfs.append(user_self)

    # ====================================
    # Org Networks
    # ====================================
    org_nets = network_gen.generate_org_networks(org_id=org_id, seed=seed)
    org_networks.extend(org_nets)

    # ====================================
    # Sites
    # ====================================
    site_configs = [
        # Large sites
        {
            "name": "HQ-Building-A", "location_idx": 0,  # San Jose
            "devices": {
                "gateways": [{"model": "SRX345", "name": "HQ-A-GW-01"}],
                "switches": [{"model": "EX4400-48T", "count": 2, "name_prefix": "HQ-A-SW"}],
                "aps": [{"model": "AP45", "count": 15, "name_prefix": "HQ-A-AP"}],
            },
            "maps": 3, "wireless_clients": 120, "wired_clients": 80,
        },
        {
            "name": "HQ-Building-B", "location_idx": 0,  # San Jose
            "devices": {
                "gateways": [{"model": "SRX320", "name": "HQ-B-GW-01"}],
                "switches": [{"model": "EX4300-48T", "count": 1, "name_prefix": "HQ-B-SW"}],
                "aps": [{"model": "AP43", "count": 8, "name_prefix": "HQ-B-AP"}],
            },
            "maps": 2, "wireless_clients": 60, "wired_clients": 40,
        },
        {
            "name": "DC-East", "location_idx": 1,  # New York
            "devices": {
                "gateways": [{"model": "SRX1500", "name": "DC-E-GW-01"}],
                "switches": [{"model": "EX4650-48Y", "count": 4, "name_prefix": "DC-E-SW"}],
                "aps": [{"model": "AP33", "count": 2, "name_prefix": "DC-E-AP"}],
            },
            "maps": 2, "wireless_clients": 10, "wired_clients": 200,
        },
        # Medium branches
        {
            "name": "Branch-Chicago", "location_idx": 2,
            "devices": {
                "gateways": [{"model": "SRX320", "name": "CHI-GW-01"}],
                "switches": [{"model": "EX2300-24T", "count": 1, "name_prefix": "CHI-SW"}],
                "aps": [{"model": "AP33", "count": 4, "name_prefix": "CHI-AP"}],
            },
            "maps": 1, "wireless_clients": 25, "wired_clients": 15,
        },
        {
            "name": "Branch-Austin", "location_idx": 3,
            "devices": {
                "gateways": [{"model": "SRX320", "name": "AUS-GW-01"}],
                "switches": [{"model": "EX2300-24T", "count": 1, "name_prefix": "AUS-SW"}],
                "aps": [{"model": "AP32", "count": 3, "name_prefix": "AUS-AP"}],
            },
            "maps": 1, "wireless_clients": 20, "wired_clients": 10,
        },
        # Small branches
        {
            "name": "Branch-Seattle", "location_idx": 4,
            "devices": {
                "gateways": [{"model": "SRX320", "name": "SEA-GW-01"}],
                "switches": [{"model": "EX2300-24T", "count": 1, "name_prefix": "SEA-SW"}],
                "aps": [{"model": "AP34", "count": 3, "name_prefix": "SEA-AP"}],
            },
            "maps": 1, "wireless_clients": 18, "wired_clients": 12,
        },
        {
            "name": "Branch-Denver", "location_idx": 5,
            "devices": {
                "gateways": [{"model": "SRX320", "name": "DEN-GW-01"}],
                "switches": [{"model": "EX2300-24T", "count": 1, "name_prefix": "DEN-SW"}],
                "aps": [{"model": "AP32", "count": 2, "name_prefix": "DEN-AP"}],
            },
            "maps": 1, "wireless_clients": 15, "wired_clients": 10,
        },
        {
            "name": "Branch-Boston", "location_idx": 6,
            "devices": {
                "gateways": [{"model": "SRX320", "name": "BOS-GW-01"}],
                "switches": [{"model": "EX2300-24T", "count": 1, "name_prefix": "BOS-SW"}],
                "aps": [{"model": "AP33", "count": 3, "name_prefix": "BOS-AP"}],
            },
            "maps": 1, "wireless_clients": 20, "wired_clients": 12,
        },
        {
            "name": "Branch-Atlanta", "location_idx": 7,
            "devices": {
                "gateways": [{"model": "SSR120", "name": "ATL-GW-01"}],
                "switches": [{"model": "EX2300-24T", "count": 1, "name_prefix": "ATL-SW"}],
                "aps": [{"model": "AP24", "count": 2, "name_prefix": "ATL-AP"}],
            },
            "maps": 1, "wireless_clients": 15, "wired_clients": 8,
        },
        {
            "name": "Branch-Miami", "location_idx": 8,
            "devices": {
                "gateways": [{"model": "SSR120", "name": "MIA-GW-01"}],
                "switches": [{"model": "EX2300-24T", "count": 1, "name_prefix": "MIA-SW"}],
                "aps": [{"model": "AP24", "count": 2, "name_prefix": "MIA-AP"}],
            },
            "maps": 1, "wireless_clients": 12, "wired_clients": 8,
        },
        {
            "name": "Branch-Dallas", "location_idx": 9,
            "devices": {
                "gateways": [{"model": "SSR130", "name": "DAL-GW-01"}],
                "switches": [{"model": "EX2300-24T", "count": 1, "name_prefix": "DAL-SW"}],
                "aps": [{"model": "AP12", "count": 2, "name_prefix": "DAL-AP"}],
            },
            "maps": 1, "wireless_clients": 12, "wired_clients": 8,
        },
        {
            "name": "Branch-Phoenix", "location_idx": 10,
            "devices": {
                "gateways": [{"model": "SSR120", "name": "PHX-GW-01"}],
                "switches": [{"model": "EX2300-24T", "count": 1, "name_prefix": "PHX-SW"}],
                "aps": [{"model": "AP12", "count": 2, "name_prefix": "PHX-AP"}],
            },
            "maps": 1, "wireless_clients": 10, "wired_clients": 5,
        },
        {
            "name": "Branch-Portland", "location_idx": 11,
            "devices": {
                "gateways": [{"model": "SSR120", "name": "PDX-GW-01"}],
                "switches": [{"model": "EX2300-24T", "count": 1, "name_prefix": "PDX-SW"}],
                "aps": [{"model": "AP12", "count": 2, "name_prefix": "PDX-AP"}],
            },
            "maps": 1, "wireless_clients": 10, "wired_clients": 5,
        },
    ]

    for i, sc in enumerate(site_configs):
        location = US_LOCATIONS[sc["location_idx"] % len(US_LOCATIONS)]
        site_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{org_id}-site-{sc['name']}-{seed}"))

        # Site
        site = site_gen.generate_site(
            site_id=site_id,
            org_id=org_id,
            name=sc["name"],
            location=location,
        )
        sites.append(site)

        # Maps
        site_maps = map_gen.generate_maps_for_site(
            site_id=site_id,
            org_id=org_id,
            count=sc["maps"],
            lat=location["lat"],
            lng=location["lng"],
            seed=seed,
        )
        maps.extend(site_maps)
        map_ids = [m["id"] for m in site_maps]

        # Devices — pass site_maps so coordinates are bounded to actual map dimensions
        site_devices = device_gen.generate_devices_for_site(
            site_id=site_id,
            org_id=org_id,
            config=sc["devices"],
            network_octet=99,
            map_ids=map_ids,
            site_maps=site_maps,
            seed=seed,
            site_index=i + 1,
        )
        device_stats.extend(site_devices)

        # Derived networks
        site_derived = network_gen.generate_derived_networks_for_site(
            site_id=site_id,
            org_id=org_id,
            org_networks=org_nets,
            site_index=i + 1,
            seed=seed,
        )
        derived_networks.extend(site_derived)

        # Wireless clients
        w_clients = client_gen.generate_wireless_clients_for_site(
            site_id=site_id,
            devices=site_devices,
            count=sc["wireless_clients"],
            site_index=i + 1,
        )
        wireless_clients.extend(w_clients)

        # Wired clients
        wr_clients = client_gen.generate_wired_clients_for_site(
            site_id=site_id,
            org_id=org_id,
            devices=site_devices,
            count=sc["wired_clients"],
            site_index=i + 1,
        )
        wired_clients.extend(wr_clients)

    return {
        "topology_name": "campus",
        "description": "Enterprise campus topology with 13 sites across the US",
        "user_selfs": user_selfs,
        "organizations": organizations,
        "sites": sites,
        "device_stats": device_stats,
        "org_networks": org_networks,
        "wireless_clients": wireless_clients,
        "wired_clients": wired_clients,
        "derived_networks": derived_networks,
        "maps": maps,
        "stats": {
            "organizations": len(organizations),
            "sites": len(sites),
            "devices": len(device_stats),
            "org_networks": len(org_networks),
            "wireless_clients": len(wireless_clients),
            "wired_clients": len(wired_clients),
            "maps": len(maps),
        },
    }
