"""
Single-pass stress test for the Mist bench mock API.

Simulates exactly what the connector does in one sync:
  - fetch all sites
  - for every site concurrently: wired_clients/search + stats/clients (wireless)
  - org-level stats/devices (paginated)

Prints total records and elapsed time.

Usage:
  python3 stress_test.py
  MIST_BENCH_API_KEY="<key>" python3 stress_test.py

When MIST_BENCH_API_KEY is not set the script pulls the key from Secrets Manager
using the okta-sso AWS profile.
"""
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.error
import urllib.request

BASE_URL = "https://mist-api-bench.highvelocitynetworking.com"
ORG_ID   = "fbf72635-a426-5255-a2c6-dd28b0e8742a"
WORKERS  = 40   # concurrent threads, same order of magnitude as the connector

API_KEY = os.environ.get("MIST_BENCH_API_KEY") or subprocess.check_output(
    ["aws", "secretsmanager", "get-secret-value",
     "--profile", "okta-sso", "--region", "eu-west-1",
     "--secret-id", "mist-mock-api/api-key-bench",
     "--query", "SecretString", "--output", "text"],
    text=True,
).strip()

HEADERS = {
    "Authorization": f"Token {API_KEY}",
    "User-Agent": "AssetInsights/1.0 Infoblox",
}


def get(path, params=""):
    url = f"{BASE_URL}{path}{'?' + params if params else ''}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read()), resp.headers
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} on {path}", file=sys.stderr)
        return None, None


def get_all_pages(path, limit=1000):
    results = []
    page = 1
    while True:
        data, _ = get(path, f"limit={limit}&page={page}")
        if data is None:
            break
        chunk = data if isinstance(data, list) else data.get("results", [])
        results.extend(chunk)
        if len(chunk) < limit:
            break
        page += 1
    return results


def get_wired(site_id):
    results = []
    path = f"/api/v1/sites/{site_id}/wired_clients/search"
    data, _ = get(path, "limit=1000")
    if data is None:
        return results
    results.extend(data.get("results", []))
    while data.get("next"):
        data, _ = get(data["next"])
        if data is None:
            break
        results.extend(data.get("results", []))
    return results


def get_wireless(site_id):
    data, _ = get(f"/api/v1/sites/{site_id}/stats/clients", "limit=1000")
    if data is None:
        return []
    return data if isinstance(data, list) else []


def fetch_site(site):
    sid = site["id"]
    return len(get_wired(sid)), len(get_wireless(sid))


t0 = time.time()

print("Step 1: fetching all sites ...")
sites = get_all_pages(f"/api/v1/orgs/{ORG_ID}/sites")
print(f"  {len(sites)} sites found  ({time.time()-t0:.1f}s)")

print(f"\nStep 2: concurrent wired + wireless fetch across all {len(sites)} sites ...")
wired_total    = 0
wireless_total = 0
errors         = 0

t1 = time.time()
with ThreadPoolExecutor(max_workers=WORKERS) as pool:
    futures = {pool.submit(fetch_site, s): s for s in sites}
    done = 0
    for f in as_completed(futures):
        done += 1
        try:
            w, wl = f.result()
            wired_total    += w
            wireless_total += wl
        except Exception:
            errors += 1
        if done % 50 == 0 or done == len(sites):
            pct = done / len(sites) * 100
            print(
                f"  {done}/{len(sites)} sites ({pct:.0f}%)  "
                f"wired={wired_total:,}  wireless={wireless_total:,}  "
                f"elapsed={time.time()-t1:.1f}s",
                flush=True,
            )

print("\nStep 3: fetching org-level devices ...")
devices = get_all_pages(f"/api/v1/orgs/{ORG_ID}/stats/devices")
print(f"  {len(devices):,} devices")

total   = wired_total + wireless_total + len(devices)
elapsed = time.time() - t0

print()
print("=" * 55)
print(f"  Wired clients   : {wired_total:>8,}")
print(f"  Wireless clients: {wireless_total:>8,}")
print(f"  Devices         : {len(devices):>8,}")
print(f"  {'─' * 29}")
print(f"  TOTAL assets    : {total:>8,}")
print(f"  Sites           : {len(sites):>8,}")
print(f"  Errors          : {errors:>8,}")
print(f"  Elapsed         : {elapsed:>7.1f}s")
print("=" * 55)
print()
if errors == 0:
    print("All records fetched in a single pass with zero errors.")
else:
    print(f"WARNING: {errors} site(s) returned errors.")
