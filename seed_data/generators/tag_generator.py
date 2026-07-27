"""
Tag generator for benchmark topology assets.

Every 1 000 assets share the same 100 tag key-value pairs.
Tag set index = global_asset_index // 1000, so:
  1 000 assets  → 1 set   → 100 unique tag values
  10 000 assets → 10 sets → 1 000 unique tag values
  150 000 assets → 150 sets → 15 000 unique tag values

Tag keys: 20 realistic enterprise labels + 80 generic Attr_XXX keys.
"""

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


def generate_tag_set(set_index: int) -> dict:
    """Return the 100-tag dict for assets belonging to the given set."""
    tags: dict = {}
    for key in TAG_KEYS:
        if key == "Environment":
            tags[key] = _ENVIRONMENTS[set_index % len(_ENVIRONMENTS)]
        elif key == "Region":
            tags[key] = _REGIONS[set_index % len(_REGIONS)]
        elif key == "Country":
            tags[key] = _COUNTRIES[set_index % len(_COUNTRIES)]
        else:
            tags[key] = f"{key}-{set_index:04d}"
    return tags
