#!/usr/bin/env python3
"""Create (or delete) the cloud-only workshop lab accounts via Microsoft Graph.

Called by scripts/tenant/create-lab-users.sh. Idempotent: existing users are left alone (use
--reset-passwords to issue new temporary passwords). Temporary passwords are written to
.azure/<env>/lab-accounts.csv (gitignored) and never printed.

Accounts: <prefix>01..<prefix><count> + <break_glass> @ the tenant's default domain,
usageLocation from workshop.yaml (SG), forceChangePasswordNextSignIn. The break-glass account gets
Global Administrator (entra_roles.global_administrator) and is meant to be excluded from any
Conditional Access policy; MFA for lab accounts comes from security defaults (no Entra P1 needed).
"""
from __future__ import annotations

import argparse
import csv
import os
import secrets
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wsconfig  # noqa: E402
from azrest import Api, ApiError  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def temp_password() -> str:
    alphabet = string.ascii_letters + string.digits
    core = "".join(secrets.choice(alphabet) for _ in range(14))
    return f"Lw-{core}!{secrets.randbelow(90) + 10}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int)
    ap.add_argument("--no-break-glass", action="store_true")
    ap.add_argument("--reset-passwords", action="store_true")
    ap.add_argument("--delete", action="store_true", help="delete the lab accounts (break-glass is kept)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    env = os.environ.get("AZURE_ENV_NAME", "")
    cfg = wsconfig.load(env)
    lab = cfg["environments"].get(env, {}).get("lab_accounts", {})
    prefix = lab.get("prefix", "hpb.lab")
    count = args.count or int(lab.get("count", 20))
    usage = lab.get("usage_location", "SG")
    bg = lab.get("break_glass", "hpb.breakglass")

    graph = Api("graph")
    org = graph.get("/v1.0/organization?$select=id,displayName,countryLetterCode,verifiedDomains")["value"][0]
    domain = next(d["name"] for d in org["verifiedDomains"] if d.get("isDefault"))
    print(f"[create-lab-users] tenant {org['displayName']} (country {org.get('countryLetterCode')}), domain {domain}")
    if org.get("countryLetterCode") not in (None, "SG"):
        print("  WARN  tenant country is not SG (SPEC.md §12.2) — continuing")

    wanted = [(f"{prefix}{i:02d}", f"LiveWell Lab {i:02d}", False) for i in range(1, count + 1)]
    if not args.no_break_glass and not args.delete:
        wanted.append((bg, "LiveWell Break Glass", True))

    out = ROOT / ".azure" / (env or "default") / "lab-accounts.csv"
    rows: list[dict] = []
    if out.exists():
        rows = list(csv.DictReader(out.open(encoding="utf-8")))
    by_upn = {r["upn"]: r for r in rows}
    created = existing = reset = deleted = 0
    for nick, display, is_bg in wanted:
        upn = f"{nick}@{domain}"
        user = graph.get(f"/v1.0/users/{upn}?$select=id,userPrincipalName,usageLocation", ok_404=True)
        if args.delete:
            if user and not args.dry_run:
                graph.delete(f"/v1.0/users/{user['id']}")
            if user:
                deleted += 1
                by_upn.pop(upn, None)
            print(f"  {'would delete' if args.dry_run else 'deleted' if user else 'absent'}  {upn}")
            continue
        if user:
            existing += 1
            if user.get("usageLocation") != usage and not args.dry_run:
                graph.patch(f"/v1.0/users/{user['id']}", {"usageLocation": usage})
            if args.reset_passwords and not args.dry_run:
                pwd = temp_password()
                graph.patch(f"/v1.0/users/{user['id']}", {"passwordProfile": {
                    "forceChangePasswordNextSignIn": True, "password": pwd}})
                by_upn[upn] = {"upn": upn, "display_name": display, "temporary_password": pwd}
                reset += 1
            print(f"  exists   {upn}{' (password reset)' if args.reset_passwords else ''}")
        else:
            if args.dry_run:
                print(f"  would create {upn}")
                continue
            pwd = temp_password()
            user = graph.post("/v1.0/users", {
                "accountEnabled": True, "displayName": display, "mailNickname": nick.replace(".", ""),
                "userPrincipalName": upn, "usageLocation": usage,
                "passwordProfile": {"forceChangePasswordNextSignIn": not is_bg, "password": pwd},
            })
            by_upn[upn] = {"upn": upn, "display_name": display, "temporary_password": pwd}
            created += 1
            print(f"  created  {upn}")
        if is_bg and not args.dry_run:
            role = cfg["entra_roles"]["global_administrator"]
            have = graph.get(f"/v1.0/roleManagement/directory/roleAssignments?$filter=principalId eq "
                             f"'{user['id']}' and roleDefinitionId eq '{role}'").get("value", [])
            if not have:
                try:
                    graph.post("/v1.0/roleManagement/directory/roleAssignments",
                               {"principalId": user["id"], "roleDefinitionId": role, "directoryScopeId": "/"})
                    print(f"  role     Global Administrator -> {upn}")
                except ApiError as e:
                    print(f"  WARN     could not assign Global Administrator to {upn}: {e.code or e.status} "
                          "(needs Privileged Role Administrator)")

    if not args.dry_run:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["upn", "display_name", "temporary_password"])
            w.writeheader()
            w.writerows(sorted(by_upn.values(), key=lambda r: r["upn"]))
    print(f"[create-lab-users] created {created}, existing {existing}, passwords reset {reset}, deleted {deleted}."
          + ("" if args.dry_run else f" Temporary passwords: {out.relative_to(ROOT).as_posix()} (gitignored)."))
    if created or reset:
        print("  Next: print one card per account; first sign-in forces a password change and Authenticator")
        print("  registration (security defaults). Then: scripts/seed-attendees.sh --lab-accounts")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ApiError as e:
        if e.status == 403:
            print(f"[create-lab-users] Graph denied the request ({e.code}). Needs User Administrator "
                  "(and Privileged Role Administrator for the break-glass role) in this tenant.")
            sys.exit(1)
        raise
