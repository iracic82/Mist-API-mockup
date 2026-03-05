"""
Organization and user self data generator for Mock Mist API.

Generates realistic Mist organization and user profile data.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Optional


class OrganizationGenerator:
    """Generator for Mist organization and user self data."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def _deterministic_uuid(self, name: str, seed: int) -> str:
        """Generate a deterministic UUID from a name and seed."""
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{name}-{seed}"))

    def generate_organization(
        self,
        org_id: str,
        name: str,
    ) -> dict:
        """
        Generate an organization matching Mist API format.

        Key fields: id, name, created_time, modified_time, allow_mist,
        session_expiry, orggroup_ids, msp_id
        """
        now = int(datetime.utcnow().timestamp())
        created = now - random.randint(86400 * 30, 86400 * 365)

        return {
            "id": org_id,
            "name": name,
            "created_time": created,
            "modified_time": now - random.randint(0, 86400 * 7),
            "allow_mist": True,
            "session_expiry": 1440,
            "orggroup_ids": [],
            "msp_id": "",
            "mist_nac": {
                "enabled": False
            },
        }

    def generate_user_self(
        self,
        email: str,
        first_name: str,
        last_name: str,
        org_id: str,
        org_name: str,
    ) -> dict:
        """
        Generate user self data matching GET /api/v1/self response.

        Key fields: email, first_name, last_name, phone, privileges,
        session_expiry, tags, via_sso
        """
        now = int(datetime.utcnow().timestamp())

        return {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "phone": "+1-408-555-0100",
            "via_sso": False,
            "session_expiry": now + 86400,
            "tags": ["admin"],
            "privileges": [
                {
                    "scope": "org",
                    "org_id": org_id,
                    "org_name": org_name,
                    "role": "admin",
                    "views": ["analytics", "monitoring"],
                    "site_id": None,
                }
            ],
        }
