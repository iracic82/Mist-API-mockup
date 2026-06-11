"""Tests for the scale / benchmark topology generator."""

import inspect

import pytest

from seed_data.topologies.scale import (
    TARGET_ASSETS,
    MIN_TARGET_ASSETS,
    MAX_TARGET_ASSETS,
    generate_scale_topology,
)

REQUIRED_KEYS = {
    "topology_name",
    "description",
    "user_selfs",
    "organizations",
    "sites",
    "device_stats",
    "org_networks",
    "wireless_clients",
    "wired_clients",
    "derived_networks",
    "maps",
    "stats",
}


def _assets(topo: dict) -> int:
    return (
        len(topo["device_stats"])
        + len(topo["wireless_clients"])
        + len(topo["wired_clients"])
    )


@pytest.mark.parametrize("target", [500, 1000, 2500, 7500])
def test_exact_asset_count(target):
    """The generator must hit the requested asset total exactly."""
    topo = generate_scale_topology(target_assets=target)
    assert _assets(topo) == target
    assert topo["stats"]["assets"] == target


def test_topology_shape_matches_seeder_contract():
    """Shape must match what seed_dynamodb.seed_topology() iterates over."""
    topo = generate_scale_topology(target_assets=500)
    assert REQUIRED_KEYS.issubset(topo.keys())
    assert topo["topology_name"] == "scale"
    # Every entity list referenced by the seeder must be a list.
    for key in REQUIRED_KEYS - {"topology_name", "description", "stats"}:
        assert isinstance(topo[key], list)
    assert topo["sites"], "scale topology must contain at least one site"


def test_deterministic_for_same_seed_and_target():
    """Same seed + same target => byte-identical entity IDs (seed=42 default)."""
    a = generate_scale_topology(target_assets=1000)
    b = generate_scale_topology(target_assets=1000)
    assert a["stats"] == b["stats"]
    assert [d["mac"] for d in a["device_stats"]] == [d["mac"] for d in b["device_stats"]]
    assert [s["id"] for s in a["sites"]] == [s["id"] for s in b["sites"]]


def test_scale_org_is_isolated_from_campus():
    """Benchmark org must be distinct so scale#... never collides with campus#..."""
    topo = generate_scale_topology(target_assets=500)
    org = topo["organizations"][0]
    assert org["name"] == "Acme Benchmark Lab"


def test_clients_carry_correlated_fields_at_scale():
    """The whole point of reuse: benchmark assets keep campus's correlation."""
    topo = generate_scale_topology(target_assets=1000)
    wireless = topo["wireless_clients"][0]
    # Location + new correlated fields introduced in the seed work.
    assert "num_locating_aps" in wireless
    assert "map_id" in wireless
    wired = topo["wired_clients"][0]
    assert wired["last_vlan_name"] != ""  # populated VLAN name, not the old empty default


def test_default_target_is_the_pr_knob():
    """generate_scale_topology() with no arg must use the TARGET_ASSETS constant."""
    sig = inspect.signature(generate_scale_topology)
    assert sig.parameters["target_assets"].default == TARGET_ASSETS


@pytest.mark.parametrize("bad", [MIN_TARGET_ASSETS - 1, MAX_TARGET_ASSETS + 1, 0])
def test_rejects_out_of_range_targets(bad):
    with pytest.raises(ValueError):
        generate_scale_topology(target_assets=bad)


def test_rejects_non_integer_target():
    with pytest.raises(TypeError):
        generate_scale_topology(target_assets="15000")
