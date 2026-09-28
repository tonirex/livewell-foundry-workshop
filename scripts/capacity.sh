#!/usr/bin/env bash
# capacity.sh — pause / resume / show the workshop Fabric capacity (F2 bills ~US$0.36/h while Active).
#
#   scripts/capacity.sh status|suspend|resume [env]
#
# Equivalent to `az fabric capacity suspend|resume` (az extension "microsoft-fabric") without needing
# the extension. Resume at T-0 (≈1 min); suspend every evening and at T+1 (SPEC.md §13).
. "$(dirname "$0")/lib/common.sh"

ACTION="${1:-status}"
load_azd_env "${2:-}"
CAPACITY="${FABRIC_CAPACITY_NAME:-$(cfg names.fabric_capacity)}"
URL="https://management.azure.com/subscriptions/${AZURE_SUBSCRIPTION_ID:?}/resourceGroups/${AZURE_RESOURCE_GROUP:?}/providers/Microsoft.Fabric/capacities/$CAPACITY"
API="api-version=2023-11-01"

state() { azq rest --method get --url "$URL?$API" --query properties.state -o tsv || echo "NotFound"; }

case "$ACTION" in
  status) echo "$CAPACITY: $(state)" ;;
  suspend|pause)
    s="$(state)"
    if [ "$s" = "Paused" ] || [ "$s" = "Suspended" ]; then ok "$CAPACITY already $s"; exit 0; fi
    [ "$s" = "NotFound" ] && die "capacity $CAPACITY not found in $AZURE_RESOURCE_GROUP"
    az rest --method post --url "$URL/suspend?$API" -o none
    for _ in $(seq 1 30); do s="$(state)"; [ "$s" = "Paused" ] && break; sleep 10; done
    ok "$CAPACITY: $s" ;;
  resume|start)
    s="$(state)"
    if [ "$s" = "Active" ]; then ok "$CAPACITY already Active"; exit 0; fi
    [ "$s" = "NotFound" ] && die "capacity $CAPACITY not found in $AZURE_RESOURCE_GROUP"
    az rest --method post --url "$URL/resume?$API" -o none
    for _ in $(seq 1 30); do s="$(state)"; [ "$s" = "Active" ] && break; sleep 10; done
    ok "$CAPACITY: $s (remember: scripts/capacity.sh suspend when done)" ;;
  *) die "usage: scripts/capacity.sh status|suspend|resume [env]" ;;
esac
