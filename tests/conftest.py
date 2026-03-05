"""
Test configuration and fixtures for Mock Mist API tests.
"""

import os
import sys

# Set environment variables before importing app modules
os.environ["CONFIG_TABLE"] = "MistMock_Config_test"
os.environ["DATA_TABLE"] = "MistMock_Data_test"
os.environ["DEFAULT_TOPOLOGY"] = "campus"
os.environ["API_KEY_SECRET_NAME"] = "mist-mock-api/api-key"
os.environ["STRICT_AUTH"] = "false"

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
