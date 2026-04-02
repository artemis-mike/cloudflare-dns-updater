import pytest
import requests_mock
import os
import sys
import json
from unittest.mock import patch, mock_open

# Add source directory to path to import the script
# We use the absolute path to ensure it works regardless of where pytest is run
source_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../source'))
sys.path.append(source_path)

from update_record import get_config, check_settings, get_public_ip_v4, get_public_ip_v6, get_zone_data, update_record, reconcile

def test_get_config_default(monkeypatch):
    monkeypatch.delenv("CF_UPDATER_ZONE_ID", raising=False)
    monkeypatch.delenv("CF_UPDATER_A_RECORD", raising=False)
    monkeypatch.delenv("CF_UPDATER_AAAA_RECORD", raising=False)
    monkeypatch.delenv("CF_UPDATER_TOKEN", raising=False)
    monkeypatch.delenv("CF_UPDATER_LOGLEVEL", raising=False)
    monkeypatch.delenv("CF_UPDATER_INTERVAL", raising=False)
    monkeypatch.delenv("CF_UPDATER_FORCE_INTERVAL", raising=False)
    
    config = get_config()
    assert config["ZONE_ID"] == ""
    assert config["LOGLEVEL"] == "INFO"
    assert config["INTERVAL"] == 30

def test_check_settings_valid():
    config = {
        "ZONE_ID": "some-zone",
        "A_RECORD": "example.com",
        "AAAA_RECORD": None,
        "TOKEN": "some-token",
        "INTERVAL": 30,
        "FORCE_INTERVAL": False
    }
    assert check_settings(config) == 0

def test_check_settings_invalid_missing_zone():
    config = {
        "ZONE_ID": "",
        "A_RECORD": "example.com",
        "AAAA_RECORD": None,
        "TOKEN": "some-token",
        "INTERVAL": 30,
        "FORCE_INTERVAL": False
    }
    assert check_settings(config) == 1

def test_get_public_ip_v4(requests_mock):
    requests_mock.get("https://ipinfo.io/ip", text="1.2.3.4")
    assert get_public_ip_v4() == "1.2.3.4"

def test_get_zone_data(requests_mock):
    zone_id = "test-zone"
    token = "test-token"
    record = "example.com"
    type = "A"
    
    mock_response = {
        "result": [
            {"name": "example.com", "type": "A", "id": "rec-123", "content": "1.1.1.1"}
        ]
    }
    requests_mock.get(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records", json=mock_response)
    
    id, content = get_zone_data(zone_id, token, record, type)
    assert id == "rec-123"
    assert content == "1.1.1.1"

def test_reconcile_no_update_needed(requests_mock):
    config = {
        "ZONE_ID": "test-zone",
        "A_RECORD": "example.com",
        "AAAA_RECORD": None,
        "TOKEN": "test-token",
        "INTERVAL": 30,
        "FORCE_INTERVAL": False
    }
    
    # Mock IP calls
    requests_mock.get("https://ipinfo.io/ip", text="1.2.3.4")
    
    # Mock Cloudflare calls
    mock_zone_response = {
        "result": [
            {"name": "example.com", "type": "A", "id": "rec-123", "content": "1.2.3.4"}
        ]
    }
    requests_mock.get("https://api.cloudflare.com/client/v4/zones/test-zone/dns_records", json=mock_zone_response)
    
    # Mock file open for lastRun.epoch
    with patch("builtins.open", mock_open()):
        reconcile(config)
    
    # Verify no PUT request was made (no update)
    # 1 for IP, 1 for Cloudflare GET
    assert requests_mock.call_count == 2

def test_reconcile_update_needed(requests_mock):
    config = {
        "ZONE_ID": "test-zone",
        "A_RECORD": "example.com",
        "AAAA_RECORD": None,
        "TOKEN": "test-token",
        "INTERVAL": 30,
        "FORCE_INTERVAL": False
    }
    
    # Mock IP calls
    requests_mock.get("https://ipinfo.io/ip", text="1.2.3.4")
    
    # Mock Cloudflare calls
    mock_zone_response = {
        "result": [
            {"name": "example.com", "type": "A", "id": "rec-123", "content": "1.1.1.1"}
        ]
    }
    requests_mock.get("https://api.cloudflare.com/client/v4/zones/test-zone/dns_records", json=mock_zone_response)
    
    # Mock update call
    requests_mock.put("https://api.cloudflare.com/client/v4/zones/test-zone/dns_records/rec-123", json={"success": True})
    
    # Mock file open for lastRun.epoch
    with patch("builtins.open", mock_open()):
        reconcile(config)
    
    # Verify PUT request was made
    assert requests_mock.called
    assert requests_mock.request_history[2].method == "PUT"
    assert json.loads(requests_mock.request_history[2].text)["content"] == "1.2.3.4"
