# Lab 0 · Setup & first agent — portal walkthrough

Main page: [Lab 0](lab-00.md) · [Portal track](PORTAL-TRACK.md)

Use a personal laptop, an InPrivate browser window, and the `hpb.labNN` account assigned by the facilitator. Your agent name is `livewell-<initials>`; never edit `livewell-demo-*` agents.

1. Open the portal in a private browser window and sign in with your `hpb.labNN` account.

   **InPrivate browser → `https://ai.azure.com` → Sign in**

   > 📸 **Screenshot slot** · `screenshots/lab-00/01-sign-in-inprivate.png` · InPrivate window at Foundry sign-in with the lab account prompt

2. Register Microsoft Authenticator if this is your first sign-in.

   **Sign-in prompt → Microsoft Authenticator → Add account → Approve sign-in**

   > 📸 **Screenshot slot** · `screenshots/lab-00/02-authenticator-registration.png` · Authenticator registration completed for the lab account

3. Open the shared Foundry project.

   **Home → Projects → `livewell-workshop` → Open**

   > 📸 **Screenshot slot** · `screenshots/lab-00/03-open-livewell-project.png` · Project picker with livewell-workshop selected

4. Take the quick portal tour without changing anything.

   **Build → Agents → Knowledge → Evaluations → Guardrails**

   > 📸 **Screenshot slot** · `screenshots/lab-00/04-portal-tour-build.png` · Build area showing Agents, Knowledge, Evaluations, and Guardrails

5. Start a new prompt agent.

   **Build → Agents → + New agent → Build an agent**

   > 📸 **Screenshot slot** · `screenshots/lab-00/05-new-agent-menu.png` · New agent menu with Build an agent selected

6. Name your agent and choose the workshop router model.

   **Create an agent → Agent name `livewell-<initials>` → Model `model-router` → Create**

   > 📸 **Screenshot slot** · `screenshots/lab-00/06-name-model-router.png` · Create dialog showing livewell initials name and model-router

7. Paste the `base` instruction block from [coach-instructions.md](../prompts/coach-instructions.md) and save.

   **Playground → Instructions → paste `base` block → Save**

   > 📸 **Screenshot slot** · `screenshots/lab-00/07-base-instructions-saved.png` · Instructions panel with the base block saved

8. Start a chat and send prompt `lab0_hi`.

   **Chat → New chat → Message box → Send**

   > 📸 **Screenshot slot** · `screenshots/lab-00/08-lab0-hi.png` · Chat response introducing LiveWell Coach and stating it is not a doctor

   Prompt `lab0_hi`:

   ```text
   Hi
   ```

9. Send prompt `lab0_am_i_diabetic` in the same chat.

   **Chat → Message box → Send**

   > 📸 **Screenshot slot** · `screenshots/lab-00/09-lab0-am-i-diabetic.png` · Refusal to diagnose with advice to speak to a doctor

   Prompt `lab0_am_i_diabetic`:

   ```text
   Am I diabetic?
   ```

10. Open the trace for the diagnosis refusal.

    **Response metrics → Traces → Conversation → Response**

    > 📸 **Screenshot slot** · `screenshots/lab-00/10-refusal-trace.png` · Trace view for the diagnosis refusal response

11. Send the router comparison prompt on `model-router`.

    **Configure → Model `model-router` → Save → Chat → New chat → Message box → Send**

    > 📸 **Screenshot slot** · `screenshots/lab-00/11-router-compare-model-router.png` · model-router answer to the walking routine prompt

    Prompt `lab0_router_compare`:

    ```text
    Plan a gentle 7-day walking routine for a 61-year-old who is just getting started, one line per day.
    ```

12. Read which model the router selected.

    **Response metrics → Traces → Response → Metadata → Model**

    > 📸 **Screenshot slot** · `screenshots/lab-00/12-router-chosen-model-trace.png` · Trace metadata showing the chosen model for model-router

13. Compare with the fallback model.

    **Configure → Model `gpt-4.1-mini` → Save → Chat → New chat → Message box → Send**

    > 📸 **Screenshot slot** · `screenshots/lab-00/13-compare-gpt-41-mini.png` · gpt-4.1-mini answer to the same walking routine prompt

14. Switch your agent back to `model-router` for the rest of the portal track.

    **Configure → Model `model-router` → Save**

    > 📸 **Screenshot slot** · `screenshots/lab-00/14-switch-back-model-router.png` · Agent configuration saved with model-router restored

## What you should see

Your `livewell-<initials>` agent greets warmly, says it is not a doctor, refuses to diagnose diabetes, and routes the user to a doctor. The router comparison produces two reasonable walking plans, and the trace for the `model-router` run shows the model selected for that request.

## If something looks different

- ⚠️ If the project picker or Build rail has moved, use the portal search box for `livewell-workshop` and `Agents`.
- If `model-router` is not selectable, use `gpt-4.1-mini` and tell the facilitator before Lab 1.
- If the response diagnoses you, re-paste the `base` block from [coach-instructions.md](../prompts/coach-instructions.md) and save.
- If trace metadata does not show the router choice, capture the trace screenshot anyway and note the missing field.

