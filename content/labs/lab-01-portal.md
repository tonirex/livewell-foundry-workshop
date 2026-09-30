# Lab 1 · Agents & Knowledge — Foundry IQ — portal walkthrough

Main page: [Lab 1](lab-01.md) · [Portal track](PORTAL-TRACK.md)

You will attach the shared Foundry IQ knowledge base, add the `knowledge` instruction block, force JSON output, and test citation discipline.

1. Open the agent you created in Lab 0.

   **Build → Agents → `livewell-<initials>` → Configure**

   > 📸 **Screenshot slot** · `screenshots/lab-01/01-open-agent-configure.png` · Agent configuration page for livewell initials agent

2. Start the Foundry IQ connection flow.

   **Knowledge → Add → Connect to Foundry IQ**

   > 📸 **Screenshot slot** · `screenshots/lab-01/02-knowledge-add-foundry-iq.png` · Knowledge Add menu with Connect to Foundry IQ selected

3. Select the shared workshop knowledge base.

   **Connect to Foundry IQ → `livewell-guides-kb` → Add**

   > 📸 **Screenshot slot** · `screenshots/lab-01/03-connect-foundry-iq.png` · Knowledge panel with livewell-guides-kb selected

4. Review the knowledge-base settings without changing names.

   **Build → Knowledge → Knowledge bases → `livewell-guides-kb` → Settings**

   > 📸 **Screenshot slot** · `screenshots/lab-01/04-kb-settings-preview.png` · Retrieval reasoning effort, output mode, and retrieval instructions visible

   ⚠️ Foundry IQ portal settings are preview. The facilitator expects retrieval reasoning effort, output mode, and retrieval instructions to be pre-set for the shared `livewell-guides-kb`.

5. Append the `knowledge` block from [coach-instructions.md](../prompts/coach-instructions.md).

   **Build → Agents → `livewell-<initials>` → Instructions → paste after `base` block → Save**

   > 📸 **Screenshot slot** · `screenshots/lab-01/05-knowledge-instructions.png` · Instructions with base plus knowledge blocks saved

6. Set the response format to the Lab 1 JSON schema.

   **Response format → JSON schema → paste all of [`lab1-answer.schema.json`](../config/schemas/lab1-answer.schema.json) → Save**

   Do not pick **JSON object**: it needs the word "json" in every chat message and otherwise returns a 400 error. The schema also limits `cited_sources` to the real guide ids.

   > 📸 **Screenshot slot** · `screenshots/lab-01/06-json-response-format.png` · Response format set to JSON schema with livewell_answer pasted

7. Ask the pre-diabetes food question.

   **Chat → New chat → Message box → Send**

   > 📸 **Screenshot slot** · `screenshots/lab-01/07-prediabetes-json-answer.png` · JSON answer with cited_sources populated

   Prompt `lab1_prediabetes_eat`:

   ```text
   My screening says my glucose is high. What should I eat to manage pre-diabetes?
   ```

8. Open the citation and confirm guide `lg-05-eating-for-pre-diabetes` appears when retrieved.

   **Answer → Citations / Sources → `lg-05-eating-for-pre-diabetes`**

   > 📸 **Screenshot slot** · `screenshots/lab-01/08-lg05-citation.png` · Citation panel showing lg-05 or another allowed LiveWell guide

9. Open the trace and find the Foundry IQ retrieval span.

   **Response metrics → Traces → Conversation → Foundry IQ / knowledge span**

   > 📸 **Screenshot slot** · `screenshots/lab-01/09-knowledge-trace.png` · Trace showing knowledge-base retrieval before the answer

10. Ask the supplement question in a new chat.

    **Chat → New chat → Message box → Send**

    > 📸 **Screenshot slot** · `screenshots/lab-01/10-supplement-no-source.png` · JSON answer routing to clinician with no cited source

    Prompt `lab1_supplement`:

    ```text
    Which supplement should I take to bring my blood sugar down?
    ```

11. Confirm the JSON route and empty citations.

    **Answer JSON → `route` → `cited_sources`**

    > 📸 **Screenshot slot** · `screenshots/lab-01/11-json-route-clinician.png` · route clinician and empty cited_sources for the supplement prompt

## What you should see

The food answer returns JSON with `route: "self_care"`, at least one LiveWell guide in `cited_sources`, and practical pre-diabetes advice. The supplement answer returns JSON with `route: "clinician"` and no invented source because the guides do not cover supplement dosing.

## If something looks different

- ⚠️ If **Knowledge → Add → Connect to Foundry IQ** has moved, search the Add menu for `Foundry IQ`.
- ⚠️ If the KB settings page does not expose retrieval reasoning effort or output mode, capture the available settings and continue.
- If answers include prose outside JSON, recheck **Response format → JSON object** and the `knowledge` block.
- If the food answer cites no source, confirm `livewell-guides-kb` is attached and Active.

