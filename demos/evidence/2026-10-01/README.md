# Script evidence - 2026-10-01

Each row is a real run, recorded with `demos/record-terminal.py` against the azd env shown in the screenshot header. Exit 0 means every check in that script passed.

| Recording | Command | Exit | Real time | Screenshot |
|---|---|---:|---:|---|
| Bridge · Fabric data agent steps (live run 17:25, replayed) | `.venv\Scripts\python.exe demos\fabric-steps.py --replay demos\samples\fabric-steps-q_dropped_attended_heldin.json` | 0 | 0 s | [bridge-fabric-steps.png](bridge-fabric-steps.png) |
| Builder Lab 1 · Knowledge (validate-builder-rail.py --labs 1) | `python scripts/validate-builder-rail.py --labs 1 --verbose` | 0 | 58 s | [builder-lab1.png](builder-lab1.png) |
| Builder rail · Lab 2: red flags, guardrails and evaluation (validate-builder-rail.py) | `python scripts/validate-builder-rail.py --labs 2 --verbose` | 0 | 2 min 55 s | [builder-lab2.png](builder-lab2.png) |
| Builder Lab 3 · Tools + Fabric IQ step (validate-builder-rail.py --labs 3) | `python scripts/validate-builder-rail.py --labs 3 --verbose` | 0 | 4 min 34 s | [builder-lab3.png](builder-lab3.png) |
| Builder Lab 4 · Multi-agent + Fabric (validate-builder-rail.py --labs 4) | `python scripts/validate-builder-rail.py --labs 4 --verbose` | 0 | 4 min 14 s | [builder-lab4.png](builder-lab4.png) |
| Lab 0 · router-picks.py: which model did model-router pick? | `python demos/router-picks.py` | 0 | 17 s | [lab0-router-picks.png](lab0-router-picks.png) |
| Lab 1 · Builder: knowledge-grounded coach (lab1_knowledge.py) | `python content/assets/lab1_knowledge.py` | 0 | 36 s | [lab1-builder-output.png](lab1-builder-output.png) |
| Lab 2 · Builder: red flags, guardrails and evaluation (lab2_govern.py) | `python content/assets/lab2_govern.py` | 0 | 2 min 3 s | [lab2-builder-output.png](lab2-builder-output.png) |
| Lab 3 · Builder: tools, approvals, memory + Fabric IQ step (lab3_tools.py --fabric) | `python content/assets/lab3_tools.py --fabric` | 0 | 6 min 41 s | [lab3-builder-output.png](lab3-builder-output.png) |
| Lab 4 · Builder: Agent Framework workflows + hosted agent (lab4_multiagent.py --fabric) | `python content/assets/lab4_multiagent.py --fabric` | 0 | 2 min 54 s | [lab4-builder-output.png](lab4-builder-output.png) |

Videos (git-ignored, on the machine that recorded them): `demos/videos/evidence-2026-10-01-<name>.mp4` (plays in PowerPoint, Teams and any player) and the same as `.webm`. Waits over 2 s are shortened; the clock shows real elapsed time. To rebuild the screenshot and both videos from a recording: `python demos/record-terminal.py --render <name>.cast` (or `asciinema play <name>.cast` on macOS/Linux).
