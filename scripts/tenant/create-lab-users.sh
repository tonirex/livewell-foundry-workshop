#!/usr/bin/env bash
# create-lab-users.sh — 20 cloud-only lab accounts + a break-glass account (SPEC.md §12.2). Idempotent.
#
#   scripts/tenant/create-lab-users.sh [env] [--count N] [--reset-passwords] [--no-break-glass]
#                                            [--delete] [--dry-run]
#
# Needs User Administrator (Privileged Role Administrator for the break-glass Global Administrator
# role) in the tenant of <env>. Names, count and usage location (SG) come from workshop.yaml
# environments.<env>.lab_accounts. Temporary passwords go to .azure/<env>/lab-accounts.csv (gitignored).
# MFA: keep Entra security defaults ON (no Entra P1 needed); users register Authenticator at first sign-in.
. "$(dirname "$0")/../lib/common.sh"

ENV_ARG=""
PASS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --count) PASS+=("$1" "$2"); shift ;;
    --reset-passwords|--no-break-glass|--delete|--dry-run) PASS+=("$1") ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    -*) die "unknown option $1" ;;
    *) ENV_ARG="$1" ;;
  esac
  shift
done
load_azd_env "$ENV_ARG"
export AZURE_TENANT_ID="${AZURE_TENANT_ID:-$(cfg "environments.$AZURE_ENV_NAME.tenant_id")}"
[ "$AZURE_TENANT_ID" = "TODO" ] && unset AZURE_TENANT_ID
exec "$PY" "$ROOT/scripts/lib/lab_users.py" "${PASS[@]}"
