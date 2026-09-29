#!/usr/bin/env bash
# Step 20: lakehouse lh_resident360, upload the kit files + scripts/r360.py to Files/livewell/, import
# content/assets/load_resident360.ipynb with the lakehouse attached, run it, then verify the Delta tables,
# Rahim and the headline reference answer against the local build.
# Idempotent: `fab exists` before `fab mkdir`; `fab cp -f` and `fab import -f` overwrite; the notebook
# overwrites its tables.
#   bash scripts/fabric/20-lakehouse-load.sh [env] [--skip-upload] [--skip-run]
. "$(dirname "$0")/../lib/common.sh"
SKIP_RUN=0; SKIP_UPLOAD=0
for a in "$@"; do case "$a" in
  --skip-run) SKIP_RUN=1 ;; --skip-upload) SKIP_UPLOAD=1 ;; -*) die "unknown flag $a" ;; *) ENV_ARG="$a" ;;
esac; done
[ -n "${AZURE_ENV_NAME:-}" ] || load_azd_env "${ENV_ARG:-}"
[ -n "$FAB" ] || die "Fabric CLI not found: pip install ms-fabric-cli==1.7.0, then fab auth login"

WS="$(cfg names.fabric_workspace)"
LH="$(cfg names.lakehouse)"
NB="load_resident360"
LHP="$WS.Workspace/$LH.Lakehouse"
winpath() { if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else printf '%s\n' "$1"; fi; }
exists() { "$FAB" exists "$1" 2>/dev/null | tr -d '\r' | grep -qi '^true'; }
# Run fab quietly; print its output only when it fails.
fabq() { local out; if out="$("$FAB" "$@" 2>&1)"; then return 0; fi; printf '%s\n' "$out" | tr -d '\r' >&2; return 1; }

log "lakehouse $LH in \"$WS\""
exists "$WS.Workspace" || die "workspace \"$WS\" missing: run scripts/fabric/10-workspace.sh first"
if exists "$LHP"; then ok "lakehouse exists"; else
  fabq mkdir "$LHP" || die "fab mkdir $LHP failed"
  ok "lakehouse created (no schemas; tables live under Tables/)"
fi
WS_ID="$("$FAB" get "$WS.Workspace" -q id 2>/dev/null | tr -d '\r' | tail -n1)"
LH_ID="$("$FAB" get "$LHP" -q id 2>/dev/null | tr -d '\r' | tail -n1)"
[ -n "$WS_ID" ] && [ -n "$LH_ID" ] || die "could not read workspace / lakehouse ids"

if [ "$SKIP_UPLOAD" -eq 0 ]; then
  log "upload Files/livewell/ (kit files, generated files, Rahim overlay, r360.py; ~15 s per file)"
  for d in livewell livewell/scripts livewell/resident360; do
    exists "$LHP/Files/$d" || fabq mkdir "$LHP/Files/$d" || die "fab mkdir Files/$d failed"
  done
  fabq cp "$(winpath "$ROOT/scripts/r360.py")" "$LHP/Files/livewell/scripts/r360.py" -f || die "upload r360.py failed"
  n=1
  for f in "$ROOT"/content/data/resident360/*; do
    [ -f "$f" ] || continue
    fabq cp "$(winpath "$f")" "$LHP/Files/livewell/resident360/$(basename "$f")" -f ||
      die "upload $(basename "$f") failed"
    n=$((n + 1))
  done
  ok "uploaded $n files"
else
  warn "--skip-upload: using the files already in Files/livewell/"
fi

log "import notebook $NB (default lakehouse $LH)"
TMP="$(mktempdir)"
trap 'rm -rf "$TMP"' EXIT
NBDIR="$(pyrun "$ROOT/scripts/fabric/notebook.py" prepare --ws-id "$WS_ID" --lh-id "$LH_ID" --lh-name "$LH" --out "$TMP")"
fabq import "$WS.Workspace/$NB.Notebook" -i "$(winpath "$NBDIR")" --format .ipynb -f ||
  die "fab import $NB.Notebook failed"
ok "notebook imported"

if [ "$SKIP_RUN" -eq 0 ]; then
  log "run $NB (Spark session start + load: typically 3-8 min on F2)"
  CONF="$(pyrun "$ROOT/scripts/fabric/notebook.py" run-config --ws-id "$WS_ID" --lh-id "$LH_ID" --lh-name "$LH")"
  "$FAB" job run "$WS.Workspace/$NB.Notebook" -C "$CONF" --timeout 1800 --polling_interval 15 2>&1 | tr -d '\r' ||
    die "notebook run failed: open $NB in the Fabric portal to see the failing cell"
  ok "notebook run completed"
fi

log "verify tables against the local build (scripts/r360.py)"
pyrun "$ROOT/scripts/fabric/notebook.py" verify --ws-id "$WS_ID" --lh-id "$LH_ID" || die "load verification failed"
