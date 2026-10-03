#!/usr/bin/env python3
"""Stage the Lab 4 DevUI build context: copy demos/lab4-devui.py and the files it reads into demos/devui-aca/app/.

Run by the azd prepackage hook of the `lab4-devui` service (azure.yaml). The copies keep the repo layout, so
livewell_common finds content/ exactly as it does on a laptop. demos/devui-aca/app/ is git-ignored.
Standard library only.
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "demos" / "devui-aca" / "app"
FILES = [
    "demos/lab4-devui.py",
    "content/assets/common/__init__.py",
    "content/assets/common/livewell_common.py",
    "content/config/workshop.yaml",
    "content/prompts/test-prompts.json",
    "content/prompts/coach-instructions.md",
    "content/data/citizens.json",
]


def main() -> int:
    if APP.exists():
        shutil.rmtree(APP)
    for rel in FILES:
        dst = APP / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dst)
    print(f"[stage-devui] {len(FILES)} files -> {APP.relative_to(ROOT).as_posix()}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
