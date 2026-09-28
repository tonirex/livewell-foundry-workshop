#!/usr/bin/env bash
# provision.sh — azd provision wrapper for the LiveWell workshop (SPEC.md §8.4). Idempotent.
#
#   scripts/provision.sh <env> [--what-if] [--what-if-only] [--skip-preflight]
#
#   env              mcaps | sponsor (an infra/env/<env>.bicepparam must exist)
#   --what-if        run `az deployment group what-if` first and print the change set
#   --what-if-only   stop after the what-if (nothing is deployed)
#   --skip-preflight do not run scripts/preflight.sh first (it runs by default)
#
# Always provision through this script (or run scripts/select-params.py yourself first): azd reads
# infra/main.bicepparam BEFORE its preprovision hook runs, so the per-env parameter file must be in
# place before `azd provision` starts.
. "$(dirname "$0")/lib/common.sh"

ENV_NAME=""; WHATIF=0; WHATIF_ONLY=0; PREFLIGHT=1
for arg in "$@"; do
  case "$arg" in
    --what-if) WHATIF=1 ;;
    --what-if-only) WHATIF=1; WHATIF_ONLY=1 ;;
    --skip-preflight) PREFLIGHT=0 ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    -*) die "unknown option $arg" ;;
    *) ENV_NAME="$arg" ;;
  esac
done
[ -n "$ENV_NAME" ] || die "usage: scripts/provision.sh <env> [--what-if] [--what-if-only] [--skip-preflight]"
[ -f "$ROOT/infra/env/$ENV_NAME.bicepparam" ] || die "no infra/env/$ENV_NAME.bicepparam"
cd "$ROOT"

export AZURE_ENV_NAME="$ENV_NAME"
SUB="$(cfg "environments.$ENV_NAME.subscription_id")"
[ -n "$SUB" ] && [ "$SUB" != "TODO" ] || die "environments.$ENV_NAME.subscription_id is TODO in content/config/workshop.yaml"
RG="$(cfg names.resource_group)"
LOCATION="$(cfg names.location)"

# 1 azd environment (create if missing) + the three values the template cannot derive itself.
if ! azd_ env list --output json 2>/dev/null | tr -d '\r' | grep -q "\"Name\": \"$ENV_NAME\""; then
  log "creating azd env $ENV_NAME"
  azd_ env new "$ENV_NAME" --subscription "$SUB" --location "$LOCATION" --no-prompt >/dev/null
fi
azd_ env select "$ENV_NAME" >/dev/null
CUR_LOC="$(azd_ env get-value AZURE_LOCATION 2>/dev/null | tr -d '\r' || true)"
case "$CUR_LOC" in ""|*" "*) azd_ env set AZURE_LOCATION "$LOCATION" >/dev/null ;; esac
azd_ env set AZURE_SUBSCRIPTION_ID "$SUB" >/dev/null
azd_ env set AZURE_RESOURCE_GROUP "$RG" >/dev/null
az account set --subscription "$SUB" >/dev/null
load_azd_env
log "env=$ENV_NAME subscription=$SUB rg=$RG location=$AZURE_LOCATION"

# 2 preflight (fails fast on quota / region / permissions).
if [ "$PREFLIGHT" = "1" ]; then
  log "running preflight"
  bash "$ROOT/scripts/preflight.sh" "$ENV_NAME" || die "preflight failed — fix the FAIL lines above (or --skip-preflight if you accept them)"
fi

# 3 parameters + principal + resource group (the same step azd runs as its preprovision hook).
pyrun "$ROOT/scripts/select-params.py"
load_azd_env

# 4 what-if (review before the first deployment into a subscription).
if [ "$WHATIF" = "1" ]; then
  log "what-if against $RG"
  az deployment group what-if -g "$RG" -n "livewell-whatif-$ENV_NAME" \
    --template-file "$ROOT/infra/main.bicep" --parameters "$ROOT/infra/main.bicepparam" \
    --result-format FullResourcePayloads --no-pretty-print -o json > "$ROOT/.azure/$ENV_NAME/whatif.json" ||
    die "what-if failed"
  pyrun - "$ROOT/.azure/$ENV_NAME/whatif.json" <<'EOF'
import json, sys
from collections import Counter
changes = json.load(open(sys.argv[1], encoding="utf-8")).get("changes", [])
count = Counter(c["changeType"] for c in changes)
for c in changes:
    rid = c["resourceId"].split("/providers/", 1)[-1]
    print(f"  {c['changeType']:<10} {rid}")
print("  summary: " + ", ".join(f"{k}={v}" for k, v in sorted(count.items())))
bad = [c for c in changes if c["changeType"] in ("Delete",)]
if bad:
    print("  WARNING: the what-if deletes resources:", *[b["resourceId"] for b in bad], sep="\n    ")
    sys.exit(2)
EOF
  [ "$WHATIF_ONLY" = "1" ] && { log "what-if only: nothing deployed"; exit 0; }
fi

# 5 provision.
log "azd provision (≈15 min on a fresh subscription)"
azd_ provision --no-prompt
load_azd_env

# 6 values sheet for facilitators.
pyrun "$ROOT/scripts/render-values.py" "$ENV_NAME"

echo
ok "provisioned $ENV_NAME: project $AZURE_AI_PROJECT_NAME in $AZURE_AI_ACCOUNT_NAME ($AZURE_LOCATION)"
if [ -n "${FABRIC_CAPACITY_NAME:-}" ]; then
  warn "Fabric capacity $FABRIC_CAPACITY_NAME is RUNNING (~US\$0.36/h). Pause it when idle: scripts/capacity.sh suspend"
fi
echo "Next: scripts/cost-guardrails.sh $ENV_NAME · scripts/fabric/deploy.sh (Phase 3) · scripts/seed-attendees.sh"
