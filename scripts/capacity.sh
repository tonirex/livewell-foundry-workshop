#!/usr/bin/env bash
# capacity.sh — pause / resume / resize / show the workshop Fabric capacity (F2 bills ~US$0.36/h while
# Active, F4 ~US$0.76/h).
#
#   scripts/capacity.sh status|suspend|resume [env]
#   scripts/capacity.sh scale F2|F4 [env]
#
# Equivalent to `az fabric capacity suspend|resume|update --sku` (az extension "microsoft-fabric") without
# needing the extension. Resume at T-0 (≈1 min); suspend every evening and at T+1 (SPEC.md §13). `scale` takes
# effect in seconds; also `azd env set FABRIC_SKU <sku>` so the next provision keeps it (ASSUMPTIONS 3b.7).
. "$(dirname "$0")/lib/common.sh"

ACTION="${1:-status}"
if [ "$ACTION" = "scale" ]; then
  SKU="${2:-}"; shift || true
  case "$SKU" in F2|F4|F8|F16|F32|F64) ;; *) die "usage: scripts/capacity.sh scale F2|F4 [env]" ;; esac
fi
load_azd_env "${2:-}"
CAPACITY="${FABRIC_CAPACITY_NAME:-$(cfg names.fabric_capacity)}"
URL="https://management.azure.com/subscriptions/${AZURE_SUBSCRIPTION_ID:?}/resourceGroups/${AZURE_RESOURCE_GROUP:?}/providers/Microsoft.Fabric/capacities/$CAPACITY"
API="api-version=2023-11-01"

state() { azq rest --method get --url "$URL?$API" --query properties.state -o tsv || echo "NotFound"; }
sku() { azq rest --method get --url "$URL?$API" --query sku.name -o tsv || echo "?"; }

case "$ACTION" in
  status) echo "$CAPACITY: $(state) ($(sku))" ;;
  scale)
    [ "$(state)" = "NotFound" ] && die "capacity $CAPACITY not found in $AZURE_RESOURCE_GROUP"
    [ "$(sku)" = "$SKU" ] && { ok "$CAPACITY already $SKU"; exit 0; }
    az rest --method patch --url "$URL?$API" --body "{\"sku\":{\"name\":\"$SKU\",\"tier\":\"Fabric\"}}" -o none
    for _ in $(seq 1 30); do [ "$(sku)" = "$SKU" ] && break; sleep 10; done
    ok "$CAPACITY: $(sku), $(state) (azd env set FABRIC_SKU $SKU keeps it on the next provision)" ;;
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
  *) die "usage: scripts/capacity.sh status|suspend|resume [env] | scale F2|F4 [env]" ;;
esac
