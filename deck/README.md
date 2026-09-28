# Slide deck generator

The PowerPoint file in this folder is generated; do not hand-edit the `.pptx`.
Edit `deck/build_deck.py` and rebuild instead.

Build from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install python-pptx pyyaml
.\.venv\Scripts\python.exe deck\build_deck.py
```

Optional output path:

```powershell
.\.venv\Scripts\python.exe deck\build_deck.py --out deck\LiveWell-Foundry-Workshop-Day1.pptx
```

Slides cover: title, agenda, logistics, Fabric-to-Foundry arc, human thread, architecture, Foundry features, six module cards, three Two IQs bridge slides, guardrail scorecard, cost controls, resources and close.

Workshop date, customer, Wi-Fi, lab durations, rails, resource names and model names are read from `content/config/workshop.yaml`.
Values set to `TODO` in that YAML render as `TODO — to be confirmed`.
