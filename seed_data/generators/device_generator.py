"""
Device stats data generator for Mock Mist API.

Generates realistic Mist device stats including APs, switches, and gateways.
Uses Juniper/Mist-specific models and firmware versions.
"""

import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Optional

# Mist device models by type
MIST_DEVICE_MODELS = {
    "ap": [
        {"model": "AP45", "firmware": "0.14.29505", "band": "Wi-Fi 6E"},
        {"model": "AP43", "firmware": "0.14.29505", "band": "Wi-Fi 6"},
        {"model": "AP41", "firmware": "0.14.29505", "band": "Wi-Fi 6"},
        {"model": "AP33", "firmware": "0.14.29505", "band": "Wi-Fi 6"},
        {"model": "AP32", "firmware": "0.14.29505", "band": "Wi-Fi 6"},
        {"model": "AP34", "firmware": "0.14.29505", "band": "Wi-Fi 6E"},
        {"model": "AP63", "firmware": "0.14.29505", "band": "Wi-Fi 6E"},
        {"model": "AP61", "firmware": "0.14.29505", "band": "Wi-Fi 6"},
        {"model": "AP24", "firmware": "0.14.29505", "band": "Wi-Fi 6"},
        {"model": "AP12", "firmware": "0.12.27805", "band": "Wi-Fi 5"},
    ],
    "switch": [
        {"model": "EX4300-48T", "firmware": "22.4R3-S3"},
        {"model": "EX4300-24T", "firmware": "22.4R3-S3"},
        {"model": "EX4400-48T", "firmware": "22.4R3-S3"},
        {"model": "EX4400-24T", "firmware": "22.4R3-S3"},
        {"model": "EX4650-48Y", "firmware": "22.4R3-S3"},
        {"model": "EX2300-24T", "firmware": "22.4R3-S3"},
        {"model": "EX2300-48T", "firmware": "22.4R3-S3"},
        {"model": "EX4100-48T", "firmware": "23.2R1-S2"},
    ],
    "gateway": [
        {"model": "SRX345", "firmware": "22.4R3-S3"},
        {"model": "SRX320", "firmware": "22.4R3-S3"},
        {"model": "SRX380", "firmware": "22.4R3-S3"},
        {"model": "SRX1500", "firmware": "22.4R3-S3"},
        {"model": "SSR120", "firmware": "6.2.5-R2"},
        {"model": "SSR130", "firmware": "6.2.5-R2"},
    ],
}


class DeviceGenerator:
    """Generator for realistic Mist device stats data."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        self._mac_counter = 0

    def _generate_mac(self) -> str:
        """Generate a Mist-style MAC address (lowercase, no colons)."""
        self._mac_counter += 1
        return ''.join(f'{random.randint(0, 255):02x}' for _ in range(6))

    def _generate_serial(self, device_type: str) -> str:
        """Generate a Juniper-style serial number."""
        if device_type == "ap":
            # Mist AP serials: alphanumeric
            return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        elif device_type == "switch":
            # Juniper EX serials: XX1234567890
            prefix = random.choice(["PE", "HW", "JN", "CW"])
            return f"{prefix}{''.join(random.choices(string.digits, k=10))}"
        else:
            # SRX/SSR serials
            prefix = random.choice(["CJ", "JN", "AD"])
            return f"{prefix}{''.join(random.choices(string.digits, k=10))}"

    def _generate_ip(self, network_octet: int, device_index: int, site_index: int = 0) -> str:
        """Generate a management IP. site_index separates sites into /24 blocks."""
        fourth = (device_index % 254) + 1
        return f"10.{network_octet}.{site_index}.{fourth}"

    def _get_model_info(self, device_type: str, model: str) -> dict:
        """Get model info from the models list."""
        for m in MIST_DEVICE_MODELS.get(device_type, []):
            if m["model"] == model:
                return m
        return MIST_DEVICE_MODELS.get(device_type, [{}])[0]

    def generate_device_stats(
        self,
        device_id: str,
        site_id: str,
        org_id: str,
        device_type: str,
        model: str,
        name: str,
        network_octet: int = 99,
        device_index: int = 0,
        map_id: str = None,
        map_data: dict = None,
        site_index: int = 0,
    ) -> dict:
        """
        Generate device stats matching Mist API format.

        Common fields: id, site_id, org_id, name, mac, model, type, serial,
        ip, status, uptime, last_seen, version, created_time, modified_time
        """
        model_info = self._get_model_info(device_type, model)
        mac = self._generate_mac()
        serial = self._generate_serial(device_type)
        ip = self._generate_ip(network_octet, device_index, site_index)
        now = int(datetime.utcnow().timestamp())

        # 95% of devices are connected
        status = "connected" if random.random() < 0.95 else "disconnected"
        uptime = float(random.randint(3600, 86400 * 90)) if status == "connected" else 0.0
        last_seen = float(now - (random.randint(0, 300) if status == "connected" else random.randint(3600, 86400 * 3)))

        # Generate x/y in pixel coordinates bounded by the actual map dimensions,
        # and x_m/y_m in meters using the map's ppm (pixels per meter) ratio.
        # Keeps a 5% margin from edges so devices aren't placed on walls.
        if map_id and map_data:
            map_w = map_data.get("width", 1000)
            map_h = map_data.get("height", 800)
            map_w_m = map_data.get("width_m", 60.0)
            map_h_m = map_data.get("height_m", 45.0)
            margin_x = map_w * 0.05
            margin_y = map_h * 0.05
            x = round(random.uniform(margin_x, map_w - margin_x), 2)
            y = round(random.uniform(margin_y, map_h - margin_y), 2)
            # Convert pixel position to meters using the map's scale
            x_m = round((x / map_w) * map_w_m, 2)
            y_m = round((y / map_h) * map_h_m, 2)
        elif map_id:
            # Fallback if map_data not provided
            x = round(random.uniform(50.0, 1280.0), 2)
            y = round(random.uniform(50.0, 1300.0), 2)
            x_m = round(random.uniform(3.0, 75.0), 2)
            y_m = round(random.uniform(3.0, 75.0), 2)
        else:
            x = None
            y = None
            x_m = None
            y_m = None

        device = {
            "id": device_id,
            "site_id": site_id,
            "org_id": org_id,
            "name": name,
            "mac": mac,
            "model": model,
            "type": device_type,
            "serial": serial,
            "ip": ip,
            "status": status,
            "uptime": uptime,
            "last_seen": last_seen,
            "version": model_info.get("firmware", "0.14.29505"),
            "created_time": float(now - random.randint(86400 * 30, 86400 * 365)),
            "modified_time": float(now - random.randint(0, 86400 * 7)),
            "map_id": map_id,
            "x": x,
            "y": y,
            "x_m": x_m,
            "y_m": y_m,
            "height": 0.0,
            "orientation": random.choice([0, 90, 180, 270]) if map_id else None,
            "locating": False,
            "notes": "",
            "ext_ip": f"198.51.100.{random.randint(1, 254)}",
            "ip_stat": {
                "ip": ip,
                "netmask": "255.255.255.0",
                "gateway": f"10.{network_octet}.{site_index}.1",
                "dns": ["8.8.8.8", "8.8.4.4"],
                "dns_suffix": [],
                "ips": {
                    "vlan99": ip,
                },
            },
            "fwupdate": {
                "status": "idle",
                "status_id": 1,
                "timestamp": now - random.randint(86400, 86400 * 30),
            },
            "cert_expiry": float(now + random.randint(86400 * 30, 86400 * 365)),
            "deviceprofile_id": None,
            "evpntopo_id": None,
            "hw_rev": "A1",
        }

        # Type-specific fields
        if device_type == "ap":
            device.update(self._generate_ap_extras(mac, status))
        elif device_type == "switch":
            device.update(self._generate_switch_extras(name, status))
        elif device_type == "gateway":
            device.update(self._generate_gateway_extras(name, status))

        return device

    def _generate_ap_extras(self, mac: str, status: str) -> dict:
        """Generate AP-specific stats fields."""
        num_clients = random.randint(0, 30) if status == "connected" else 0
        return {
            "num_clients": num_clients,
            "radio_stat": {
                "band_24": {
                    "channel": random.choice([1, 6, 11]),
                    "bandwidth": 20,
                    "power": random.randint(8, 17),
                    "num_clients": num_clients // 3,
                },
                "band_5": {
                    "channel": random.choice([36, 40, 44, 48, 149, 153, 157, 161]),
                    "bandwidth": 80,
                    "power": random.randint(12, 20),
                    "num_clients": num_clients - (num_clients // 3),
                },
            },
            "ble_stat": {
                "beacon_enabled": True,
                "beacon_rate": 3,
                "ibeacon_enabled": False,
            },
            "env_stat": {
                "cpu_temp": random.randint(40, 65),
                "ambient_temp": random.randint(20, 30),
            },
            "lldp_stat": {
                "system_name": f"Switch-{random.randint(1, 10):02d}",
                "port_id": f"ge-0/0/{random.randint(1, 48)}",
                "mgmt_addr": f"10.{random.randint(1, 254)}.0.1",
            },
            "auto_placement": {
                "info": {
                    "status": "placed",
                },
            },
            "led": {"enabled": True},
            "power_budget": random.choice([15400, 25500, 30000]),
            "power_src": "DC",
            "num_wlans": random.randint(1, 4),
            "rx_bps": random.randint(1000, 500000),
            "tx_bps": random.randint(1000, 500000),
            "rx_bytes": random.randint(1000000, 10000000000),
            "tx_bytes": random.randint(1000000, 5000000000),
        }

    def _generate_switch_extras(self, name: str, status: str) -> dict:
        """Generate switch-specific stats fields."""
        num_clients = random.randint(5, 48) if status == "connected" else 0
        return {
            "if_stat": {
                f"ge-0/0/{i}": {
                    "port_id": f"ge-0/0/{i}",
                    "up": random.random() < 0.7,
                    "speed": random.choice([100, 1000, 10000]),
                    "duplex": "full",
                    "rx_bytes": random.randint(1000000, 10000000000),
                    "tx_bytes": random.randint(1000000, 10000000000),
                }
                for i in range(0, min(4, 48))  # Sample ports
            },
            "clients": [
                {
                    "mac": self._generate_mac(),
                    "port_id": f"ge-0/0/{random.randint(1, 48)}",
                }
                for _ in range(min(num_clients, 5))
            ],
            "module_stat": [],
            "mac_table_stats": {
                "mac_table_count": random.randint(10, 500),
                "max_mac_table_count": 16384,
            },
            "clients_stats": {
                "total": num_clients,
            },
            "cpu_stat": {
                "idle": random.randint(60, 95),
                "system": random.randint(2, 20),
                "user": random.randint(2, 15),
                "interrupt": random.randint(0, 5),
            },
            "memory_stat": {
                "usage": random.randint(30, 70),
            },
            "hostname": name.lower().replace(" ", "-"),
            "config_status": "synced" if status == "connected" else "out_of_sync",
        }

    def _generate_gateway_extras(self, name: str, status: str) -> dict:
        """Generate gateway-specific stats fields."""
        return {
            "if_stat": {
                "ge-0/0/0": {
                    "port_id": "ge-0/0/0",
                    "up": status == "connected",
                    "speed": 1000,
                    "duplex": "full",
                    "rx_bytes": random.randint(1000000000, 100000000000),
                    "tx_bytes": random.randint(1000000000, 100000000000),
                },
            },
            "cpu_stat": {
                "idle": random.randint(60, 95),
                "system": random.randint(2, 20),
                "user": random.randint(2, 15),
                "interrupt": random.randint(0, 5),
            },
            "memory_stat": {
                "usage": random.randint(30, 70),
            },
            "service_stat": {},
            "bgp_peers": [],
            "cluster_stat": None,
            "hostname": name.lower().replace(" ", "-"),
            "is_ha": False,
            "route_summary_stats": {
                "fib_routes": random.randint(10, 500),
                "max_unicast_routes_count": 1048576,
            },
            "mac_table_stats": {
                "mac_table_count": random.randint(10, 200),
                "max_mac_table_count": 65536,
            },
        }

    def generate_devices_for_site(
        self,
        site_id: str,
        org_id: str,
        config: dict,
        network_octet: int = 99,
        map_ids: list = None,
        site_maps: list = None,
        seed: int = 42,
        site_index: int = 0,
    ) -> list[dict]:
        """
        Generate all devices for a site based on configuration.

        Args:
            site_maps: List of map dicts (with width, height, width_m, height_m)
                       so device coordinates are bounded to actual map dimensions.

        Config format:
            {
                "gateways": [{"model": "SRX345", "name": "HQ-GW-01"}],
                "switches": [{"model": "EX4400-48T", "count": 2, "name_prefix": "HQ-SW"}],
                "aps": [{"model": "AP45", "count": 15, "name_prefix": "HQ-AP"}],
            }
        """
        devices = []
        device_index = 0

        # Build map_id → map_data lookup for coordinate correlation
        maps_by_id = {}
        if site_maps:
            for m in site_maps:
                maps_by_id[m["id"]] = m

        # Gateways go on the first map (server/network room)
        for gw_config in config.get("gateways", []):
            device_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{site_id}-gw-{device_index}-{seed}"))
            gw_map_id = map_ids[0] if map_ids else None
            device = self.generate_device_stats(
                device_id=device_id,
                site_id=site_id,
                org_id=org_id,
                device_type="gateway",
                model=gw_config["model"],
                name=gw_config["name"],
                network_octet=network_octet,
                device_index=device_index,
                map_id=gw_map_id,
                map_data=maps_by_id.get(gw_map_id),
                site_index=site_index,
            )
            devices.append(device)
            device_index += 1

        # Switches go on the first map (server/network room)
        for sw_config in config.get("switches", []):
            count = sw_config.get("count", 1)
            name_prefix = sw_config.get("name_prefix", "SW")
            for i in range(count):
                device_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{site_id}-sw-{device_index}-{seed}"))
                sw_map_id = map_ids[0] if map_ids else None
                device = self.generate_device_stats(
                    device_id=device_id,
                    site_id=site_id,
                    org_id=org_id,
                    device_type="switch",
                    model=sw_config["model"],
                    name=f"{name_prefix}-{i + 1:02d}",
                    network_octet=network_octet,
                    device_index=device_index,
                    map_id=sw_map_id,
                    map_data=maps_by_id.get(sw_map_id),
                    site_index=site_index,
                )
                devices.append(device)
                device_index += 1

        for ap_config in config.get("aps", []):
            count = ap_config.get("count", 1)
            name_prefix = ap_config.get("name_prefix", "AP")
            for i in range(count):
                device_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{site_id}-ap-{device_index}-{seed}"))
                ap_map_id = None
                if map_ids:
                    ap_map_id = map_ids[i % len(map_ids)]
                device = self.generate_device_stats(
                    device_id=device_id,
                    site_id=site_id,
                    org_id=org_id,
                    device_type="ap",
                    model=ap_config["model"],
                    name=f"{name_prefix}-{i + 1:02d}",
                    network_octet=network_octet,
                    device_index=device_index,
                    map_id=ap_map_id,
                    map_data=maps_by_id.get(ap_map_id),
                    site_index=site_index,
                )
                devices.append(device)
                device_index += 1

        return devices
