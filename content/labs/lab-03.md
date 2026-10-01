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

### How the code works

The coach gets five tools, and they run in three different places. That is the main idea of this lab.

| Tool | Kind | Where it runs | Code |
|---|---|---|---|
| `knowledge_base_retrieve` | MCP (`MCPTool`) | Foundry calls the knowledge base | [`kb_tool`](../assets/common/livewell_common.py#L454-L458) |
| `find_activities`, `register_interest` | MCP (`MCPTool`) with approval rules | Foundry calls the activities server, but pauses before `register_interest` | [`activities_tool`](../assets/common/livewell_common.py#L461-L473) |
| `get_citizen_profile` | Function (`FunctionTool`) | **Your script** answers it from `citizens.json` | [`profile_tool`](../assets/common/livewell_common.py#L529-L536), [`get_citizen_profile`](../assets/common/livewell_common.py#L512-L518) |
| `livewell-nutrition`, `livewell-activity` | Function | **Your script** runs a specialist agent and returns its reply | [`specialist()`](../assets/lab3_tools.py#L105-L116) |
| memory search | `MemorySearchPreviewTool` | Foundry searches and updates your memory store | [`memory_tool`](../assets/common/livewell_common.py#L583-L585) |

All of them go into one [`create_agent`](../assets/lab3_tools.py#L128-L136) call, with the evidence schema and the guardrail. The coach runs on `gpt-5.4-mini` when memory is on.

[`lw.ask`](../assets/common/livewell_common.py#L862-L942) is a small loop that handles what comes back from each response:

- **`function_call`.** Foundry cannot run a function tool, so it hands the call back. `ask` looks the name up in `FUNCTIONS`, runs it, and sends the result as a `function_call_output` ([lines 914–925](../assets/common/livewell_common.py#L914-L925)). This is how a profile lookup stays on your side: the function refuses any resident except the signed-in one.
- **`mcp_approval_request`.** Foundry stops before `register_interest` and waits. `ask` calls `approve` (`lw.ask_human` asks you `[y/N]` at the keyboard) and sends an `mcp_approval_response` ([lines 926–931](../assets/common/livewell_common.py#L926-L931)). Nothing is written until you say yes.
- **A message.** This is the final answer; the loop stops.

The specialists are agents used as tools. When the coach calls `livewell-nutrition`, the handler calls `lw.ask(nutrition, ...)`, and the specialist's answer becomes the function result. The Activity specialist gets `find_activities` only, so only the coach can ask you to approve a registration.

For memory, the script waits for the preference to be stored, then asks `lab3_memory_recall` in `lw.new_conversation()`. A new conversation has no chat history, so a correct answer can only come from memory.

The Navigator uses an OpenAPI tool for the profile, which Foundry calls on the server. Builder uses a function tool so that you can see the call arrive in your own code.

## Checkpoint

✅ **Built** a coach that can personalise, search activities, wait for approval and delegate to specialists.

✅ **Did** at least one compound tool run and one evidence JSON reply.

✅ **Learned** which work belongs in instructions, which belongs in tools, and where human approval belongs.

There is nothing to submit. Try the steps first, then open **Expected output** to compare.

<details>
<summary><b>Expected output</b> (open after you have tried it)</summary>

**What this demonstrates.** Hyper-personalisation comes from tools, not from a longer prompt. The coach reads the signed-in resident's profile, searches the guides and community activities, and remembers stated preferences across conversations. Writes are different from reads: registering interest changes something for the resident, so Foundry pauses for a human yes. The evidence schema keeps every answer explainable, with advice, confidence, the guides behind it, a rationale and the profile signals used.

`lab3_profile_tailored`: the trace shows the profile tool (with `resident_id` `me`) and then the knowledge base. The tool output is Rahim's profile. The reply uses it, but never repeats the resident identifier.

![Trace showing the profile tool before the knowledge-base search](screenshots/lab-03/11-profile-trace.png)

`lab3_hazy_indoor_signup`: the coach looks up indoor options, then asks to register. After your yes, the approval card shows the exact call (`register_interest` with an activity id and display name) and waits.

![Approval card for register_interest with Approve and Deny](screenshots/lab-03/12-hazy-indoor-signup.png)

`lab3_memory_recall` in a **new** chat: morning, indoor suggestions and no swimming. Look for `prefers morning` and `dislikes swimming` in `personalisation_flags`, and `memory_search_call` in the chips under the reply.

![New chat recalling the morning preference and avoiding swimming](screenshots/lab-03/15-memory-recall-new-chat.png)

**Builder.** Look for:

- `another resident -> {'error': 'forbidden', ...}`: the profile function only serves the signed-in resident;
- `get_citizen_profile` and `knowledge_base_retrieve` in the `tools:` list of the first answer, with `personalisation_flags` such as `high_screening_risk`, `low_steps` and `region_hazy`;
- `APPROVAL requested: livewell_activities.register_interest(...) -> APPROVED` before the registration, and the PASS line "approval requested before register_interest";
- `memories: ['User prefers mornings.', ... 'User dislikes swimming.' ...]`, then a recall answer with morning, indoor options and no swimming;
- `livewell-nutrition` and `livewell-activity` in the `tools:` list of the specialists answer: one merged plan built from both specialists.

![lab3_tools.py output: session resident, forbidden lookup for another resident, profile-tailored answer, approval before register_interest, memory recall and specialists, each with PASS lines](screenshots/lab-03/builder-output.png)

</details>

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
