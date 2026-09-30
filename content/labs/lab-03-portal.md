# Lab 3 · Tools, MCP & Memory — hyper-personalisation — portal walkthrough

Main page: [Lab 3](lab-03.md) · [Portal track](PORTAL-TRACK.md)

You will add a profile OpenAPI tool, an activities MCP tool with approval before registration, memory, and optionally the Fabric IQ tool for programme-level questions.

1. Open your guarded agent.

   **Build → Agents → `livewell-<initials>` → Configure**

   > 📸 **Screenshot slot** · `screenshots/lab-03/01-open-guarded-agent.png` · Agent configuration page after Lab 2

2. Start adding the profile OpenAPI tool.

   **Tools → Add → Browse all tools → Custom → OpenAPI**

   > 📸 **Screenshot slot** · `screenshots/lab-03/02-add-openapi-tool.png` · Tool catalog showing Custom OpenAPI

3. Create the `livewell-profile` tool from the spec URL shown on the facilitator values sheet.

   **OpenAPI → Name `livewell-profile` → Import from URL → Add**

   > 📸 **Screenshot slot** · `screenshots/lab-03/03-livewell-profile-spec.png` · OpenAPI form with livewell-profile named and imported

4. Start adding the activities MCP tool.

   **Tools → Add → Browse all tools → Custom → MCP tool**

   > 📸 **Screenshot slot** · `screenshots/lab-03/04-add-mcp-tool.png` · Tool catalog showing Custom MCP tool

5. Select the existing workshop MCP connection.

   **MCP tool → Existing connection → `livewell-activities-mcp` → Connect**

   > 📸 **Screenshot slot** · `screenshots/lab-03/05-select-activities-mcp.png` · MCP connection livewell-activities-mcp selected

6. Require approval for the write action.

   **MCP tool row → Configure → Approval setting → require approval for `register_interest` → Apply**

   > 📸 **Screenshot slot** · `screenshots/lab-03/06-register-interest-approval.png` · register_interest configured to require approval

7. Enable memory for the agent and switch it to the memory model.

   **Memory (Preview) → Enable memory → Create / select memory store → Save**, then **Model → `gpt-5.4-mini` → Save**

   Memory is not searched when the agent runs on `model-router`, so the Lab 3 coach runs on `gpt-5.4-mini`.

   > 📸 **Screenshot slot** · `screenshots/lab-03/07-enable-memory-preview.png` · Memory preview enabled for the agent, model gpt-5.4-mini

8. Append the `tools` instruction block from [coach-instructions.md](../prompts/coach-instructions.md) and switch to the evidence schema.

   **Instructions → paste after `safety` block**, then **Response format → JSON schema → replace with all of [`lab3-evidence.schema.json`](../config/schemas/lab3-evidence.schema.json) → Save**

   > 📸 **Screenshot slot** · `screenshots/lab-03/08-tools-instructions.png` · Instructions with tools block appended and livewell_evidence schema set

9. Save a tools-and-memory version.

   **Versions → Save / Create version → Name `v3-tools-memory` → Save**

   > 📸 **Screenshot slot** · `screenshots/lab-03/09-save-v3-tools-memory.png` · Version list showing v3 tools and memory version

10. Ask for tailored advice from the profile.

    **Chat → New chat → Message box → Send**

    > 📸 **Screenshot slot** · `screenshots/lab-03/10-profile-tailored-answer.png` · Answer tailored to profile, low steps, and elevated glucose

    Prompt `lab3_profile_tailored`:

    ```text
    Based on my profile, what is one change I should make this week?
    ```

11. Confirm the profile and knowledge tools in the trace.

    **Response metrics → Traces → tool calls → `get_citizen_profile` and knowledge span**

    > 📸 **Screenshot slot** · `screenshots/lab-03/11-profile-trace.png` · Trace showing profile and knowledge tool calls

12. Ask for an indoor Woodlands activity and registration.

    **Chat → Message box → Send**

    > 📸 **Screenshot slot** · `screenshots/lab-03/12-hazy-indoor-signup.png` · Activity recommendation with registration approval pending

    Prompt `lab3_hazy_indoor_signup`:

    ```text
    It's hazy today. What can I do indoors near Woodlands, and can you sign me up?
    ```

13. Approve the registration card once.

    **Approval card → Approve once**

    > 📸 **Screenshot slot** · `screenshots/lab-03/13-approve-register-interest.png` · MCP approval card for register_interest approved once

14. Store a preference in memory.

    **Chat → Message box → Send**

    > 📸 **Screenshot slot** · `screenshots/lab-03/14-memory-set.png` · Agent acknowledges morning preference and swimming dislike

    Prompt `lab3_memory_set`:

    ```text
    By the way, I prefer mornings, and I don't like swimming.
    ```

15. Start a new chat and test memory recall.

    **Chat → New chat → Message box → Send**

    > 📸 **Screenshot slot** · `screenshots/lab-03/15-memory-recall-new-chat.png` · New chat respects morning preference and avoids swimming

    Prompt `lab3_memory_recall`:

    ```text
    Any activities you would suggest for me next week?
    ```

16. Optional Fabric step: add the published Fabric IQ data agent from the OneLake Catalog.

    **Tools → Add → Fabric IQ → OneLake Catalog → Resident360 Ontology Agent**

    > 📸 **Screenshot slot** · `screenshots/lab-03/16-fabric-iq-onelake-catalog.png` · Fabric IQ picker with Resident360 Ontology Agent selected

17. If the connection already exists, attach it instead of browsing the catalog.

    **Tools → Add → Fabric IQ → Existing connection → `livewell-fabric-resident360`**

    > 📸 **Screenshot slot** · `screenshots/lab-03/17-existing-fabric-connection.png` · Existing Fabric IQ connection livewell-fabric-resident360 selected

18. Append the `fabric` instruction block when Fabric IQ is attached.

    **Instructions → paste `fabric` block after `tools` block → Save**

    > 📸 **Screenshot slot** · `screenshots/lab-03/18-fabric-instructions.png` · Fabric routing rules appended to instructions

19. Ask the programme-level Fabric question.

    **Chat → New chat → Message box → Send**

    > 📸 **Screenshot slot** · `screenshots/lab-03/19-fabric-disengaged-regions.png` · Aggregated region answer with no resident_id

    Prompt `fabric_q_disengaged_regions`:

    ```text
    Which regions have the highest share of disengaged residents?
    ```

20. Confirm the Fabric IQ call in the trace.

    **Response metrics → Traces → Fabric IQ / MCP call**

    > 📸 **Screenshot slot** · `screenshots/lab-03/20-fabric-iq-trace.png` · Trace showing Fabric IQ call for the officer question

21. Confirm a citizen knowledge question does not call Fabric.

    **Chat → New chat → Message box → Send**

    > 📸 **Screenshot slot** · `screenshots/lab-03/21-no-fabric-for-citizen-question.png` · Trace for food question showing knowledge/profile but no Fabric IQ call

    Prompt `lab1_prediabetes_eat`:

    ```text
    My screening says my glucose is high. What should I eat to manage pre-diabetes?
    ```

## What you should see

Profile advice is tailored to the signed-in synthetic resident and cites guides. Activity registration pauses on an approval card before `register_interest` runs. Memory affects a new chat. In the optional Fabric step, the officer aggregate question calls Fabric IQ, while the citizen food question stays on Foundry IQ and profile tools.

## If something looks different

- ⚠️ OpenAPI import labels and spec URL entry points vary; use the facilitator values sheet and keep the tool name `livewell-profile`.
- ⚠️ Memory is preview and may appear under a different panel; if it is unavailable, complete the tool steps and watch the facilitator memory demo.
- ⚠️ Fabric IQ is preview; if OneLake Catalog browsing is unavailable, use `livewell-fabric-resident360` or the facilitator's prepared agent.
- If registration runs without approval, stop using that chat and reconfigure approval for `register_interest`.

