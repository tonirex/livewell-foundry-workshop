# Lab 3 · Tools, MCP & Memory — hyper-personalisation

**40 min** · **Part C** · **Audience:** everyone · **Level:** L300 · **Rails:** 🟢 Navigator + 🔵 Builder · **Patterns:** #2 Evidence-Based Decision Support · #3 Workflow Orchestration · #6 Human-in-the-Loop Review · #8 Institutional Memory · #9 Collaboration Between Specialists

**You are here:** [Lab 0](lab-00.md) → [Lab 1](lab-01.md) → [Lab 2](lab-02.md) → **Lab 3** ([Fabric step](fabric-step.md)) → [Lab 4](lab-04.md) → [Bridge spotlight](bridge-spotlight.md) · [README](../../README.md)

## Shared objective

> An agent that acts: personalise on governed data, take real actions with a human in the loop, delegate to specialists, and route each kind of question to the right tool

Patterns: #2 Evidence-Based Decision Support; #3 Workflow Orchestration; #6 Human-in-the-Loop Review; #8 Institutional Memory; #9 Collaboration Between Specialists.

## Foundry features covered

- OpenAPI tool **`livewell_profile`** for the resident profile extract.
- Function tool path for Builder: `get_citizen_profile` with a strict schema and local execution.
- MCP tool from project connection **`livewell-activities-mcp`**, with `register_interest` requiring approval and `find_activities` allowed without approval.
- Memory ⚠️ preview for stated preferences across conversations.
- Connected agents and Agent Framework orchestration: Coach → Nutrition + Activity specialists.
- Optional Fabric IQ bridge ⚠️ preview, covered in [Fabric step](fabric-step.md).

## Story chapter

[Chapter 3](../narrative/rahim.md#chapter-3--its-hazy-today--what-can-i-do-indoors-lab-3--tools-mcp--memory) is where the coach becomes personal and active. Rahim asks for advice based on his own profile, asks for indoor activities near Woodlands, approves an activity registration, and later expects the coach to remember preferences in a new conversation. The optional officer beat routes Mei's programme question to Fabric, but Rahim's citizen questions stay with the knowledge base and profile tool.

## 🟢 Navigator

1. Open your guarded **`livewell-<initials>`** agent.
2. Add the profile API: **Tools** → **Add** → **Add tools** → **Custom** → **OpenAPI tool** → **Create**. Name the tool **`livewell_profile`** (the portal does not accept dashes in tool names) and paste a one-line description. Keep **Authentication method** on **Anonymous**. Open the **Profile OpenAPI spec URL on the values sheet** in a new browser tab, copy all of the JSON, paste it into **OpenAPI 3.0+ schema** and select **Create tool**.
3. Add the activities MCP: **Tools** → **Add** → **Add tools** → **Configured** → select the project connection **`livewell-activities-mcp`** → **Add tool**. (**Custom** → **Model Context Protocol (MCP)** would create a new connection instead.)
4. Configure MCP approval (tool row → **Actions** → **Configure**):
   - `find_activities` needs no approval.
   - `register_interest` must require approval before the tool call proceeds.
5. Enable **Memory** ⚠️ preview if it is available in your project, and switch the agent **Model** to **`gpt-5.4-mini`**: memory is not searched when the agent runs on `model-router`. If memory is not available, stay on `model-router` and skip only the memory checkpoint.
6. In **Instructions**, keep the base, knowledge and safety blocks, then append the [`tools`](../prompts/coach-instructions.md#tools-lab-3) block. Set **Response format** → **JSON schema** and paste all of [`lab3-evidence.schema.json`](../config/schemas/lab3-evidence.schema.json) in place of the Lab 1 schema. Save a new version.
7. Send (`lab3_profile_tailored`):

   ```text
   Based on my profile, what is one change I should make this week?
   ```

   Expect evidence JSON with advice, confidence, supporting guides, rationale and personalisation flags.
8. Send (`lab3_hazy_indoor_signup`):

   ```text
   It's hazy today. What can I do indoors near Woodlands, and can you sign me up?
   ```

   Expect profile + activity lookup in the trace. The coach registers interest only after a clear yes, so if it lists options and asks first, reply `Yes, please sign me up for the first indoor option you found.` in the same chat. Approve the card only when the agent asks to register interest, and pick **Approve → Approve once** (the *Always approve* options skip later approvals).
9. Set memory. Send (`lab3_memory_set`):

   ```text
   By the way, I prefer mornings, and I don't like swimming.
   ```

10. Start a **new conversation** and send (`lab3_memory_recall`):

    ```text
    Any activities you would suggest for me next week?
    ```

    Expect suggestions that respect mornings and avoid swimming or aqua activities.
11. Optional connected-agent view. Send (`lab3_specialists`):

    ```text
    Can you give me a simple meal plan and an exercise plan for this week that fit my glucose results?
    ```

    Navigator may watch the facilitator's connected-agent setup instead of creating specialists. Builder creates **`livewell-<INITIALS>-nutrition`** and **`livewell-<INITIALS>-activity`**.

> **Optional Fabric step (15 min, only when `FABRIC_BRIDGE=true`):** follow [Fabric step](fabric-step.md). When `FABRIC_BRIDGE=false`, the profile tool still works from [citizens.json](../data/citizens.json) and you skip Fabric.

## 🔵 Builder

```bash
INITIALS=abc python content/assets/lab3_tools.py
```

```powershell
$env:INITIALS = "abc"
python content\assets\lab3_tools.py
```

Or open `content/assets/lab3_tools.py` and run it cell by cell in VS Code or Codespaces. Add `--fabric` only when the facilitator confirms `FABRIC_BRIDGE=true`.

What the script does per cell:

1. Loads the session resident from [citizens.json](../data/citizens.json).
2. Creates `get_citizen_profile` as a client-side FUNCTION tool with a strict schema.
3. Answers that function locally from `content/data/citizens.json` and only for the session resident.
4. Attaches the activities MCP connection **`livewell-activities-mcp`** with approval required for `register_interest`, and wakes the MCP server (it scales to zero between sessions, so the first call can take ~25 s).
5. Enables memory when the project exposes the preview capability. The coach with memory runs on **`gpt-5.4-mini`** because memory is not searched behind `model-router`.
6. Creates or updates **`livewell-<INITIALS>-nutrition`** and **`livewell-<INITIALS>-activity`** specialists and gives them to the coach as function tools: the script runs each specialist when the coach calls it and returns the answer.
7. Runs the profile, activity, approval, memory and specialist prompts. Replies use the strict evidence schema, where `supporting_guides` only accepts real guide ids.

Use `--verbose` for tool-call and approval details. Use `--cleanup` to delete only `livewell-<INITIALS>-*` agents. Lines to retype are marked `# 👉`.

## Checkpoint

✅ **Built** a coach that can personalise, search activities, wait for approval and delegate to specialists.

✅ **Did** at least one compound tool run and one evidence JSON reply.

✅ **Learned** which work belongs in instructions, which belongs in tools, and where human approval belongs.

Paste into the checkpoint form: the trace tool-call list for `lab3_hazy_indoor_signup`, the evidence JSON for `lab3_profile_tailored`, and, if memory is enabled, the new-conversation reply for `lab3_memory_recall`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Profile tool is missing | Re-add OpenAPI using the Profile OpenAPI URL shown on the values sheet; do not paste endpoints into this page. |
| Approval card is not shown | Check MCP approval settings. `register_interest` must require approval; `find_activities` can be auto-approved. |
| Agent registers without approval | Stop using that version. Reconfigure MCP approval and re-copy the [`tools`](../prompts/coach-instructions.md#tools-lab-3) block. |
| Memory ⚠️ preview is not available | Skip the memory checkpoint and continue with profile + MCP. |
| Memory recall ignores preferences | Use a new conversation after `lab3_memory_set`, and allow time for memory processing. Check the agent model is `gpt-5.4-mini`, not `model-router`. |
| 400 "must contain the word 'json'" | The response format is **JSON object**. Switch to **JSON schema** and paste [`lab3-evidence.schema.json`](../config/schemas/lab3-evidence.schema.json). |
| Tool call returns another resident or prints the resident identifier | Use the Builder function tool path or re-check the OpenAPI backend; the lab allows only the session resident. |
| 5xx or MCP timeout | Retry once; the Builder script handles transient 5xx and the MCP server may take a moment to wake. |

## Where next

If `FABRIC_BRIDGE=true`, continue to [Fabric step · Add the Resident 360 data agent as a Fabric IQ tool](fabric-step.md). Otherwise go to [Lab 4 · Multi-agent & Hosted deploy](lab-04.md). Keep [README](../../README.md) open for the final checkpoint.
