# Lab 4 · Multi-agent & Hosted deploy — portal walkthrough

Main page: [Lab 4](lab-04.md) · [Portal track](PORTAL-TRACK.md)

This is a watch-along for the facilitator demo. Foundry User participants observe the hosted agent, versions, traces, and RBAC boundaries; deployment and production publishing require Foundry Project Manager.

How the three agents are wired (diagrams, code pointers and the DevUI view of each run): [Lab 4 · Under the hood](lab-04.md#under-the-hood).

1. Find the hosted workshop agent in the agent list.

   **Build → Agents → Search `livewell-workshop-hosted`**

   ![Agents list filtered to livewell-workshop-hosted](screenshots/lab-04/01-find-hosted-agent.png)

2. Open the hosted agent details.

   **Agents → `livewell-workshop-hosted` → Overview / Playground**

   ![Hosted agent page opened in the Foundry portal](screenshots/lab-04/02-open-hosted-agent.png)

3. Open the version history.

   **Version dropdown (top right) → Show all version history**

   ![Version history for livewell-workshop-hosted](screenshots/lab-04/03-hosted-agent-versions.png)

4. Inspect the active version without changing traffic.

   **Details tab → Active version** (leave **Edit** alone)

   ![Active hosted-agent version details](screenshots/lab-04/04-active-version-details.png)

5. Watch the facilitator smoke-test the hosted agent with a grounded food prompt. (The week-plan hand-off prompt from [Lab 4](lab-04.md) step 3 runs in DevUI, not here.)

   **Playground → New chat → Message box → Send**

   ![Hosted agent responding with JSON and a citation](screenshots/lab-04/05-hosted-agent-food-prompt.png)

   Prompt `lab1_prediabetes_eat`:

   ```text
   My screening says my glucose is high. What should I eat to manage pre-diabetes?
   ```

6. Open the hosted-agent trace.

   **Response metrics → Traces → Conversation → Response**

   ![Trace for the hosted-agent response](screenshots/lab-04/06-hosted-agent-trace.png)

7. Look at the disabled deployment or publishing controls from a Foundry User account.

   **Agent page → Deploy / Publish**

   > 📸 **Screenshot slot** · `screenshots/lab-04/07-disabled-deploy-publish.png` · Deploy or Publish controls disabled for Foundry User

8. Confirm why the buttons are disabled.

   **Project settings → Access control → My role**

   > 📸 **Screenshot slot** · `screenshots/lab-04/08-foundry-user-role.png` · Current participant role showing Foundry User, not Foundry Project Manager

9. Watch the facilitator show the Project Manager path.

   **Project Manager account → Agent page → Deploy / Publish**

   ![Facilitator view with deployment and publishing controls available](screenshots/lab-04/09-project-manager-publish-path.png)

## What you should see

`livewell-workshop-hosted` appears beside the prompt agents, has version history, responds in the playground, and produces traces like the prompt agents. Foundry User participants can observe and test but cannot deploy or publish; those buttons require Foundry Project Manager.

## If something looks different

- ⚠️ If the hosted agent is not visible, the facilitator may still be deploying it or filtering by a different protected name.
- ⚠️ If Deploy and Publish labels have changed, capture the disabled production action and the role message shown by the portal.
- If traces are unavailable, the facilitator should show a pre-captured trace from the demo kit.
- If you have Project Manager unexpectedly, do not publish; stay in watch-along mode.

