"""
Tag generator for benchmark topology assets.

Only the first TAGGED_ASSET_LIMIT assets (by global generation order, across
devices + wireless_clients + wired_clients) carry a tags field at all. The
rest of the benchmark dataset is untagged.

Each tagged asset gets its own unique 100-tag key-value set, keyed by its
own global asset index — no two tagged assets share identical tag values.

Tag keys: 20 realistic enterprise labels + 80 generic Attr_XXX keys.
"""

TAGGED_ASSET_LIMIT = 1000

_ENVIRONMENTS = ["Prod", "Dev", "Staging", "QA", "UAT"]
_REGIONS = ["US-East", "US-West", "EU-West", "EU-Central", "AP-South", "AP-East", "LATAM", "ME-Africa"]
_COUNTRIES = ["US", "DE", "GB", "IN", "SG", "FR", "JP", "AU"]

TAG_KEYS: list[str] = [
    "Dept", "SubDept", "Team", "Owner", "CostCenter",
    "BudgetCode", "BusinessUnit", "Division", "Environment", "Role",
    "Region", "Country", "Site", "Building", "Floor",
    "Room", "Zone", "Rack", "Domain", "Network",
] + [f"Attr_{i:03d}" for i in range(21, 101)]

assert len(TAG_KEYS) == 100, "TAG_KEYS must contain exactly 100 keys"


def generate_tag_set(asset_index: int) -> dict:
    """Return a 100-tag dict unique to the given asset index."""
    tags: dict = {}
    for key in TAG_KEYS:
        if key == "Environment":
            tags[key] = _ENVIRONMENTS[asset_index % len(_ENVIRONMENTS)]
        elif key == "Region":
            tags[key] = _REGIONS[asset_index % len(_REGIONS)]
        elif key == "Country":
            tags[key] = _COUNTRIES[asset_index % len(_COUNTRIES)]
        else:
            tags[key] = f"{key}-{asset_index:04d}"
    return tags
