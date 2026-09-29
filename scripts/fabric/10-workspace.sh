#!/usr/bin/env bash
# Step 10: Fabric workspace "HPB Resident 360" on capacity fablivewell<env>; facilitators are Admin.
# Idempotent: `fab exists` before `fab mkdir`; `fab acl set -f` re-applies roles.
#   bash scripts/fabric/10-workspace.sh [env]      (normally run by scripts/fabric/deploy.sh)
. "$(dirname "$0")/../lib/common.sh"
[ -n "${AZURE_ENV_NAME:-}" ] || load_azd_env "${1:-}"
ENV="$AZURE_ENV_NAME"
[ -n "$FAB" ] || die "Fabric CLI not found: pip install ms-fabric-cli==1.7.0, then fab auth login"
"$FAB" auth status >/dev/null 2>&1 || die "fab is not signed in: run 'fab auth login' (same account as az login)"

WS="$(cfg names.fabric_workspace)"
CAP="$(cfg names.fabric_capacity)"
log "workspace \"$WS\" on capacity $CAP (env $ENV)"

CAPS="$(fabric_api GET /v1/capacities)"
read -r CAP_ID CAP_STATE < <(printf '%s' "$CAPS" | pyrun -c 'import json,sys
d=json.load(sys.stdin); n=sys.argv[1]
c=next((c for c in d.get("value",[]) if c.get("displayName")==n), {})
print(c.get("id","-"), c.get("state","-"))' "$CAP")
case "$CAP_STATE" in
  Active) ok "capacity $CAP is Active" ;;
  -)      die "capacity $CAP not visible to you in Fabric: provision it (FABRIC_BRIDGE=true bash scripts/provision.sh $ENV) and make sure you are a capacity admin" ;;
  *)      die "capacity $CAP is $CAP_STATE: bash scripts/capacity.sh resume $ENV" ;;
esac

if "$FAB" exists "$WS.Workspace" 2>/dev/null | tr -d '\r' | grep -qi '^true'; then
  ok "workspace exists"
else
  "$FAB" mkdir "$WS.Workspace" -P "capacityName=$CAP" >/dev/null || die "fab mkdir \"$WS.Workspace\" failed"
  ok "workspace created"
fi

WS_CAP="$("$FAB" get "$WS.Workspace" -q capacityId 2>/dev/null | tr -d '\r' | tail -n1)"
if [ "$WS_CAP" = "$CAP_ID" ]; then
  ok "workspace is on $CAP"
else
  "$FAB" assign ".capacities/$CAP.Capacity" -W "$WS.Workspace" -f >/dev/null && ok "workspace assigned to $CAP" ||
    die "could not assign \"$WS\" to $CAP"
fi

# Facilitators (workshop.yaml environments.<env>.facilitator_upns) -> workspace Admin.
while IFS= read -r upn; do
  [ -n "$upn" ] || continue
  oid="$(azq ad user show --id "$upn" --query id -o tsv)"
  if [ -z "$oid" ]; then warn "facilitator $upn not found in Entra"; continue; fi
  if "$FAB" acl set "$WS.Workspace" -I "$oid" -R admin -f >/dev/null 2>&1; then
    ok "facilitator $upn is workspace Admin"
  elif "$FAB" acl ls "$WS.Workspace" 2>/dev/null | tr -d '\r' | grep -i "$upn" | grep -qi admin; then
    ok "facilitator $upn is workspace Admin (already)"
  else
    bad "could not make $upn workspace Admin"
  fi
done < <(cfg "environments.$ENV.facilitator_upns" 2>/dev/null || true)

WS_ID="$("$FAB" get "$WS.Workspace" -q id 2>/dev/null | tr -d '\r' | tail -n1)"
[ -n "$WS_ID" ] || die "could not read the workspace id"
log "workspace id $WS_ID"
[ "$FAILURES" -eq 0 ] || exit 1
