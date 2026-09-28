# TENANT-BOOTSTRAP — delivering in the sponsored subscription's tenant

The delivery subscription (Azure sponsorship) lives in a **different Entra tenant** from the MCAPS dry-run
environment. This runbook takes an empty tenant to a green `sponsor` environment (SPEC.md §12.2). Everything
carries over from the dry run except GUIDs, RBAC, lab accounts and tenant settings, which scripts or this page
re-create.

- [Step 0: can we skip all of this?](#step-0-can-we-skip-all-of-this)
- [Step 1: admin roles and tenant basics](#step-1-admin-roles-and-tenant-basics)
- [Fabric tenant settings](#fabric-tenant-settings)
- [Step 2: Azure subscription preparation](#step-2-azure-subscription-preparation)
- [Step 3: lab accounts](#step-3-lab-accounts)
- [Step 4: build and prove the sponsor environment](#step-4-build-and-prove-the-sponsor-environment)
- [Checklist](#checklist)

## Step 0: can we skip all of this?

First check whether the sponsorship offer allows the Azure **Change directory** transfer into the MCAPS tenant.
If it does, the subscription joins the tenant where the dry run already works, and this runbook is unnecessary:
use `infra/env/mcaps.bicepparam` settings with the sponsor subscription ID.

1. Azure portal → **Subscriptions** → the sponsorship subscription → **Overview** → **Change directory**.
2. The **subscription Owner** starts the transfer. An **Entra admin in the destination tenant** must accept it.
3. **Restrictions:** CSP subscriptions are excluded. Every Azure role assignment is lost and must be re-created;
   `scripts/provision.sh` and `scripts/seed-attendees.sh` do that. Managed identities are re-created by the template.
4. If the button is greyed out, or the offer type says it is not supported, continue with Step 1.

Record the outcome in [ASSUMPTIONS.md](../../ASSUMPTIONS.md) under "Values Antonia must supply".

## Step 1: admin roles and tenant basics

| Check | How | Needed for |
|---|---|---|
| You are **Global Administrator** (or hold **Fabric Administrator** + **User Administrator**) | Entra admin centre → Roles & admins → My roles | Tenant settings, lab accounts |
| Tenant country/region is **Singapore** | Entra admin centre → Overview → Properties | Data residency statement, lab-account usage location |
| The facilitator account is a **member** (not a guest) of this tenant | Entra → Users → user type = Member | Fabric capacity admin must be a member UPN |
| Security defaults are **on** | Entra → Overview → Properties → Manage security defaults | MFA for lab accounts without Entra P1 |
| The facilitator has a Fabric licence | Sign in once at https://app.fabric.microsoft.com (the Free licence is assigned on first sign-in) | Fabric REST / `fab` calls (otherwise `UserNotLicensed`) |

Put the facilitator UPN(s) into [workshop.yaml](../config/workshop.yaml) `environments.sponsor.facilitator_upns`, and into
`fabricAdminMembers` and `budgetContactEmails` in `infra/env/sponsor.bicepparam`. Put the subscription and tenant IDs
into `environments.sponsor`.

## Fabric tenant settings

Fabric admin portal (app.fabric.microsoft.com → Settings → Admin portal → **Tenant settings**). Scope each setting to a
security group (for example `sg-livewell-workshop` containing the facilitators and lab accounts) rather than the whole
organisation, except where noted.

| Setting | Value | Why |
|---|---|---|
| Users can create Fabric items | Enabled (group) | Lakehouse, notebook, ontology, data agent |
| Ontology item (preview) | Enabled (group) | `resident_ontology` |
| Fabric data agent | Enabled (group) | `Resident360 Ontology Agent` |
| Users can use Copilot and other features powered by Azure OpenAI | Enabled (group) | Data agent runtime |
| Data sent to Azure OpenAI can be processed outside your capacity's geographic region… | Enabled | Enable even though Sweden Central is in the EU |
| Data sent to Azure OpenAI can be stored outside your capacity's geographic region… | Enabled | Same |
| Service principals can use Fabric APIs | Enabled (group) | Automation fallback; runtime still uses user identity |
| Create workspaces | Enabled for the **facilitator group only** | Attendees do not create workspaces |

Allow up to **one hour** for the settings to propagate before running `scripts/fabric/deploy.sh`.
`bash scripts/preflight.sh sponsor` (check 8) reads the tenant settings through the Fabric admin API.

## Step 2: Azure subscription preparation

```bash
az login --tenant <sponsor-tenant-id>
az account set --subscription <sponsor-subscription-id>
azd auth login --tenant-id <sponsor-tenant-id>
azd env new sponsor --subscription <sponsor-subscription-id> --location swedencentral
bash scripts/preflight.sh sponsor      # registers resource providers; prints quota links for any FAIL
```

On a fresh subscription, expect to request:

- **Fabric capacity units:** 2 CU in `swedencentral`. This is often 0 on a new subscription. The Fabric trial is refused;
  the workshop needs a paid F2 or larger.
- **Foundry model quota** in `swedencentral`: `model-router`, `gpt-4.1-mini` and `text-embedding-3-large`,
  100K TPM each, Global Standard.

Lead time for quota can be several business days. Start this at T-10 (see [ADMIN-SETUP.md](ADMIN-SETUP.md#t-10-quota-requests)).

## Step 3: lab accounts

```bash
bash scripts/tenant/create-lab-users.sh sponsor --dry-run    # shows hpb.lab01 … hpb.lab20 + hpb.breakglass
bash scripts/tenant/create-lab-users.sh sponsor
```

- The script creates 20 cloud-only accounts `hpb.lab01`…`hpb.lab20` on the tenant's default domain, with usage
  location **SG** and a temporary password. The password must be changed at first sign-in, when security defaults
  also force Authenticator registration.
- It also creates a **break-glass** account `hpb.breakglass`: Global Administrator, no forced password change. Exclude
  it from any Conditional Access policy and keep its password offline.
- Temporary passwords are written to `.azure/sponsor/lab-accounts.csv`, which is gitignored and never printed. Print one card
  per account. Personal laptops only: WOG devices cannot sign in to an external tenant.
- Re-running is safe. Use `--reset-passwords` to issue new passwords, or `--delete` after the workshop.

## Step 4: build and prove the sponsor environment

Same sequence as the dry run ([ADMIN-SETUP.md → T-3](ADMIN-SETUP.md#t-3-build-the-environment)):

```bash
bash scripts/provision.sh sponsor --what-if       # capacity admins = member UPNs in THIS tenant
bash scripts/cost-guardrails.sh sponsor
bash scripts/fabric/deploy.sh sponsor             # Phase 3
# Fabric IQ connection: portal runbook step (content/labs/fabric-step.md), needs Foundry Project Manager
bash scripts/seed-attendees.sh sponsor --lab-accounts
python scripts/smoke-test.py && python scripts/validate-narrative.py
bash scripts/capacity.sh suspend sponsor
```

Then run a **full second dry run** with a lab account in a private browser window.

## Checklist

- [ ] Step 0 answered (Change directory possible? yes/no)
- [ ] Global / Fabric / User Administrator confirmed; tenant country Singapore; facilitator is a member
- [ ] Facilitator signed in once to app.fabric.microsoft.com
- [ ] Fabric tenant settings enabled and propagated (≥ 1 h)
- [ ] `workshop.yaml` `environments.sponsor` and `infra/env/sponsor.bicepparam` have no TODO left
- [ ] Fabric CU and model quota granted; `preflight.sh sponsor` all PASS
- [ ] Lab accounts + break-glass created; password cards printed
- [ ] `provision.sh sponsor` → `cost-guardrails.sh sponsor` green; budget alerts at US$150 / US$300
- [ ] Fabric deploy, Fabric IQ connection, `seed-attendees.sh`, smoke test and narrative gate green
- [ ] Capacity paused
