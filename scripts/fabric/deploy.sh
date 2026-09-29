#!/usr/bin/env bash
# Fabric IQ deploy: workspace -> lakehouse + load -> ontology -> graph refresh -> data agent -> azd env.
# Every step is idempotent and safe to re-run; --from resumes after a failure.
#   bash scripts/fabric/deploy.sh [env] [--from NN] [--only NN] [--skip-upload]
#   steps: 10 workspace | 20 lakehouse-load | 30 ontology | 35 graph-refresh | 40 data-agent | 90 write-env
# Needs: az login + fab auth login as a Fabric admin/capacity admin, capacity Active (scripts/capacity.sh resume),
# and the tenant settings in docs/TENANT-BOOTSTRAP.md (Ontology item, data agent, Copilot/Azure OpenAI).
. "$(dirname "$0")/../lib/common.sh"
FROM=0; ONLY=""; PASS_ARGS=()
while [ $# -gt 0 ]; do case "$1" in
  --from) FROM="$2"; shift 2 ;; --only) ONLY="$2"; shift 2 ;;
  --skip-upload) PASS_ARGS+=(--skip-upload); shift ;;
  -*) die "unknown flag $1" ;; *) ENV_ARG="$1"; shift ;;
esac; done
load_azd_env "${ENV_ARG:-}"
export AZURE_ENV_NAME
[ -n "$FAB" ] || die "Fabric CLI not found: pip install ms-fabric-cli==1.7.0, then fab auth login"

D="$ROOT/scripts/fabric"
STEPS=(10 20 30 35 40 90)
declare -A NAME=([10]=workspace [20]=lakehouse-load [30]=ontology [35]=graph-refresh [40]=data-agent [90]=write-env)
run_step() {
  case "$1" in
    10) bash "$D/10-workspace.sh" ;;
    20) bash "$D/20-lakehouse-load.sh" ${PASS_ARGS[@]+"${PASS_ARGS[@]}"} ;;
    30) pyrun "$D/30-ontology.py" ;;
    35) pyrun "$D/35-graph-refresh.py" ;;
    40) pyrun "$D/40-data-agent.py" ;;
    90) pyrun "$D/90-write-env.py" ;;
  esac
}

TIMINGS=()
TOTAL0=$SECONDS
for s in "${STEPS[@]}"; do
  if [ -n "$ONLY" ]; then [ "$s" = "$ONLY" ] || continue; elif [ "$s" -lt "$FROM" ]; then continue; fi
  log "step $s ${NAME[$s]}"
  t0=$SECONDS
  if ! run_step "$s"; then
    die "step $s ${NAME[$s]} failed after $((SECONDS - t0))s; fix and resume with: bash scripts/fabric/deploy.sh $AZURE_ENV_NAME --from $s"
  fi
  TIMINGS+=("$(printf '%-3s %-15s %4ss' "$s" "${NAME[$s]}" "$((SECONDS - t0))")")
done

echo
log "done in $((SECONDS - TOTAL0))s"
for t in "${TIMINGS[@]}"; do printf '  %s\n' "$t"; done
echo "  Next: bash scripts/seed-attendees.sh $AZURE_ENV_NAME (Fabric Viewer + data agent access), then"
echo "        python scripts/fabric/ask.py \"Which regions have the highest share of disengaged residents?\""
