"""
Authentication middleware for Mock Mist API.

Validates the Authorization: Token {key} header against API key stored in AWS Secrets Manager.
"""

import os
import logging
import secrets
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_api_key_from_secrets_manager() -> str:
    """
    Fetch API key from AWS Secrets Manager.
    Cached to avoid repeated calls.
    """
    secret_name = os.environ.get("API_KEY_SECRET_NAME", "mist-mock-api/api-key")

    try:
        client = boto3.client("secretsmanager")
        response = client.get_secret_value(SecretId=secret_name)
        return response["SecretString"]
    except ClientError as e:
        logger.error(f"Failed to get API key from Secrets Manager: {e}")
        raise


def validate_api_key(headers: dict) -> dict:
    """
    Validate the Mist API token from request headers.

    Mist uses: Authorization: Token {key}

    Args:
        headers: Dictionary of request headers (lowercase keys)

    Returns:
        dict with 'valid' boolean and optional 'error' message
    """
    logger.warning(f"DEBUG - All headers received: {list(headers.keys())}")

    # Parse Authorization: Token {key}
    api_key = None
    auth_header = headers.get("authorization", "")
    if auth_header.startswith("Token "):
        api_key = auth_header[6:]
        logger.info("Found API key in Authorization Token header")

    if not api_key:
        logger.warning("Missing API key header")
        return {
            "valid": False,
            "error": "Missing API key. Please include 'Authorization: Token {key}' header."
        }

    # In non-strict mode, accept any token (for testing)
    strict = os.environ.get("STRICT_AUTH", "true").lower()
    if strict == "false":
        logger.info("Non-strict auth mode - accepting any token")
        return {"valid": True}

    try:
        required_key = _get_api_key_from_secrets_manager()
    except Exception as e:
        logger.error(f"Failed to retrieve API key: {e}")
        return {
            "valid": False,
            "error": "API authentication unavailable"
        }

    # Constant-time comparison to prevent timing attacks
    if secrets.compare_digest(api_key, required_key):
        logger.info("API key validated successfully")
        return {"valid": True}
    else:
        logger.warning("Invalid API key provided")
        return {
            "valid": False,
            "error": "Invalid API key"
        }
