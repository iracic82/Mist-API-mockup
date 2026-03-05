"""
Site data generator for Mock Mist API.

Generates realistic Mist site data with geographic coordinates.
"""

import random
import uuid
from datetime import datetime
from typing import Optional


# US office locations with realistic coordinates
US_LOCATIONS = [
    {"city": "San Jose", "state": "CA", "country": "US", "lat": 37.3382, "lng": -121.8863, "tz": "America/Los_Angeles"},
    {"city": "New York", "state": "NY", "country": "US", "lat": 40.7128, "lng": -74.0060, "tz": "America/New_York"},
    {"city": "Chicago", "state": "IL", "country": "US", "lat": 41.8781, "lng": -87.6298, "tz": "America/Chicago"},
    {"city": "Austin", "state": "TX", "country": "US", "lat": 30.2672, "lng": -97.7431, "tz": "America/Chicago"},
    {"city": "Seattle", "state": "WA", "country": "US", "lat": 47.6062, "lng": -122.3321, "tz": "America/Los_Angeles"},
    {"city": "Denver", "state": "CO", "country": "US", "lat": 39.7392, "lng": -104.9903, "tz": "America/Denver"},
    {"city": "Boston", "state": "MA", "country": "US", "lat": 42.3601, "lng": -71.0589, "tz": "America/New_York"},
    {"city": "Atlanta", "state": "GA", "country": "US", "lat": 33.7490, "lng": -84.3880, "tz": "America/New_York"},
    {"city": "Miami", "state": "FL", "country": "US", "lat": 25.7617, "lng": -80.1918, "tz": "America/New_York"},
    {"city": "Dallas", "state": "TX", "country": "US", "lat": 32.7767, "lng": -96.7970, "tz": "America/Chicago"},
    {"city": "Phoenix", "state": "AZ", "country": "US", "lat": 33.4484, "lng": -112.0740, "tz": "America/Phoenix"},
    {"city": "Portland", "state": "OR", "country": "US", "lat": 45.5152, "lng": -122.6784, "tz": "America/Los_Angeles"},
    {"city": "Minneapolis", "state": "MN", "country": "US", "lat": 44.9778, "lng": -93.2650, "tz": "America/Chicago"},
]

STREET_NAMES = [
    "Main Street", "Oak Avenue", "Park Boulevard", "Market Street", "Broadway",
    "First Avenue", "Technology Parkway", "Innovation Boulevard",
    "Corporate Drive", "Business Park Lane", "Enterprise Avenue",
]


class SiteGenerator:
    """Generator for realistic Mist site data."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def _deterministic_uuid(self, name: str, seed: int) -> str:
        """Generate a deterministic UUID from a name and seed."""
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{name}-{seed}"))

    def generate_site(
        self,
        site_id: str,
        org_id: str,
        name: str,
        location: dict,
        sitegroup_ids: list = None,
    ) -> dict:
        """
        Generate a site matching Mist API format.

        Key fields: id, org_id, name, address, country_code, timezone,
        latlng, created_time, modified_time, sitegroup_ids, rftemplate_id,
        networktemplate_id, gatewaytemplate_id
        """
        now = int(datetime.utcnow().timestamp())
        created = now - random.randint(86400 * 30, 86400 * 365)

        street_num = random.randint(100, 9999)
        street = random.choice(STREET_NAMES)
        address = f"{street_num} {street}, {location['city']}, {location['state']}"

        return {
            "id": site_id,
            "org_id": org_id,
            "name": name,
            "address": address,
            "country_code": location.get("country", "US"),
            "timezone": location["tz"],
            "latlng": {
                "lat": location["lat"] + random.uniform(-0.01, 0.01),
                "lng": location["lng"] + random.uniform(-0.01, 0.01),
            },
            "created_time": created,
            "modified_time": now - random.randint(0, 86400 * 7),
            "sitegroup_ids": sitegroup_ids or [],
            "rftemplate_id": None,
            "networktemplate_id": None,
            "gatewaytemplate_id": None,
        }
