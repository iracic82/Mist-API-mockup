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

from seed_data.generators.network_generator import ORG_NETWORK_TEMPLATES

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
        {"model": "EX4300-48T", "firmware": "22.4R3-S3", "port_count": 48, "port_prefix": "ge"},
        {"model": "EX4300-24T", "firmware": "22.4R3-S3", "port_count": 24, "port_prefix": "ge"},
        {"model": "EX4400-48T", "firmware": "22.4R3-S3", "port_count": 48, "port_prefix": "mge"},
        {"model": "EX4400-24T", "firmware": "22.4R3-S3", "port_count": 24, "port_prefix": "mge"},
        {"model": "EX4650-48Y", "firmware": "22.4R3-S3", "port_count": 48, "port_prefix": "et"},
        {"model": "EX2300-24T", "firmware": "22.4R3-S3", "port_count": 24, "port_prefix": "ge"},
        {"model": "EX2300-48T", "firmware": "22.4R3-S3", "port_count": 48, "port_prefix": "ge"},
        {"model": "EX4100-48T", "firmware": "23.2R1-S2", "port_count": 48, "port_prefix": "mge"},
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

# WAN link definitions for gateway interfaces — each site gateway gets these
# WAN interfaces on ge-0/0/0 through ge-0/0/2, LAN trunk on ge-0/0/3
WAN_LINKS = [
    {"port": 0, "wan_name": "ISP-Primary", "address_mode": "Dynamic"},
    {"port": 1, "wan_name": "ISP-Secondary", "address_mode": "Dynamic"},
]


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
            "tag_uuid": org_id,
            "tag_id": random.randint(1000000, 9999999),
            "config_version": now - random.randint(0, 86400),
            "config_timestamp": now - random.randint(0, 86400),
            "chassis_serial": serial,
            "chassis_model": model if device_type == "switch" else "",
            "chassis_mac": mac if device_type == "switch" else "",
            "part_number": "",
            "fw_versions_outofsync": False,
            "fw_restore_available": True if status == "connected" else False,
            "last_trouble": {"code": "", "timestamp": 0},
        }

        # Type-specific fields (may override ip_stat, if_stat, etc.)
        extras_kwargs = {
            "mac": mac,
            "serial": serial,
            "model": model,
            "model_info": model_info,
            "status": status,
            "uptime": uptime,
            "now": now,
        }
        if device_type == "ap":
            device.update(self._generate_ap_extras(**extras_kwargs))
        elif device_type == "switch":
            device.update(self._generate_switch_extras(
                name=name, ip=ip, site_index=site_index, **extras_kwargs,
            ))
        elif device_type == "gateway":
            device.update(self._generate_gateway_extras(
                name=name, ip=ip, site_index=site_index, **extras_kwargs,
            ))

        return device

    def _generate_ap_extras(self, mac: str, status: str, now: int, serial: str,
                            model: str, model_info: dict, uptime: float) -> dict:
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
            "auto_upgrade_stat": {
                "lastcheck": now - random.randint(0, 86400),
                "scheduled": False,
            },
            "radio_config": {"band_5": {}},
            "ip_config": {"type": "dhcp", "network": "default"},
            "config_reverted": False,
            "port_stat": {
                "eth0": {
                    "up": True,
                    "speed": 1000,
                    "full_duplex": True,
                    "rx_bytes": random.randint(1000000, 10000000000),
                    "tx_bytes": random.randint(1000000, 5000000000),
                    "rx_pkts": random.randint(10000, 100000000),
                    "tx_pkts": random.randint(10000, 100000000),
                },
            },
            "mount": random.choice(["facedown", "ceiling", "wall"]),
            "mesh": {"enabled": False, "role": "base", "group": None},
            "switch_redundancy": {"num_redundant_aps": 0},
            "cpu_util": random.randint(5, 40),
            "mem_used_kb": random.randint(100000, 500000),
            "mem_total_kb": random.randint(500000, 1000000),
        }

    def _generate_switch_if_stat(self, model_info: dict, ip: str, site_index: int) -> dict:
        """
        Generate switch if_stat matching real Mist API format.

        Includes physical ports (ge-/mge-/et-), IRB management interface with
        management VLAN IP, VME interface, loopback, and management ethernet.
        IPs on irb.0 and vme.0 are correlated with the site's Management VLAN (99)
        subnet: 10.99.{site_index}.0/24.
        """
        port_prefix = model_info.get("port_prefix", "ge")
        port_count = model_info.get("port_count", 48)
        mgmt_ip = ip  # 10.99.{site_index}.{device}

        if_stat = {}

        # Physical ports — key format: "{prefix}-0/0/{i}.0"
        for i in range(port_count):
            port_up = random.random() < 0.3  # ~30% of ports active
            key = f"{port_prefix}-0/0/{i}.0"
            entry = {
                "port_id": f"{port_prefix}-0/0/{i}",
                "up": port_up,
                "tx_pkts": random.randint(10000, 1000000) if port_up else 0,
                "rx_pkts": random.randint(10000, 5000000) if port_up else 0,
                "tx_bytes": random.randint(1000000, 10000000000) if port_up else 0,
                "rx_bytes": random.randint(1000000, 10000000000) if port_up else 0,
            }
            if_stat[key] = entry

        # IRB.0 — Integrated Routing and Bridging for management VLAN (99)
        # Carries the switch's management IP on the management subnet
        if_stat["irb.0"] = {
            "port_id": "irb",
            "up": True,
            "vlan": 99,
            "ips": [f"{mgmt_ip}/24"],
            "servp_info": {},
            "tx_pkts": random.randint(1000, 10000000),
            "rx_pkts": random.randint(1000, 50000000),
            "tx_bytes": random.randint(100000, 1000000000),
            "rx_bytes": random.randint(100000, 5000000000),
        }

        # VME.0 — Virtual Management Ethernet (Junos management plane)
        # Also on the management subnet, same IP as the device management address
        if_stat["vme.0"] = {
            "port_id": "vme",
            "up": True,
            "ips": [f"{mgmt_ip}/24"],
            "servp_info": {},
            "tx_pkts": random.randint(1000000, 100000000),
            "rx_pkts": random.randint(1000000, 500000000),
            "tx_bytes": random.randint(1000000000, 80000000000),
            "rx_bytes": random.randint(1000000000, 40000000000),
        }

        # ME0.0 — Management Ethernet (out-of-band)
        if_stat["me0.0"] = {
            "port_id": "me0",
            "up": True,
            "tx_pkts": random.randint(1000000, 100000000),
            "rx_pkts": random.randint(1000000, 500000000),
            "tx_bytes": random.randint(1000000000, 80000000000),
            "rx_bytes": random.randint(1000000000, 40000000000),
        }

        # lo0.16384 — Internal loopback (localhost)
        if_stat["lo0.16384"] = {
            "port_id": "lo0",
            "up": True,
            "ips": ["127.0.0.1/0"],
            "servp_info": {},
            "tx_pkts": 0,
            "rx_pkts": 0,
            "tx_bytes": 0,
            "rx_bytes": 0,
        }

        # lo0.16385 — System loopback (routing engine)
        if_stat["lo0.16385"] = {
            "port_id": "lo0",
            "up": True,
            "tx_pkts": random.randint(100000000, 2000000000),
            "rx_pkts": random.randint(100000000, 2000000000),
            "tx_bytes": random.randint(10000000000, 120000000000),
            "rx_bytes": random.randint(10000000000, 120000000000),
        }

        return if_stat

    def _generate_switch_extras(self, name: str, status: str, mac: str, serial: str,
                               model: str, model_info: dict, uptime: float, now: int,
                               ip: str, site_index: int) -> dict:
        """Generate switch-specific stats fields with correlated interface IPs."""
        num_clients = random.randint(5, 48) if status == "connected" else 0
        mgmt_ip = ip  # 10.99.{site_index}.{device}

        return {
            "if_stat": self._generate_switch_if_stat(model_info, ip, site_index),
            # Override ip_stat to match real Mist format for switches:
            # netmask 255.255.255.255, ips grouped by VLAN, no dns fields
            "ip_stat": {
                "ip": mgmt_ip,
                "netmask": "255.255.255.255",
                "gateway": f"10.99.{site_index}.1",
                "ips": {
                    "vlan99": f"{mgmt_ip},127.0.0.1,{mgmt_ip}",
                },
            },
            "clients": [
                {
                    "mac": self._generate_mac(),
                    "port_id": f"ge-0/0/{random.randint(1, 48)}",
                }
                for _ in range(min(num_clients, 5))
            ],
            "module_stat": [
                {
                    "locating": False,
                    "optics_cpld_version": "",
                    "power_cpld_version": "",
                    "cpld_version": "2.64",
                    "memory_stat": {"usage": random.randint(30, 70)},
                    "vc_state": "present",
                    "boot_partition": "junos",
                    "poe": {
                        "max_power": random.choice([180.0, 370.0, 740.0, 1480.0]),
                        "power_reserved": 0.0,
                        "power_draw": round(random.uniform(10.0, 200.0), 1),
                        "status": random.choice(["AT_MODE", "BT_MODE"]),
                    },
                    "backup_version": "22.4R2-S1.6",
                    "vc_mode": "HiGiG",
                    "type": "fpc",
                    "mac": mac,
                    "_idx": 0,
                    "temperatures": [
                        {"name": f"Thermal board Sensor {i+1}", "status": "ok", "celsius": float(random.randint(38, 55))}
                        for i in range(3)
                    ] + [{"name": "PFE Die Sensor", "status": "ok", "celsius": float(random.randint(45, 65))}],
                    "psus": [
                        {"name": "Power Supply 0", "status": "ok", "description": "PSU-200W-AC"},
                        {"name": "Power Supply 1", "status": random.choice(["ok", "absent"]), "description": random.choice(["PSU-200W-AC", ""])},
                    ],
                    "humidity": [],
                    "fans": [
                        {"name": f"Fan Tray {i} Fan 1", "status": "ok", "airflow": "out", "rpm": random.randint(2000, 5000)}
                        for i in range(2)
                    ],
                    "model": model,
                    "serial": serial,
                    "part_number": "",
                    "version": model_info.get("firmware", "22.4R3-S3"),
                    "fpc_idx": 0,
                    "vc_role": "master",
                    "uptime": int(uptime),
                },
            ],
            "mac_table_stats": {
                "mac_table_count": random.randint(10, 500),
                "max_mac_entries_supported": 16384,
            },
            "clients_stats": {
                "total": {
                    "num_wired_clients": num_clients,
                    "num_aps": [random.randint(0, 5)],
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
            "hostname": name.lower().replace(" ", "-"),
            "_id": mac,
            "config_status": "COMMITED" if status == "connected" else "out_of_sync",
            "auto_upgrade_stat": {"lastcheck": now, "scheduled": False},
            "arp_table_stats": {
                "arp_table_count": random.randint(10, 200),
                "max_entries_supported": 65536,
            },
            "route_summary_stats": {
                "fib_routes": random.randint(10, 500),
                "max_unicast_routes_supported": 1048576,
                "total_routes": random.randint(10, 500),
            },
            "vc_setup_info": {
                "err_vc_config_out_of_sync": False,
                "config_type": "nonprovisioned",
                "err_missing_dev_id_fpc": False,
            },
            "fw_restore_available": True if status == "connected" else False,
            "has_pcap": False,
            "dhcpd_stat": {},
            "service_stat": {},
            "expiring_certs": {},
            "ap_redundancy": {
                "num_aps": 0,
                "num_aps_with_switch_redundancy": 0,
            },
        }

    def _generate_gateway_if_stat(self, ip: str, site_index: int, status: str) -> dict:
        """
        Generate gateway if_stat matching real Mist API format.

        Includes WAN interfaces, LAN sub-interfaces per VLAN (with gateway IPs
        derived from ORG_NETWORK_TEMPLATES), management fxp0, and loopbacks.
        Each LAN sub-interface on ge-0/0/3.{vlan_id} carries the correct
        gateway IP for that VLAN's site-derived subnet.
        """
        is_up = status == "connected"
        if_stat = {}

        # WAN interfaces — ge-0/0/0 and ge-0/0/1
        for wan in WAN_LINKS:
            port_num = wan["port"]
            wan_ip = f"198.51.{100 + port_num}.{random.randint(2, 254)}"
            key = f"ge-0/0/{port_num}.0"
            if_stat[key] = {
                "port_id": f"ge-0/0/{port_num}",
                "up": is_up,
                "port_usage": "wan",
                "wan_name": wan["wan_name"],
                "network_name": "",
                "address_mode": wan["address_mode"],
                "vlan": 0,
                "ips": [f"{wan_ip}/24"] if is_up else [],
                "nat_addresses": ["0.0.0.0"],
                "servp_info": {},
                "tx_pkts": random.randint(100000000, 20000000000) if is_up else 0,
                "rx_pkts": random.randint(100000000, 20000000000) if is_up else 0,
                "tx_bytes": random.randint(1000000000000, 6000000000000) if is_up else 0,
                "rx_bytes": random.randint(1000000000000, 20000000000000) if is_up else 0,
            }

        # LAN sub-interfaces on ge-0/0/3 — one per VLAN from ORG_NETWORK_TEMPLATES
        # Each carries the gateway IP for that VLAN's site-derived /24 subnet
        for net in ORG_NETWORK_TEMPLATES:
            vlan_id = net["vlan_id"]
            # Derive site-specific gateway: 10.{second_octet}.{site_index}.1/24
            base_parts = net["subnet"].split("/")[0].split(".")
            gw_ip = f"{base_parts[0]}.{base_parts[1]}.{site_index}.1"
            subnet_cidr = f"{gw_ip}/24"

            # Management VLAN (99) is the native/untagged VLAN on sub-interface .0
            # Other VLANs use their VLAN ID as the sub-interface number
            if vlan_id == 99:
                sub_iface = "ge-0/0/3.0"
            else:
                sub_iface = f"ge-0/0/3.{vlan_id}"

            if_stat[sub_iface] = {
                "port_id": "ge-0/0/3",
                "up": is_up,
                "port_usage": "lan",
                "network_name": net["name"],
                "address_mode": "Static",
                "vlan": vlan_id,
                "ips": [subnet_cidr] if is_up else [],
                "nat_addresses": ["0.0.0.0"],
                "servp_info": {},
                "tx_pkts": random.randint(1000000, 20000000000) if is_up else 0,
                "rx_pkts": random.randint(1000000, 15000000000) if is_up else 0,
                "tx_bytes": random.randint(1000000000, 20000000000000) if is_up else 0,
                "rx_bytes": random.randint(1000000000, 5000000000000) if is_up else 0,
            }

        # fxp0.0 — Management interface (out-of-band)
        if_stat["fxp0.0"] = {
            "port_id": "fxp0",
            "up": is_up,
            "port_usage": "",
            "network_name": "",
            "address_mode": "Dynamic",
            "vlan": 0,
            "ips": [f"{ip}/24"] if is_up else [],
            "nat_addresses": ["0.0.0.0"],
            "servp_info": {},
            "tx_pkts": random.randint(1000000, 10000000) if is_up else 0,
            "rx_pkts": random.randint(100000000, 1000000000) if is_up else 0,
            "tx_bytes": random.randint(100000000, 1000000000) if is_up else 0,
            "rx_bytes": random.randint(10000000000, 100000000000) if is_up else 0,
        }

        # lo0.0 — Router loopback with overlay IP
        if_stat["lo0.0"] = {
            "port_id": "lo0",
            "up": True,
            "port_usage": "",
            "network_name": "",
            "address_mode": "Unknown",
            "vlan": 0,
            "ips": [f"100.100.0.{site_index}/128"],
            "nat_addresses": ["0.0.0.0"],
            "servp_info": {},
            "tx_pkts": random.randint(100000, 2000000),
            "rx_pkts": random.randint(100000, 2000000),
            "tx_bytes": random.randint(10000000, 200000000),
            "rx_bytes": random.randint(10000000, 200000000),
        }

        # lo0.16384 — Internal loopback (localhost)
        if_stat["lo0.16384"] = {
            "port_id": "lo0",
            "up": True,
            "port_usage": "",
            "network_name": "",
            "address_mode": "Unknown",
            "vlan": 0,
            "ips": ["127.0.0.1/128"],
            "nat_addresses": ["0.0.0.0"],
            "servp_info": {},
            "tx_pkts": random.randint(1000000, 10000000),
            "rx_pkts": random.randint(1000000, 10000000),
            "tx_bytes": random.randint(100000000, 2000000000),
            "rx_bytes": random.randint(100000000, 2000000000),
        }

        # lo0.16385 — System loopback (routing engine, tunnel endpoints)
        if_stat["lo0.16385"] = {
            "port_id": "lo0",
            "up": True,
            "port_usage": "",
            "network_name": "",
            "address_mode": "Unknown",
            "vlan": 0,
            "ips": [
                f"10.0.0.{site_index}/128",
                f"128.0.0.{site_index}/128",
            ],
            "nat_addresses": ["0.0.0.0"] * 5,
            "servp_info": {},
            "tx_pkts": random.randint(100000000, 1000000000),
            "rx_pkts": random.randint(100000000, 1000000000),
            "tx_bytes": random.randint(10000000000, 40000000000),
            "rx_bytes": random.randint(10000000000, 40000000000),
        }

        return if_stat

    def _generate_gateway_extras(self, name: str, status: str, mac: str, serial: str,
                                model: str, model_info: dict, uptime: float, now: int,
                                ip: str, site_index: int) -> dict:
        """Generate gateway-specific stats fields with correlated interface IPs."""
        mgmt_ip = ip  # 10.99.{site_index}.{device} (device_index 0 → .1 = gateway IP)

        # Build DHCP stats per LAN network
        dhcpd_stat = {}
        for net in ORG_NETWORK_TEMPLATES:
            num_ips = 245 if net["vlan_id"] != 99 else 200
            num_leased = random.randint(0, num_ips // 3) if status == "connected" else 0
            dhcpd_stat[net["name"]] = {
                "num_ips": num_ips,
                "num_leased": num_leased,
            }

        return {
            "if_stat": self._generate_gateway_if_stat(ip, site_index, status),
            # Override ip_stat to match real Mist format for gateways
            "ip_stat": {
                "ip": mgmt_ip,
                "netmask": "255.255.255.255",
                "gateway": f"10.99.{site_index}.1",
                "ips": {
                    "vlan99": mgmt_ip,
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
            "dhcpd_stat": dhcpd_stat,
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
            "auto_upgrade_stat": {},
            "module_stat": [{"mac": mac, "status": status, "serial": serial, "model": model}],
            "expiring_certs": {},
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
