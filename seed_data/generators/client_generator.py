"""
Client data generator for Mock Mist API.

Generates wireless and wired client data matching Mist API response schemas.
"""

import random
import string
import uuid
from datetime import datetime, timedelta
from typing import Optional


# Client manufacturers with OUI prefixes (Mist MACs are no-colon lowercase hex)
CLIENT_MANUFACTURERS = [
    {"name": "Apple", "oui": "3ce072", "weight": 15, "os": ["iOS 17", "iOS 16"]},
    {"name": "Apple", "oui": "a483e7", "weight": 10, "os": ["macOS Sonoma", "macOS Ventura"]},
    {"name": "Samsung", "oui": "8425db", "weight": 12, "os": ["Android 14", "Android 13"]},
    {"name": "Dell", "oui": "f8b156", "weight": 12, "os": ["Windows 11", "Windows 10"]},
    {"name": "HP", "oui": "10b676", "weight": 10, "os": ["Windows 11", "Windows 10"]},
    {"name": "Lenovo", "oui": "28d244", "weight": 10, "os": ["Windows 11", "Windows 10"]},
    {"name": "Microsoft", "oui": "281878", "weight": 5, "os": ["Windows 11"]},
    {"name": "Google", "oui": "f4f5d8", "weight": 5, "os": ["Android 14", "Chrome OS"]},
    {"name": "Cisco", "oui": "001b0d", "weight": 3, "os": ["Cisco IP Phone"]},
    {"name": "Zebra", "oui": "00a0f8", "weight": 3, "os": ["Android 11"]},
    {"name": "HP", "oui": "c8b5ad", "weight": 3, "os": ["Embedded"]},
]

SSIDS = ["Corporate", "Guest", "IoT"]
BANDS = ["2.4", "5", "6"]
CHANNELS_24 = [1, 6, 11]
CHANNELS_5 = [36, 40, 44, 48, 149, 153, 157, 161]
CHANNELS_6 = [1, 5, 9, 13, 17, 21]

HOSTNAMES = [
    "LAPTOP", "DESKTOP", "IPHONE", "MACBOOK", "GALAXY", "SURFACE",
    "PRINTER", "SCANNER", "VOIP", "IPAD", "PIXEL", "THINKPAD",
]

KEY_MGMTS = ["wpa2-psk", "wpa3-sae", "wpa2-eap", "open"]
PROTOS = ["a", "ac", "ax", "n"]
OS_FAMILIES = ["Apple", "Windows", "Android", "Linux", "Chrome OS"]


class ClientGenerator:
    """Generator for Mist wireless and wired client data."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        self._manufacturers = []
        for m in CLIENT_MANUFACTURERS:
            self._manufacturers.extend([m] * m["weight"])

    def _generate_mac(self, oui: str = None) -> str:
        """Generate a Mist-style MAC (lowercase, no colons, 12 hex chars)."""
        if oui:
            suffix = ''.join(f'{random.randint(0, 255):02x}' for _ in range(3))
            return f"{oui}{suffix}"
        return ''.join(f'{random.randint(0, 255):02x}' for _ in range(6))

    def _generate_hostname(self) -> str:
        prefix = random.choice(HOSTNAMES)
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"{prefix}-{suffix}"

    def generate_wireless_client(
        self,
        site_id: str,
        ap_mac: str = None,
        ap_id: str = None,
        vlan_id: int = 10,
        client_index: int = 0,
    ) -> dict:
        """
        Generate a wireless client matching Mist /stats/clients response.

        Key fields: mac, hostname, ip, ssid, band, channel, vlan_id,
        ap_mac, ap_id, rssi, snr, rx_bps, tx_bps, rx_bytes, tx_bytes,
        proto, key_mgmt, manufacture, os, family, model, dual_band,
        is_guest, last_seen, idle_time, uptime
        """
        manufacturer = random.choice(self._manufacturers)
        mac = self._generate_mac(manufacturer["oui"])
        band = random.choice(BANDS)
        if band == "2.4":
            channel = random.choice(CHANNELS_24)
        elif band == "5":
            channel = random.choice(CHANNELS_5)
        else:
            channel = random.choice(CHANNELS_6)

        ssid = random.choice(SSIDS)
        now = int(datetime.utcnow().timestamp())

        return {
            "mac": mac,
            "hostname": self._generate_hostname(),
            "ip": f"10.{vlan_id}.{client_index // 254}.{(client_index % 254) + 2}",
            "ssid": ssid,
            "band": band,
            "channel": channel,
            "vlan_id": vlan_id,
            "ap_mac": ap_mac or self._generate_mac(),
            "ap_id": ap_id or str(uuid.uuid4()),
            "rssi": random.randint(-80, -30),
            "snr": random.randint(10, 50),
            "rx_bps": random.randint(1000, 500000),
            "tx_bps": random.randint(1000, 500000),
            "rx_bytes": random.randint(1000000, 10000000000),
            "tx_bytes": random.randint(1000000, 5000000000),
            "proto": random.choice(PROTOS),
            "key_mgmt": random.choice(KEY_MGMTS),
            "manufacture": manufacturer["name"],
            "os": random.choice(manufacturer["os"]),
            "family": random.choice(OS_FAMILIES),
            "model": manufacturer["name"],
            "dual_band": random.random() < 0.7,
            "is_guest": ssid == "Guest",
            "last_seen": now - random.randint(0, 300),
            "idle_time": random.randint(0, 600),
            "uptime": random.randint(60, 86400 * 7),
        }

    def generate_wired_client(
        self,
        site_id: str,
        org_id: str,
        device_mac: str = None,
        port_id: str = None,
        vlan_id: int = 10,
        client_index: int = 0,
    ) -> dict:
        """
        Generate a wired client matching Mist wired_clients/search response.

        Key fields: mac, ip, device_mac, device_mac_port, port_id,
        vlan, org_id, site_id, timestamp
        """
        manufacturer = random.choice(self._manufacturers)
        mac = self._generate_mac(manufacturer["oui"])
        ip = f"10.{vlan_id}.{client_index // 254}.{(client_index % 254) + 2}"
        dev_mac = device_mac or self._generate_mac()
        p_id = port_id or f"ge-0/0/{random.randint(1, 48)}"
        now = int(datetime.utcnow().timestamp())

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
            "timestamp": now - random.randint(0, 3600),
        }

    def generate_wireless_clients_for_site(
        self, site_id: str, devices: list[dict], count: int
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
            )
            # Internal field for seeding - tracks parent site
            client["_site_id"] = site_id
            clients.append(client)
        return clients

    def generate_wired_clients_for_site(
        self, site_id: str, org_id: str, devices: list[dict], count: int
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
            )
            clients.append(client)
        return clients
