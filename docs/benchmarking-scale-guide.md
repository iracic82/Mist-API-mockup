# Benchmarking the Mist Mock API at Scale

This guide is for **anyone** who needs to load- or benchmark-test a system that
ingests the Mist API (for example, an Infoblox on-prem host) against a large,
realistic asset inventory — and how to **change the asset count with a simple
pull request**.

It covers three things:

1. [How to reach the benchmark endpoint](#1-reach-the-benchmark-endpoint)
2. [How to change the scale with a PR](#2-change-the-scale-with-a-pr) ← the main flow
3. [One-time setup for the environment owner](#3-one-time-setup-owner-only)

---

## Background: how this works in one paragraph

The mock serves data from DynamoDB partitioned by **topology**. The default
`campus` topology (~840 assets) is what powers demos and must stay untouched.
Benchmarking uses a separate **`scale`** topology that lives in its own
**isolated `bench` deployment** (its own Lambda + DynamoDB tables), so a heavy
load test never affects the demo. An "asset" is what Infoblox counts —
a **device or a client** (`devices + wireless_clients + wired_clients`). Maps,
networks, and sites are scaffolding and are not counted.

The scale of the benchmark is controlled by **one number** in source control, so
changing it is a reviewable pull request — not a console click.

---

## 1. Reach the benchmark endpoint

You need two things from the environment owner (Igor):

| Thing | Example |
|-------|---------|
| **Bench base URL** | `https://mist-api-bench.highvelocitynetworking.com` (custom domain — **no `/Prod`** in the path) |
| **API key** | `Authorization: Token <key>` |

The bench stack defaults its topology to `scale`, so a normal call already
returns the large dataset:

```bash
curl -s "https://mist-api-bench.highvelocitynetworking.com/api/v1/self" \
  -H "Authorization: Token <key>" \
  -H "user-agent: AssetInsights/1.0 Infoblox"
```

To be explicit (or to hit a bench that didn't default to `scale`), add the
topology header:

```bash
curl -s "https://mist-api-bench.highvelocitynetworking.com/api/v1/orgs/<org_id>/sites" \
  -H "Authorization: Token <key>" \
  -H "X-Mock-Topology: scale"
```

Walk the same 9 endpoints as the demo (see the main `README.md`); you'll just
get many more sites, devices, and clients.

---

## 2. Change the scale with a PR

**This is the whole point.** To make the benchmark bigger or smaller, you change
**one constant** and open a PR. No infrastructure knowledge required.

### Step 1 — branch

```bash
git clone https://github.com/iracic82/Mist-API-mockup.git
cd Mist-API-mockup
git checkout -b bench/scale-30k
```

### Step 2 — edit one number

Open `seed_data/topologies/scale.py` and change **`TARGET_ASSETS`**:

```python
# ════════════════════════════════════════════════════════════════════════════
# THE SCALE KNOB — change this one number in a PR to resize the benchmark.
# ════════════════════════════════════════════════════════════════════════════
TARGET_ASSETS = 30000   # was 15000
```

That's the only edit. The generator automatically spreads the new total across
the right number of sites and keeps the data realistic (VLAN segmentation,
SSID/security correlation, client-to-floor-map location — same as the demo).

> **Bounds:** `TARGET_ASSETS` must be between `100` and `500000`. Anything
> outside that range fails fast with a clear error, so a typo can't trigger a
> runaway seed.

### Step 3 — open the PR

```bash
git commit -s -am "bench: scale benchmark to 30k assets"
git push -u origin bench/scale-30k
gh pr create --base main --fill
```

`main` is protected: the PR needs **one approval** before it can merge. That
review is the safety gate on what data the benchmark environment serves.

### Step 4 — merge → it reseeds itself

When the PR merges, the **`Reseed bench`** GitHub Action detects the change to
`scale.py` and reseeds the bench DynamoDB with the new count (via OIDC — no
credentials are stored in the repo). Watch it under the repo's **Actions** tab;
the run summary prints the new asset total.

> Until OIDC is configured (see §3), the Action runs but **skips** the AWS step
> and leaves a notice — so merges are never blocked by a red build. In that
> window, the owner reseeds manually (below).

### Manual reseed (fallback / owner)

Any time you want to apply the current `TARGET_ASSETS` without waiting for CI:

```bash
aws sso login --profile okta-sso   # if your session expired

python seed_data/seed_dynamodb.py \
  --topology scale \
  --config-table MistMock_Config_bench \
  --data-table MistMock_Data_bench \
  --default-topology scale \
  --profile okta-sso --region eu-west-1 \
  --clear
```

**Seeding time:** items are written in batches of 25 to on-demand tables, so
15k assets is a couple of minutes; 100k is proportionally longer. The tables are
`PAY_PER_REQUEST`, so there is no throughput to tune and ~no idle cost between runs.

---

## 3. One-time setup (owner only)

Done once per AWS account. After this, everything above "just works."

### 3a. Deploy the isolated bench stack

Same template as prod, a different `Environment` value → separate Lambda +
DynamoDB, zero impact on the demo:

```bash
sam build
sam deploy \
  --stack-name mist-mock-bench \
  --parameter-overrides Environment=bench DefaultTopology=scale \
  --capabilities CAPABILITY_IAM --resolve-s3 \
  --profile okta-sso --region eu-west-1
```

Grab the API Gateway URL from the stack outputs and hand it (plus the API key)
to whoever is benchmarking. Seed it once with the manual command in §2.

### 3b. Enable auto-reseed (GitHub OIDC)

Creates the OIDC trust + a least-privilege IAM role (DynamoDB on the bench
tables only, assumable only from this repo's `main`):

```bash
aws sso login --profile okta-sso
./infra/github-oidc-bench/setup.sh
# then run the `gh secret set AWS_BENCH_ROLE_ARN ...` line it prints
```

Once the `AWS_BENCH_ROLE_ARN` secret exists, the `Reseed bench` workflow will
reseed automatically on every merge that touches the scale config. Trigger a dry
run any time from **Actions → Reseed bench → Run workflow**.

---

## FAQ

**Does scaling the benchmark affect the demo?**
No. The bench stack has its own Lambda and its own DynamoDB tables. The demo
(`campus`) is a different deployment entirely.

**Can I run it without AWS at all?**
Yes — seed a local DynamoDB and run the API locally:
```bash
python seed_data/seed_dynamodb.py --local --topology scale --default-topology scale
sam local start-api
```

**How exact is the asset count?**
Exact. `TARGET_ASSETS = 15000` produces exactly 15,000 devices + clients
(verified in `tests/test_scale_topology.py`).
