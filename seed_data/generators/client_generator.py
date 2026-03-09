"""
Client data generator for Mock Mist API.

Generates wireless and wired client data matching Mist API response schemas.
Uses coherent device profiles so hostname, manufacturer, OUI, OS, and model
are always consistent (e.g. PRINTER always gets a printer OUI, not a laptop OUI).
"""

import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Optional


# Coherent client profiles: each profile bundles hostname, OUI, manufacturer,
# OS, family, and model together. Separate weights for wireless vs wired
# since device type distribution differs (phones are wireless, printers are wired).
#
# OUI prefixes are real IEEE assignments for the correct product lines:
# - Apple mobile (3ce072) vs Apple computer (a483e7) — different product divisions
# - HP Inc. PCs (10b676) vs HP Inc. printers (c8b5ad) — different OUI ranges
# - HPE switches/servers would use 3822d6 but those are infrastructure, not clients
CLIENT_PROFILES = [
    # ── Apple mobile ──
    {
        "hostname_prefix": "IPHONE",
        "manufacturer": "Apple", "oui": "3ce072",
        "os": ["iOS 17", "iOS 16"], "family": "Apple", "model": "iPhone",
        "dhcp_vendor_class": "Apple iPhone", "dhcp_request_params": "1 3 6 15 119 252",
        "wireless_weight": 12, "wired_weight": 0,
    },
    {
        "hostname_prefix": "IPAD",
        "manufacturer": "Apple", "oui": "3ce072",
        "os": ["iPadOS 17", "iPadOS 16"], "family": "Apple", "model": "iPad",
        "dhcp_vendor_class": "Apple iPad", "dhcp_request_params": "1 3 6 15 119 252",
        "wireless_weight": 5, "wired_weight": 0,
    },
    # ── Apple computer ──
    {
        "hostname_prefix": "MACBOOK",
        "manufacturer": "Apple", "oui": "a483e7",
        "os": ["macOS Sonoma", "macOS Ventura"], "family": "Apple", "model": "MacBook",
        "dhcp_vendor_class": "AAPLBSD", "dhcp_request_params": "1 3 6 15 119 252",
        "wireless_weight": 8, "wired_weight": 3,
    },
    # ── Samsung ──
    {
        "hostname_prefix": "GALAXY",
        "manufacturer": "Samsung", "oui": "8425db",
        "os": ["Android 14", "Android 13"], "family": "Android", "model": "Galaxy",
        "dhcp_vendor_class": "android-dhcp-14", "dhcp_request_params": "1 3 6 15 26 28 51 58 59 43",
        "wireless_weight": 12, "wired_weight": 0,
    },
    # ── Dell ──
    {
        "hostname_prefix": "LAPTOP",
        "manufacturer": "Dell", "oui": "f8b156",
        "os": ["Windows 11", "Windows 10"], "family": "Windows", "model": "Latitude",
        "dhcp_vendor_class": "MSFT 5.0", "dhcp_request_params": "1 3 6 15 31 33 43 44 46 47 119 121 249 252",
        "wireless_weight": 8, "wired_weight": 6,
    },
    {
        "hostname_prefix": "DESKTOP",
        "manufacturer": "Dell", "oui": "f8b156",
        "os": ["Windows 11", "Windows 10"], "family": "Windows", "model": "OptiPlex",
        "dhcp_vendor_class": "MSFT 5.0", "dhcp_request_params": "1 3 6 15 31 33 43 44 46 47 119 121 249 252",
        "wireless_weight": 0, "wired_weight": 10,
    },
    # ── HP — PCs use 10b676, printers use c8b5ad (different OUI ranges!) ──
    {
        "hostname_prefix": "LAPTOP",
        "manufacturer": "HP", "oui": "10b676",
        "os": ["Windows 11", "Windows 10"], "family": "Windows", "model": "EliteBook",
        "dhcp_vendor_class": "MSFT 5.0", "dhcp_request_params": "1 3 6 15 31 33 43 44 46 47 119 121 249 252",
        "wireless_weight": 7, "wired_weight": 5,
    },
    {
        "hostname_prefix": "PRINTER",
        "manufacturer": "HP", "oui": "c8b5ad",
        "os": ["Embedded"], "family": "HP", "model": "LaserJet",
        "dhcp_vendor_class": "Hewlett-Packard JetDirect", "dhcp_request_params": "1 3 6 23 44",
        "wireless_weight": 1, "wired_weight": 8,
    },
    # ── Lenovo ──
    {
        "hostname_prefix": "THINKPAD",
        "manufacturer": "Lenovo", "oui": "28d244",
        "os": ["Windows 11", "Windows 10"], "family": "Windows", "model": "ThinkPad",
        "dhcp_vendor_class": "MSFT 5.0", "dhcp_request_params": "1 3 6 15 31 33 43 44 46 47 119 121 249 252",
        "wireless_weight": 8, "wired_weight": 6,
    },
    # ── Microsoft ──
    {
        "hostname_prefix": "SURFACE",
        "manufacturer": "Microsoft", "oui": "281878",
        "os": ["Windows 11"], "family": "Windows", "model": "Surface",
        "dhcp_vendor_class": "MSFT 5.0", "dhcp_request_params": "1 3 6 15 31 33 43 44 46 47 119 121 249 252",
        "wireless_weight": 5, "wired_weight": 2,
    },
    # ── Google ──
    {
        "hostname_prefix": "PIXEL",
        "manufacturer": "Google", "oui": "f4f5d8",
        "os": ["Android 14"], "family": "Android", "model": "Pixel",
        "dhcp_vendor_class": "android-dhcp-14", "dhcp_request_params": "1 3 6 15 26 28 51 58 59 43",
        "wireless_weight": 4, "wired_weight": 0,
    },
    # ── Cisco VoIP ──
    {
        "hostname_prefix": "VOIP",
        "manufacturer": "Cisco", "oui": "001b0d",
        "os": ["Cisco IP Phone"], "family": "Cisco", "model": "IP Phone 8845",
        "dhcp_vendor_class": "Cisco Systems, Inc. IP Phone", "dhcp_request_params": "1 66 6 3 15 150 35",
        "wireless_weight": 1, "wired_weight": 8,
    },
    # ── Zebra scanners ──
    {
        "hostname_prefix": "SCANNER",
        "manufacturer": "Zebra", "oui": "00a0f8",
        "os": ["Android 11"], "family": "Android", "model": "TC52",
        "dhcp_vendor_class": "android-dhcp-11", "dhcp_request_params": "1 3 6 15 26 28 51 58 59 43",
        "wireless_weight": 3, "wired_weight": 2,
    },
]

SSIDS = ["Corporate", "Guest", "IoT"]
BANDS = ["24", "5", "6"]
CHANNELS_24 = [1, 6, 11]
CHANNELS_5 = [36, 40, 44, 48, 149, 153, 157, 161]
CHANNELS_6 = [1, 5, 9, 13, 17, 21]

KEY_MGMTS = ["wpa2-psk", "wpa3-sae", "wpa2-eap", "open"]
PROTOS = ["a", "ac", "ax", "n"]


class ClientGenerator:
    """Generator for Mist wireless and wired client data."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        # Build weighted pools for wireless and wired separately
        self._wireless_profiles = []
        self._wired_profiles = []
        for p in CLIENT_PROFILES:
            self._wireless_profiles.extend([p] * p["wireless_weight"])
            self._wired_profiles.extend([p] * p["wired_weight"])

    def _generate_mac(self, oui: str = None) -> str:
        """Generate a Mist-style MAC (lowercase, no colons, 12 hex chars)."""
        if oui:
            suffix = ''.join(f'{random.randint(0, 255):02x}' for _ in range(3))
            return f"{oui}{suffix}"
        return ''.join(f'{random.randint(0, 255):02x}' for _ in range(6))

    def _generate_hostname(self, prefix: str) -> str:
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"{prefix}-{suffix}"

    def generate_wireless_client(
        self,
        site_id: str,
        ap_mac: str = None,
        ap_id: str = None,
        vlan_id: int = 10,
        client_index: int = 0,
        site_index: int = 0,
    ) -> dict:
        """
        Generate a wireless client matching Mist /stats/clients response.

        All fields (hostname, manufacturer, OUI, OS, family, model) are
        drawn from a single coherent profile so they always match.
        """
        profile = random.choice(self._wireless_profiles)
        mac = self._generate_mac(profile["oui"])
        band = random.choice(BANDS)
        if band == "24":
            channel = random.choice(CHANNELS_24)
        elif band == "5":
            channel = random.choice(CHANNELS_5)
        else:
            channel = random.choice(CHANNELS_6)

        ssid = random.choice(SSIDS)
        now = int(datetime.utcnow().timestamp())

        ap_id_val = ap_id or str(uuid.uuid4())
        wlan_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"wlan-{ssid}"))

        return {
            "mac": mac,
            "hostname": self._generate_hostname(profile["hostname_prefix"]),
            "ip": f"10.{vlan_id}.{site_index}.{(client_index % 254) + 2}",
            "site_id": site_id,
            "ssid": ssid,
            "wlan_id": wlan_id,
            "band": band,
            "channel": channel,
            "vlan_id": str(vlan_id),
            "ap_mac": ap_mac or self._generate_mac(),
            "ap_id": ap_id_val,
            "rssi": float(random.randint(-80, -30)),
            "snr": float(random.randint(10, 50)),
            "rx_bps": random.randint(1000, 500000),
            "tx_bps": random.randint(1000, 500000),
            "rx_bytes": random.randint(1000000, 10000000000),
            "tx_bytes": random.randint(1000000, 5000000000),
            "rx_rate": round(random.uniform(6.0, 1200.0), 1),
            "tx_rate": round(random.uniform(6.0, 1200.0), 1),
            "rx_retries": random.randint(0, 500),
            "tx_retries": random.randint(0, 500),
            "rx_pkts": random.randint(1000, 10000000),
            "tx_pkts": random.randint(1000, 10000000),
            "proto": random.choice(PROTOS),
            "key_mgmt": random.choice(KEY_MGMTS),
            "manufacture": profile["manufacturer"],
            "os": random.choice(profile["os"]),
            "family": profile["family"],
            "model": profile["model"],
            "dual_band": random.random() < 0.7,
            "is_guest": ssid == "Guest",
            "last_seen": float(now - random.randint(0, 300)),
            "idle_time": float(random.randint(0, 600)),
            "uptime": float(random.randint(60, 86400 * 7)),
            "assoc_time": now - random.randint(60, 86400),
            "username": "",
        }

    def generate_wired_client(
        self,
        site_id: str,
        org_id: str,
        device_mac: str = None,
        port_id: str = None,
        vlan_id: int = 10,
        client_index: int = 0,
        site_index: int = 0,
    ) -> dict:
        """
        Generate a wired client matching Mist wired_clients/search response.

        All fields drawn from a single coherent profile (more desktops,
        printers, VoIP phones — things that are typically wired).
        """
        profile = random.choice(self._wired_profiles)
        mac = self._generate_mac(profile["oui"])
        ip = f"10.{vlan_id}.{site_index}.{(client_index % 254) + 2}"
        dev_mac = device_mac or self._generate_mac()
        p_id = port_id or f"ge-0/0/{random.randint(1, 48)}"
        now = int(datetime.utcnow().timestamp())

        hostname = self._generate_hostname(profile["hostname_prefix"])

        return {
            "mac": mac,
            "ip": [ip],
            "device_mac": [dev_mac],
            "device_mac_port": [
                {
                    "device_mac": dev_mac,
                    "port_id": p_id,
                    "vlan": vlan_id,
                    "ip": ip,
                }
            ],
            "port_id": [p_id],
            "vlan": [vlan_id],
            "org_id": org_id,
            "site_id": site_id,
            "timestamp": float(now - random.randint(0, 3600)),
            "hostname": [hostname],
            "manufacture": profile["manufacturer"],
            "random_mac": False,
            "last_hostname": hostname,
            "last_port_id": p_id,
            "last_vlan": vlan_id,
            "last_vlan_name": "",
            "last_device_mac": dev_mac,
            "dhcp_hostname": hostname.lower(),
            "dhcp_fqdn": f"{hostname.lower()}.local",
            "dhcp_client_identifier": mac,
            "dhcp_client_options": [],
            "dhcp_vendor_class_identifier": profile["dhcp_vendor_class"],
            "dhcp_request_params": profile["dhcp_request_params"],
            "auth_state": "authenticated",
            "auth_method": random.choice(["mac_auth", "dot1x", "mab"]),
        }

    def generate_wireless_clients_for_site(
        self, site_id: str, devices: list[dict], count: int, site_index: int = 0
    ) -> list[dict]:
        """Generate wireless clients distributed across APs."""
        aps = [d for d in devices if d.get("type") == "ap"]
        clients = []
        for i in range(count):
            ap = random.choice(aps) if aps else None
            client = self.generate_wireless_client(
                site_id=site_id,
                ap_mac=ap.get("mac") if ap else None,
                ap_id=ap.get("id") if ap else None,
                vlan_id=random.choice([10, 20, 30]),
                client_index=i,
                site_index=site_index,
            )
            # Internal field for seeding - tracks parent site
            client["_site_id"] = site_id
            clients.append(client)
        return clients

    def generate_wired_clients_for_site(
        self, site_id: str, org_id: str, devices: list[dict], count: int, site_index: int = 0
    ) -> list[dict]:
        """Generate wired clients distributed across switches."""
        switches = [d for d in devices if d.get("type") == "switch"]
        clients = []
        for i in range(count):
            sw = random.choice(switches) if switches else None
            client = self.generate_wired_client(
                site_id=site_id,
                org_id=org_id,
                device_mac=sw.get("mac") if sw else None,
                port_id=f"ge-0/0/{random.randint(1, 48)}",
                vlan_id=random.choice([10, 20, 40, 50]),
                client_index=i,
                site_index=site_index,
            )
            clients.append(client)
        return clients
