# Script evidence - 2026-10-03

Each row is a real run, recorded with `demos/record-terminal.py` against the azd env shown in the screenshot header. Exit 0 means every check in that script passed.

| Recording | Command | Exit | Real time | Screenshot |
|---|---|---:|---:|---|
| Lab 1 · Builder: knowledge-grounded coach (lab1_knowledge.py) | `.venv\Scripts\python.exe content/assets/lab1_knowledge.py` | 0 | 47 s | [lab1-builder-output.png](lab1-builder-output.png) |
| Lab 2 · Builder: red flags, guardrails and evaluation (lab2_govern.py) | `.venv\Scripts\python.exe content/assets/lab2_govern.py` | 0 | 3 min 50 s | [lab2-builder-output.png](lab2-builder-output.png) |
| Lab 3 · Builder: tools, approvals, memory + Fabric IQ step (lab3_tools.py --fabric) | `.venv\Scripts\python.exe content/assets/lab3_tools.py --fabric` | 0 | 6 min 40 s | [lab3-builder-output.png](lab3-builder-output.png) |
| Lab 4 · Builder: Agent Framework workflows + hosted agent (lab4_multiagent.py --fabric) | `.venv\Scripts\python.exe content/assets/lab4_multiagent.py --fabric` | 0 | 4 min 12 s | [lab4-builder-output.png](lab4-builder-output.png) |

Videos (git-ignored, on the machine that recorded them): `demos/videos/evidence-2026-10-03-<name>.mp4` (plays in PowerPoint, Teams and any player) and the same as `.webm`. Waits over 2 s are shortened; the clock shows real elapsed time. To rebuild the screenshot and both videos from a recording: `python demos/record-terminal.py --render <name>.cast` (or `asciinema play <name>.cast` on macOS/Linux).
