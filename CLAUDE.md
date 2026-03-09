# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository is a **Mock Juniper Mist API** server built with AWS SAM (Lambda + API Gateway + DynamoDB). It simulates the Mist Orchestrator's 9 endpoints for testing the assets-mapping-controller project. Architecture mirrors the Meraki mock API (`/Users/iracic/PycharmProjects/Meraki_Controller_API/`).

## Architecture

- **AWS SAM** — Lambda + API Gateway + DynamoDB (single-table design)
- **Topology switching** via `X-Mock-Topology` header/query param (default: `campus`)
- **Auth** via `Authorization: Token {key}` (Mist-style), backed by AWS Secrets Manager
- **Non-strict auth mode** via `STRICT_AUTH=false` env var (for testing)

## Build & Test Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
PYTHONPATH=src python -m pytest tests/ -v

# Build SAM template
sam build

# Local API
sam local start-api

# Seed local DynamoDB
python seed_data/seed_dynamodb.py --local --clear

# Seed AWS DynamoDB
python seed_data/seed_dynamodb.py --profile okta-sso --region eu-west-1 --clear

# Deploy
sam deploy --profile okta-sso
```

## API Endpoints

| Route | Handler | Pagination |
|-------|---------|------------|
| `GET /api/v1/self` | `validation.get_self` | N/A |
| `GET /api/v1/orgs/{org_id}` | `organizations.get_organization` | N/A |
| `GET /api/v1/orgs/{org_id}/sites` | `sites.list_sites` | page-based (`limit`, `page`, `X-Page-Total`) |
| `GET /api/v1/sites/{site_id}/stats/devices` | `devices.list_device_stats` | page-based + type filter |
| `GET /api/v1/orgs/{org_id}/networks` | `networks.list_org_networks` | page-based |
| `GET /api/v1/sites/{site_id}/stats/clients` | `clients.list_wireless_clients` | limit-based |
| `GET /api/v1/sites/{site_id}/wired_clients/search` | `clients.search_wired_clients` | link-based (`next` URL) |
| `GET /api/v1/sites/{site_id}/networks/derived` | `networks.list_derived_networks` | N/A |
| `GET /api/v1/sites/{site_id}/maps/{map_id}` | `maps.get_site_map` | N/A |
| `GET /api/v1/sites/{site_id}/maps` | `maps.list_site_maps` | page-based |
| Admin routes | `admin.*` | N/A |

## DynamoDB Key Design

| Entity | PK | SK | GSI1PK | GSI1SK |
|--------|----|----|--------|--------|
| user_self | `{topo}#user_self` | `{email}` | — | — |
| organization | `{topo}#organization` | `{org_id}` | — | — |
| site | `{topo}#site` | `{site_id}` | `{topo}#organization#{org_id}` | `site#{site_id}` |
| device_stats | `{topo}#device_stats` | `{device_id}` | `{topo}#site#{site_id}` | `device_stats#{device_id}` |
| org_network | `{topo}#org_network` | `{network_id}` | `{topo}#organization#{org_id}` | `org_network#{network_id}` |
| wireless_client | `{topo}#wireless_client` | `{mac}` | `{topo}#site#{site_id}` | `wireless_client#{mac}` |
| wired_client | `{topo}#wired_client` | `{mac}` | `{topo}#site#{site_id}` | `wired_client#{mac}` |
| derived_network | `{topo}#derived_network` | `{network_id}` | `{topo}#site#{site_id}` | `derived_network#{network_id}` |
| map | `{topo}#map` | `{map_id}` | `{topo}#site#{site_id}` | `map#{map_id}` |

## Campus Topology (Default)

- 1 org ("Acme Corporation"), 13 sites, ~80 devices, ~350 wireless clients, ~410 wired clients, 7 org networks, ~17 maps
- Device types: Juniper APs (AP45, AP43, AP33, AP32, etc.), Switches (EX4400, EX4300, EX2300), Gateways (SRX345, SRX320, SRX1500, SSR120, SSR130)

## Key Conventions

- **IDs**: UUID v4/v5 (deterministic from seed)
- **MAC format**: lowercase no-colon hex (`aabbccddeeff`)
- **Firmware**: AP: `0.14.XXXXX`, Junos: `22.4R3-S3`, SSR: `6.2.5-R2`
- **Auth header**: `Authorization: Token {key}`
- **User-Agent**: `user-agent: AssetInsights/1.0 Infoblox`
- **AWS Profile**: `okta-sso` for deployment
- **Owner tag**: `iracic@infoblox.com`

## Postman Collection

`mist.postman_collection.json` documents the 9 real Mist API endpoints. Collection variables: `baseUrl`, `apiKey`, `org_id`, `site_id`.
