"""
Map data generator for Mock Mist API.

Generates site floor plan/map data matching Mist API format.
"""

import random
import uuid
from datetime import datetime
from typing import Optional


FLOOR_NAMES = [
    "Ground Floor", "1st Floor", "2nd Floor", "3rd Floor", "4th Floor",
    "Basement", "Mezzanine", "Lobby", "Server Room", "Warehouse",
]

MAP_TYPES = ["image", "google"]


class MapGenerator:
    """Generator for Mist site map data."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def generate_map(
        self,
        map_id: str,
        site_id: str,
        org_id: str,
        name: str,
        lat: float = 37.3382,
        lng: float = -121.8863,
    ) -> dict:
        """
        Generate a site map matching Mist API format.

        Key fields: id, site_id, org_id, name, type, url, thumbnail_url,
        width, height, width_m, height_m, ppm, origin_x, origin_y,
        orientation, latlng_br, latlng_tl, locked, flags,
        created_time, modified_time
        """
        now = int(datetime.utcnow().timestamp())
        created = now - random.randint(86400 * 30, 86400 * 365)

        width = random.randint(800, 3000)
        height = random.randint(600, 2000)
        width_m = random.uniform(20.0, 100.0)
        height_m = width_m * (height / width)
        ppm = float(width) / width_m  # pixels per meter

        # Calculate bounding box from center point
        lat_offset = random.uniform(0.001, 0.005)
        lng_offset = random.uniform(0.001, 0.005)

        # Generate wayfinding path nodes with proper connections
        num_nodes = random.randint(3, 8)
        wayfinding_nodes = []
        for j in range(num_nodes):
            node_name = f"N{j + 1}"
            node = {
                "name": node_name,
                "position": {
                    "x": round(random.uniform(50.0, float(width) - 50), 2),
                    "y": round(random.uniform(50.0, float(height) - 50), 2),
                },
                "edges": {},
            }
            # Connect to previous and next nodes
            if j > 0:
                node["edges"][f"N{j}"] = "1"
            if j < num_nodes - 1:
                node["edges"][f"N{j + 2}"] = "1"
            wayfinding_nodes.append(node)

        return {
            "id": map_id,
            "site_id": site_id,
            "org_id": org_id,
            "name": name,
            "type": "image",
            "url": f"https://mock-mist-api.s3.amazonaws.com/maps/{map_id}.png",
            "thumbnail_url": f"https://mock-mist-api.s3.amazonaws.com/maps/{map_id}_thumb.png",
            "width": width,
            "height": height,
            "width_m": round(width_m, 2),
            "height_m": round(height_m, 2),
            "ppm": round(ppm, 6),
            "origin_x": round(random.uniform(10.0, 100.0), 2),
            "origin_y": round(random.uniform(100.0, 600.0), 2),
            "orientation": random.choice([0, 5, 90, 180, 270]),
            "latlng_br": {
                "lat": lat - lat_offset,
                "lng": lng + lng_offset,
            },
            "latlng_tl": {
                "lat": lat + lat_offset,
                "lng": lng - lng_offset,
            },
            "locked": False,
            "flags": {},
            "wayfinding": {
                "snap_to_path": True,
            },
            "wayfinding_path": {
                "coordinate": "actual",
                "nodes": wayfinding_nodes,
                "name": "Office",
            },
            "occupancy_limit": random.choice([0, 50, 100, 150, 200]),
            "use_auto_orientation": random.choice([True, False]),
            "use_auto_placement": random.choice([True, False]),
            "intended_coverage_areas": [],
            "group_name": name,
            "group_idx": 0,
            "sitesurvey_path": [],
            "wall_path": {
                "coordinate": "actual",
                "nodes": [],
                "name": "",
            },
            "created_time": created,
            "modified_time": now - random.randint(0, 86400 * 7),
        }

    def generate_maps_for_site(
        self,
        site_id: str,
        org_id: str,
        count: int,
        lat: float = 37.3382,
        lng: float = -121.8863,
        seed: int = 42,
    ) -> list[dict]:
        """Generate multiple maps (floor plans) for a site."""
        maps = []
        for i in range(count):
            map_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{site_id}-map-{i}-{seed}"))
            name = FLOOR_NAMES[i] if i < len(FLOOR_NAMES) else f"Floor {i + 1}"
            m = self.generate_map(
                map_id=map_id,
                site_id=site_id,
                org_id=org_id,
                name=name,
                lat=lat,
                lng=lng,
            )
            maps.append(m)
        return maps
