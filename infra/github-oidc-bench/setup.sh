#!/usr/bin/env bash
#
# One-time setup for the GitHub Actions -> AWS OIDC trust used by the
# "Reseed bench" workflow (.github/workflows/reseed-bench.yml).
#
# Creates (idempotently):
#   1. The GitHub OIDC identity provider in this AWS account (if missing).
#   2. An IAM role GitHub can assume, trusted ONLY from
#         repo:iracic82/Mist-API-mockup ref:refs/heads/main
#      and permitted ONLY to read/write the MistMock_*_bench DynamoDB tables.
#
# Prereqs: an authenticated AWS session (e.g. `aws sso login --profile okta-sso`)
#          with IAM permissions to create OIDC providers and roles.
#
# Usage:
#   ./infra/github-oidc-bench/setup.sh                 # uses defaults below
#   AWS_PROFILE=okta-sso AWS_REGION=eu-west-1 ./infra/github-oidc-bench/setup.sh
#
set -euo pipefail

AWS_PROFILE="${AWS_PROFILE:-okta-sso}"
AWS_REGION="${AWS_REGION:-eu-west-1}"
ROLE_NAME="${ROLE_NAME:-mist-mock-bench-gha-reseed}"
REPO="iracic82/Mist-API-mockup"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ACCOUNT_ID="$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query Account --output text)"
echo "Account: ${ACCOUNT_ID}  Region: ${AWS_REGION}  Profile: ${AWS_PROFILE}"

# 1. GitHub OIDC provider (idempotent) --------------------------------------
PROVIDER_ARN="arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
if aws iam get-open-id-connect-provider \
      --open-id-connect-provider-arn "$PROVIDER_ARN" \
      --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  echo "OIDC provider already present."
else
  echo "Creating GitHub OIDC provider..."
  aws iam create-open-id-connect-provider \
    --url "https://token.actions.githubusercontent.com" \
    --client-id-list "sts.amazonaws.com" \
    --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1" \
                      "1c58a3a8518e8759bf075b76b750d4f2df264fcd" \
    --profile "$AWS_PROFILE" >/dev/null
fi

# 2. Render the policy templates with this account/region -------------------
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
sed -e "s/__AWS_ACCOUNT_ID__/${ACCOUNT_ID}/g" -e "s/__AWS_REGION__/${AWS_REGION}/g" \
    "$HERE/trust-policy.json" > "$TMP/trust.json"
sed -e "s/__AWS_ACCOUNT_ID__/${ACCOUNT_ID}/g" -e "s/__AWS_REGION__/${AWS_REGION}/g" \
    "$HERE/permissions-policy.json" > "$TMP/perms.json"

# 3. IAM role (create, or refresh its trust policy) -------------------------
if aws iam get-role --role-name "$ROLE_NAME" --profile "$AWS_PROFILE" >/dev/null 2>&1; then
  echo "Role ${ROLE_NAME} exists; refreshing trust policy..."
  aws iam update-assume-role-policy --role-name "$ROLE_NAME" \
    --policy-document "file://$TMP/trust.json" --profile "$AWS_PROFILE"
else
  echo "Creating role ${ROLE_NAME}..."
  aws iam create-role --role-name "$ROLE_NAME" \
    --assume-role-policy-document "file://$TMP/trust.json" \
    --description "GitHub Actions OIDC role to reseed the Mist mock bench DynamoDB tables" \
    --tags Key=Owner,Value=iracic@infoblox.com Key=Application,Value=MistMockAPI \
    --profile "$AWS_PROFILE" >/dev/null
fi

# 4. Least-privilege inline permissions -------------------------------------
aws iam put-role-policy --role-name "$ROLE_NAME" \
  --policy-name "reseed-bench-dynamodb" \
  --policy-document "file://$TMP/perms.json" \
  --profile "$AWS_PROFILE"

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
echo ""
echo "✅ Role ready: ${ROLE_ARN}"
echo ""
echo "Final step — store it as a repo secret so the workflow can assume it:"
echo ""
echo "  gh secret set AWS_BENCH_ROLE_ARN --repo ${REPO} --body \"${ROLE_ARN}\""
echo ""
