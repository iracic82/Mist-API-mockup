"""
Scale / Benchmark Topology Generator for Mock Mist API.

This topology exists for load- and benchmark-testing the Infoblox on-prem host
(and anything else that ingests the Mist API) against a large, realistic asset
inventory.

It is a parameterised sibling of `campus.py`: it reuses the exact same entity
generators, so every benchmark asset inherits the realistic correlation the
campus topology has (VLAN segmentation, SSID->VLAN->key_mgmt, client-to-map
location, etc.). The only difference is *how many* sites/assets it produces.

────────────────────────────────────────────────────────────────────────────
THE ONE KNOB
────────────────────────────────────────────────────────────────────────────
To change the size of the benchmark, edit a SINGLE number below and open a PR:

    TARGET_ASSETS = 50000

An "asset" here means what Infoblox counts: a device OR a client
(devices + wireless_clients + wired_clients). Maps, networks, sites and the
org are scaffolding and are NOT counted as assets — exactly as in the campus
topology's documented "840 assets = devices + clients".

The generator auto-distributes TARGET_ASSETS across an appropriate number of
sites and splits each site into devices / wireless / wired using campus-like
ratios, so you never have to do the math — just pick the total.
"""

import math
import uuid

from seed_data.generators.organization_generator import OrganizationGenerator
from seed_data.generators.site_generator import SiteGenerator, US_LOCATIONS
from seed_data.generators.device_generator import DeviceGenerator
from seed_data.generators.network_generator import NetworkGenerator
from seed_data.generators.client_generator import ClientGenerator
from seed_data.generators.map_generator import MapGenerator


# ════════════════════════════════════════════════════════════════════════════
# THE SCALE KNOB — change this one number in a PR to resize the benchmark.
# ════════════════════════════════════════════════════════════════════════════
TARGET_ASSETS = 50000

# ─── Distribution shape (rarely need to touch these) ────────────────────────
# Each benchmark site has a fixed device footprint and is then filled with
# clients to reach the nominal per-site asset count. With these defaults a
# "typical" site is 15 devices + 235 clients = 250 assets, so 50,000 assets
# lands on ~200 sites — a realistic multi-site enterprise.
DEVICES_PER_SITE = 15  # 1 gateway + 2 switches + 12 APs (see _site_device_config)
NOMINAL_ASSETS_PER_SITE = 250

# Guard rails: refuse absurd values so a typo in a PR (e.g. 1_500_000) can't
# trigger a runaway multi-hour seed or an empty dataset.
MIN_TARGET_ASSETS = 100
MAX_TARGET_ASSETS = 500_000


def _validate_target(target_assets: int) -> int:
    if not isinstance(target_assets, int):
        raise TypeError(f"TARGET_ASSETS must be an int, got {type(target_assets).__name__}")
    if target_assets < MIN_TARGET_ASSETS:
        raise ValueError(
            f"TARGET_ASSETS={target_assets} is below the minimum of {MIN_TARGET_ASSETS}. "
            "Pick a larger number."
        )
    if target_assets > MAX_TARGET_ASSETS:
        raise ValueError(
            f"TARGET_ASSETS={target_assets} exceeds the safety cap of {MAX_TARGET_ASSETS}. "
            "Raise MAX_TARGET_ASSETS deliberately if you really need this much."
        )
    return target_assets


def _site_device_config(tag: str) -> dict:
    """Fixed 15-device footprint per benchmark site (matches DEVICES_PER_SITE)."""
    return {
        "gateways": [{"model": "SRX320", "name": f"{tag}-GW-01"}],
        "switches": [{"model": "EX4400-48T", "count": 2, "name_prefix": f"{tag}-SW"}],
        "aps": [{"model": "AP45", "count": 12, "name_prefix": f"{tag}-AP"}],
    }


def _plan_sites(target_assets: int) -> list[dict]:
    """
    Turn a target asset count into a list of per-site configs whose
    devices + clients sum *exactly* to target_assets.

    Strategy: pick the number of sites from the nominal per-site size, give
    every site the fixed device footprint, then spread the remaining client
    budget across sites as evenly as possible (the remainder lands on the
    first few sites). Clients are split ~50/50 wireless/wired.
    """
    num_sites = max(1, math.ceil(target_assets / NOMINAL_ASSETS_PER_SITE))
    total_devices = num_sites * DEVICES_PER_SITE
    total_clients = max(0, target_assets - total_devices)

    base_clients = total_clients // num_sites
    remainder = total_clients % num_sites

    site_configs = []
    for i in range(num_sites):
        clients_here = base_clients + (1 if i < remainder else 0)
        wireless_here = clients_here // 2
        wired_here = clients_here - wireless_here
        tag = f"BENCH-{i + 1:03d}"
        site_configs.append(
            {
                "name": f"BENCH-Site-{i + 1:03d}",
                "location_idx": i % len(US_LOCATIONS),
                "devices": _site_device_config(tag),
                "maps": 1,
                "wireless_clients": wireless_here,
                "wired_clients": wired_here,
                "floor_names": ["Office"],
            }
        )
    return site_configs


def generate_scale_topology(seed: int = 42, target_assets: int = TARGET_ASSETS) -> dict:
    """
    Generate a large benchmark topology with ~`target_assets` assets.

    The dict shape is identical to `generate_campus_topology()` so the seed
    script can write it without any special-casing.

    Args:
        seed: deterministic seed — same seed + same target = same dataset.
        target_assets: total devices + clients to generate. Defaults to the
            module-level TARGET_ASSETS constant (the PR knob).
    """
    target_assets = _validate_target(target_assets)

    org_gen = OrganizationGenerator(seed=seed)
    site_gen = SiteGenerator(seed=seed)
    device_gen = DeviceGenerator(seed=seed)
    network_gen = NetworkGenerator(seed=seed)
    client_gen = ClientGenerator(seed=seed)
    map_gen = MapGenerator(seed=seed)

    user_selfs = []
    organizations = []
    sites = []
    device_stats = []
    org_networks = []
    wireless_clients = []
    wired_clients = []
    derived_networks = []
    maps = []

    # ── Organization (distinct from campus so the two never collide) ──
    org_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"acme-benchmark-{seed}"))
    org = org_gen.generate_organization(org_id=org_id, name="Acme Benchmark Lab")
    organizations.append(org)

    user_self = org_gen.generate_user_self(
        email="admin@acme.com",
        first_name="Admin",
        last_name="User",
        org_id=org_id,
        org_name="Acme Benchmark Lab",
    )
    user_selfs.append(user_self)

    # ── Org networks (shared template, derived per site) ──
    org_nets = network_gen.generate_org_networks(org_id=org_id, seed=seed)
    org_networks.extend(org_nets)

    # ── Sites (auto-planned to hit target_assets exactly) ──
    site_configs = _plan_sites(target_assets)

    for i, sc in enumerate(site_configs):
        location = US_LOCATIONS[sc["location_idx"] % len(US_LOCATIONS)]
        site_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{org_id}-site-{sc['name']}-{seed}"))

        site = site_gen.generate_site(
            site_id=site_id,
            org_id=org_id,
            name=sc["name"],
            location=location,
        )
        sites.append(site)

        site_maps = map_gen.generate_maps_for_site(
            site_id=site_id,
            org_id=org_id,
            count=sc["maps"],
            lat=location["lat"],
            lng=location["lng"],
            seed=seed,
            site_name=sc["name"],
            floor_names=sc.get("floor_names"),
        )
        maps.extend(site_maps)
        map_ids = [m["id"] for m in site_maps]

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

        site_derived = network_gen.generate_derived_networks_for_site(
            site_id=site_id,
            org_id=org_id,
            org_networks=org_nets,
            site_index=i + 1,
            seed=seed,
        )
        derived_networks.extend(site_derived)

        w_clients = client_gen.generate_wireless_clients_for_site(
            site_id=site_id,
            devices=site_devices,
            count=sc["wireless_clients"],
            site_index=i + 1,
            site_maps=site_maps,
        )
        wireless_clients.extend(w_clients)

        wr_clients = client_gen.generate_wired_clients_for_site(
            site_id=site_id,
            org_id=org_id,
            devices=site_devices,
            count=sc["wired_clients"],
            site_index=i + 1,
        )
        wired_clients.extend(wr_clients)

    asset_count = len(device_stats) + len(wireless_clients) + len(wired_clients)

    return {
        "topology_name": "scale",
        "description": (
            f"Benchmark topology — {asset_count} assets across {len(sites)} sites "
            f"(target {target_assets})"
        ),
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
            "assets": asset_count,
        },
    }
