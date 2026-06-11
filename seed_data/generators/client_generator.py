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
# Each profile defines: hostname, OUI, manufacturer, OS, family, model,
# allowed SSIDs (wireless) / VLANs (wired), and auth methods.
#
# SSID-to-VLAN mapping: Corporate→10, Guest→20, IoT→30
# Wired VLANs: Corporate→10, IoT→30, Voice→40, Server→50
SSID_VLAN_MAP = {"Corporate": 10, "Guest": 20, "IoT": 30}

CLIENT_PROFILES = [
    # ── Apple mobile ──
    {
        "hostname_prefix": "IPHONE",
        "manufacturer": "Apple", "oui": "3ce072",
        "os": ["iOS 17", "iOS 16"], "family": "Apple", "model": "iPhone",
        "dhcp_vendor_class": "Apple iPhone", "dhcp_request_params": "1 3 6 15 119 252",
        "wireless_weight": 12, "wired_weight": 0,
        "allowed_ssids": ["Corporate", "Guest"],
        "wired_vlan": None, "auth_method": None,
    },
    {
        "hostname_prefix": "IPAD",
        "manufacturer": "Apple", "oui": "3ce072",
        "os": ["iPadOS 17", "iPadOS 16"], "family": "Apple", "model": "iPad",
        "dhcp_vendor_class": "Apple iPad", "dhcp_request_params": "1 3 6 15 119 252",
        "wireless_weight": 5, "wired_weight": 0,
        "allowed_ssids": ["Corporate", "Guest"],
        "wired_vlan": None, "auth_method": None,
    },
    # ── Apple computer ──
    {
        "hostname_prefix": "MACBOOK",
        "manufacturer": "Apple", "oui": "a483e7",
        "os": ["macOS Sonoma", "macOS Ventura"], "family": "Apple", "model": "MacBook",
        "dhcp_vendor_class": "AAPLBSD", "dhcp_request_params": "1 3 6 15 119 252",
        "wireless_weight": 8, "wired_weight": 3,
        "allowed_ssids": ["Corporate"],
        "wired_vlan": 10, "auth_method": "dot1x",
    },
    # ── Samsung ──
    {
        "hostname_prefix": "GALAXY",
        "manufacturer": "Samsung", "oui": "8425db",
        "os": ["Android 14", "Android 13"], "family": "Android", "model": "Galaxy",
        "dhcp_vendor_class": "android-dhcp-14", "dhcp_request_params": "1 3 6 15 26 28 51 58 59 43",
        "wireless_weight": 12, "wired_weight": 0,
        "allowed_ssids": ["Corporate", "Guest"],
        "wired_vlan": None, "auth_method": None,
    },
    # ── Dell ──
    {
        "hostname_prefix": "LAPTOP",
        "manufacturer": "Dell", "oui": "f8b156",
        "os": ["Windows 11", "Windows 10"], "family": "Windows", "model": "Latitude",
        "dhcp_vendor_class": "MSFT 5.0", "dhcp_request_params": "1 3 6 15 31 33 43 44 46 47 119 121 249 252",
        "wireless_weight": 8, "wired_weight": 6,
        "allowed_ssids": ["Corporate"],
        "wired_vlan": 10, "auth_method": "dot1x",
    },
    {
        "hostname_prefix": "DESKTOP",
        "manufacturer": "Dell", "oui": "f8b156",
        "os": ["Windows 11", "Windows 10"], "family": "Windows", "model": "OptiPlex",
        "dhcp_vendor_class": "MSFT 5.0", "dhcp_request_params": "1 3 6 15 31 33 43 44 46 47 119 121 249 252",
        "wireless_weight": 0, "wired_weight": 10,
        "allowed_ssids": [],
        "wired_vlan": 10, "auth_method": "dot1x",
    },
    # ── HP — PCs use 10b676, printers use c8b5ad (different OUI ranges!) ──
    {
        "hostname_prefix": "LAPTOP",
        "manufacturer": "HP", "oui": "10b676",
        "os": ["Windows 11", "Windows 10"], "family": "Windows", "model": "EliteBook",
        "dhcp_vendor_class": "MSFT 5.0", "dhcp_request_params": "1 3 6 15 31 33 43 44 46 47 119 121 249 252",
        "wireless_weight": 7, "wired_weight": 5,
        "allowed_ssids": ["Corporate"],
        "wired_vlan": 10, "auth_method": "dot1x",
    },
    {
        "hostname_prefix": "PRINTER",
        "manufacturer": "HP", "oui": "c8b5ad",
        "os": ["Embedded"], "family": "HP", "model": "LaserJet",
        "dhcp_vendor_class": "Hewlett-Packard JetDirect", "dhcp_request_params": "1 3 6 23 44",
        "wireless_weight": 1, "wired_weight": 8,
        "allowed_ssids": ["IoT"],
        "wired_vlan": 30, "auth_method": "mac_auth",
    },
    # ── Lenovo ──
    {
        "hostname_prefix": "THINKPAD",
        "manufacturer": "Lenovo", "oui": "28d244",
        "os": ["Windows 11", "Windows 10"], "family": "Windows", "model": "ThinkPad",
        "dhcp_vendor_class": "MSFT 5.0", "dhcp_request_params": "1 3 6 15 31 33 43 44 46 47 119 121 249 252",
        "wireless_weight": 8, "wired_weight": 6,
        "allowed_ssids": ["Corporate"],
        "wired_vlan": 10, "auth_method": "dot1x",
    },
    # ── Microsoft ──
    {
        "hostname_prefix": "SURFACE",
        "manufacturer": "Microsoft", "oui": "281878",
        "os": ["Windows 11"], "family": "Windows", "model": "Surface",
        "dhcp_vendor_class": "MSFT 5.0", "dhcp_request_params": "1 3 6 15 31 33 43 44 46 47 119 121 249 252",
        "wireless_weight": 5, "wired_weight": 2,
        "allowed_ssids": ["Corporate"],
        "wired_vlan": 10, "auth_method": "dot1x",
    },
    # ── Google ──
    {
        "hostname_prefix": "PIXEL",
        "manufacturer": "Google", "oui": "f4f5d8",
        "os": ["Android 14"], "family": "Android", "model": "Pixel",
        "dhcp_vendor_class": "android-dhcp-14", "dhcp_request_params": "1 3 6 15 26 28 51 58 59 43",
        "wireless_weight": 4, "wired_weight": 0,
        "allowed_ssids": ["Corporate", "Guest"],
        "wired_vlan": None, "auth_method": None,
    },
    # ── Cisco VoIP ──
    {
        "hostname_prefix": "VOIP",
        "manufacturer": "Cisco", "oui": "001b0d",
        "os": ["Cisco IP Phone"], "family": "Cisco", "model": "IP Phone 8845",
        "dhcp_vendor_class": "Cisco Systems, Inc. IP Phone", "dhcp_request_params": "1 66 6 3 15 150 35",
        "wireless_weight": 1, "wired_weight": 8,
        "allowed_ssids": ["IoT"],
        "wired_vlan": 40, "auth_method": "mac_auth",
    },
    # ── Zebra scanners ──
    {
        "hostname_prefix": "SCANNER",
        "manufacturer": "Zebra", "oui": "00a0f8",
        "os": ["Android 11"], "family": "Android", "model": "TC52",
        "dhcp_vendor_class": "android-dhcp-11", "dhcp_request_params": "1 3 6 15 26 28 51 58 59 43",
        "wireless_weight": 3, "wired_weight": 2,
        "allowed_ssids": ["Corporate", "IoT"],
        "wired_vlan": 30, "auth_method": "mac_auth",
    },
]

# SSID → security mapping (realistic enterprise config)
SSID_KEY_MGMT = {
    "Corporate": ["wpa2-eap", "wpa3-sae"],
    "Guest": ["open"],
    "IoT": ["wpa2-psk"],
}

BANDS = ["24", "5", "6"]
CHANNELS_24 = [1, 6, 11]
CHANNELS_5 = [36, 40, 44, 48, 149, 153, 157, 161]
CHANNELS_6 = [1, 5, 9, 13, 17, 21]

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
        ap_map_id: str = None,
        site_maps: list = None,
        client_index: int = 0,
        site_index: int = 0,
    ) -> dict:
        """
        Generate a wireless client matching Mist /stats/clients response.

        All fields are correlated: profile determines allowed SSIDs,
        SSID determines VLAN and key_mgmt, OUI matches device type.
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

        # SSID from profile's allowed list → VLAN from SSID → key_mgmt from SSID
        ssid = random.choice(profile["allowed_ssids"])
        vlan_id = SSID_VLAN_MAP[ssid]
        key_mgmt = random.choice(SSID_KEY_MGMT[ssid])
        now = int(datetime.utcnow().timestamp())

        ap_id_val = ap_id or str(uuid.uuid4())
        wlan_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"wlan-{ssid}"))

        # Place client on same map as its AP, with randomized coordinates
        map_id = ap_map_id
        x = None
        y = None
        x_m = None
        y_m = None
        num_locating_aps = None
        if map_id and site_maps:
            site_map = next((m for m in site_maps if m["id"] == map_id), None)
            if site_map:
                w = site_map.get("width", 1650)
                h = site_map.get("height", 2550)
                w_m = site_map.get("width_m", 57.0)
                h_m = site_map.get("height_m", 88.0)
                x = round(random.uniform(50.0, float(w) - 50), 2)
                y = round(random.uniform(50.0, float(h) - 50), 2)
                x_m = round(x / (float(w) / w_m), 6)
                y_m = round(y / (float(h) / h_m), 6)
                num_locating_aps = random.randint(1, 4)

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
            "key_mgmt": key_mgmt,
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
            "group": "",
            "psk_id": "",
            "annotation": "unknown",
            "_ttl": random.randint(100, 600),
            "_id": mac,
            "map_id": map_id,
            "x": x,
            "y": y,
            "x_m": x_m,
            "y_m": y_m,
            "num_locating_aps": num_locating_aps,
        }

    def generate_wired_client(
        self,
        site_id: str,
        org_id: str,
        device_mac: str = None,
        port_id: str = None,
        client_index: int = 0,
        site_index: int = 0,
    ) -> dict:
        """
        Generate a wired client matching Mist wired_clients/search response.

        VLAN and auth_method are determined by profile (device type):
        - Laptops/desktops → Corporate VLAN 10, dot1x
        - Printers/scanners → IoT VLAN 30, mac_auth
        - VoIP phones → Voice VLAN 40, mac_auth
        """
        profile = random.choice(self._wired_profiles)
        vlan_id = profile["wired_vlan"]
        auth_method = profile["auth_method"]
        # VLAN name from network templates
        vlan_names = {10: "Corporate", 20: "Guest", 30: "IoT", 40: "Voice", 50: "Server"}
        vlan_name = vlan_names.get(vlan_id, "")

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
            "last_vlan_name": vlan_name,
            "last_device_mac": dev_mac,
            "dhcp_hostname": hostname.lower(),
            "dhcp_fqdn": f"{hostname.lower()}.{vlan_name.lower()}.local" if vlan_name else f"{hostname.lower()}.local",
            "dhcp_client_identifier": mac,
            "dhcp_client_options": [],
            "dhcp_vendor_class_identifier": profile["dhcp_vendor_class"],
            "dhcp_request_params": profile["dhcp_request_params"],
            "auth_state": "authenticated",
            "auth_method": auth_method,
        }

    def generate_wireless_clients_for_site(
        self, site_id: str, devices: list[dict], count: int, site_index: int = 0,
        site_maps: list = None,
    ) -> list[dict]:
        """Generate wireless clients distributed across APs with location data."""
        aps = [d for d in devices if d.get("type") == "ap"]
        clients = []
        for i in range(count):
            ap = random.choice(aps) if aps else None
            client = self.generate_wireless_client(
                site_id=site_id,
                ap_mac=ap.get("mac") if ap else None,
                ap_id=ap.get("id") if ap else None,
                ap_map_id=ap.get("map_id") if ap else None,
                site_maps=site_maps,
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
                client_index=i,
                site_index=site_index,
            )
            clients.append(client)
        return clients
