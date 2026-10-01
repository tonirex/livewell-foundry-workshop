#!/usr/bin/env python3
"""Record a script run as evidence: a replayable .cast, a screenshot of the whole output and a video.

    python demos/record-terminal.py builder-lab1 -- python scripts/validate-builder-rail.py --labs 1 --verbose
    python demos/record-terminal.py router-picks --title "Lab 0 · router picks" -- python demos/router-picks.py
    python demos/record-terminal.py --render demos/evidence/2026-10-01/router-picks.cast   # redo png and video

The command runs for real: its output is echoed live and its exit code is returned. The output is recorded
with its timings as an asciinema v2 file (`asciinema play x.cast` also works), then replayed in a
terminal-style page. In the video, waits longer than --idle seconds are shortened; the clock always shows the
real elapsed time. Output:

  demos/evidence/<date>/<name>.cast          recorded output with real timings (commit it)
  demos/evidence/<date>/<name>.png           the whole output as one image (commit it)
  demos/evidence/<date>/README.md            index of that day's recordings (rewritten on every run)
  demos/videos/evidence-<date>-<name>.webm   replay video (git-ignored, like the other videos)
  demos/videos/evidence-<date>-<name>.mp4    the same as H.264 for PowerPoint, Teams and QuickTime (needs ffmpeg)

IDs, endpoints and e-mails are rewritten with the same rules as the portal captures (portal.redaction_rules), and
local paths are shown relative to the repo (the home folder as ~).
Needs Playwright with Edge (as capture-screenshots.py); --no-video skips the videos.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import portal as P  # noqa: E402  (loads the azd env, which the redaction rules need)

ROOT = P.ROOT
EVIDENCE = ROOT / "demos" / "evidence"
VIDEOS = ROOT / "demos" / "videos"
RUNS = ROOT / "demos" / "runs"
VIEW = {"width": 1280, "height": 720}
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07")
MIN_GAP = 0.03  # seconds per line in the video, so bursts still scroll visibly


def path_rules() -> list[tuple[re.Pattern, str]]:
    """Repo paths become relative and the home folder becomes ~, so no user name lands in a committed file."""
    rules = []
    for path, rep in ((ROOT, "."), (pathlib.Path.home(), "~")):
        for s in dict.fromkeys((str(path), path.as_posix())):
            if rep == ".":
                rules.append((re.compile(re.escape(s) + r"[\\/](?=\S)", re.I), ""))
            rules.append((re.compile(re.escape(s), re.I), rep))
    return rules


def redactor():
    rules = path_rules() + [(re.compile(rx, re.I if "i" in flags else 0), re.sub(r"\$(\d)", r"\\\1", rep))
                            for rx, flags, rep in P.redaction_rules()]

    def apply(text: str) -> str:
        for rx, rep in rules:
            text = rx.sub(rep, text)
        return text
    return apply


def git_commit() -> str:
    def git(*a):
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    sha = git("rev-parse", "--short", "HEAD") or "unknown"
    return sha + (" + uncommitted changes" if git("status", "--porcelain", "--untracked-files=no") else "")


def record(name: str, title: str, cmd: list[str]) -> tuple[pathlib.Path, int]:
    shown = " ".join(cmd)
    exe = list(cmd)
    if exe[0] in ("python", "python3", "py"):
        exe[0:1] = [sys.executable, "-u"]
    redact = redactor()
    env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
    started = dt.datetime.now().astimezone()
    events = [[0.0, f"PS livewell-foundry-workshop> {shown}"]]
    print(events[0][1], flush=True)
    t0 = time.monotonic()
    proc = subprocess.Popen(exe, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        text = ANSI.sub("", line.rstrip("\n"))
        text = text[text.rfind("\r") + 1:] if "\r" in text else text
        events.append([round(time.monotonic() - t0, 3), redact(text)])
    code = proc.wait()
    seconds = time.monotonic() - t0
    out = EVIDENCE / f"{started:%Y-%m-%d}" / f"{name}.cast"
    out.parent.mkdir(parents=True, exist_ok=True)
    header = {"version": 2, "width": 120, "height": 36, "timestamp": int(started.timestamp()), "title": title,
              "env": {"TERM": "xterm-256color", "SHELL": "pwsh"},
              "livewell": {"command": shown, "exit": code, "seconds": round(seconds, 1),
                           "recorded": started.isoformat(timespec="seconds"),
                           "azd_env": os.environ.get("AZURE_ENV_NAME", ""), "commit": git_commit()}}
    rows = [json.dumps(header, ensure_ascii=False)]
    rows += [json.dumps([t, "o", text + "\r\n"], ensure_ascii=False) for t, text in events]
    out.write_bytes(("\n".join(rows) + "\n").encode("utf-8"))
    print(f"[record] exit {code} · {seconds:.0f} s · {out.relative_to(ROOT)}", flush=True)
    return out, code


def reredact(cast: pathlib.Path) -> None:
    """Apply the current redaction rules to a saved cast (for recordings made before a rule was added)."""
    redact = redactor()
    lines = cast.read_text(encoding="utf-8").splitlines()
    rows = lines[:1]
    for line in lines[1:]:
        t, kind, text = json.loads(line)
        rows.append(json.dumps([t, kind, "\r\n".join(redact(x) for x in text.split("\r\n"))], ensure_ascii=False))
    if rows != lines:
        cast.write_bytes(("\n".join(rows) + "\n").encode("utf-8"))
        print(f"[record] re-redacted {cast.relative_to(ROOT)}", flush=True)


def load(cast: pathlib.Path) -> dict:
    lines = cast.read_text(encoding="utf-8").splitlines()
    header = json.loads(lines[0])
    meta = header.get("livewell", {})
    events = [[e[0], e[2].replace("\r\n", "\n").rstrip("\n")] for e in map(json.loads, lines[1:]) if e[1] == "o"]
    return {"title": header.get("title") or cast.stem, "events": events, "exit": meta.get("exit", 0),
            "seconds": meta.get("seconds", events[-1][0] if events else 0), "command": meta.get("command", ""),
            "recorded": meta.get("recorded", ""), "env": meta.get("azd_env", ""), "commit": meta.get("commit", "")}


PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>__TITLE__</title><style>
body{margin:0;background:#0c0c0c;color:#d4d4d4;font:15px/1.45 "Cascadia Mono","Cascadia Code",Consolas,monospace}
header{position:sticky;top:0;z-index:2;background:#1f1f1f;border-bottom:1px solid #333;padding:10px 16px;
  font-family:"Segoe UI",sans-serif}
h1{margin:0;font-size:18px;color:#fff;font-weight:600}
.meta{font-size:13px;color:#9da5b4;margin-top:3px}
.clock{float:right;text-align:right;font:600 18px "Cascadia Mono",Consolas,monospace;color:#4fc1ff}
.clock small{display:block;font:12px "Segoe UI",sans-serif;color:#9da5b4}
#term{padding:12px 16px;white-space:pre-wrap;word-break:break-word}
#term div{min-height:1.45em}
.replay #term{height:calc(100vh - 94px);overflow:hidden;box-sizing:border-box}
.p{color:#d7ba7d}.ok{color:#4ec9b0}.bad{color:#f48771}.warn{color:#dcdcaa}.info{color:#4fc1ff}
#banner{display:none;margin:4px 16px 16px;padding:8px 14px;border-radius:4px;font:600 15px "Segoe UI",sans-serif}
.replay #banner{position:fixed;right:16px;bottom:12px;margin:0}
#banner.ok{display:inline-block;background:#0e3b2e;color:#4ec9b0}
#banner.bad{display:inline-block;background:#4b1d1d;color:#f48771}
</style></head><body>
<header><div class="clock"><span id="clock">00:00</span><small id="clocknote">real elapsed time</small></div>
<h1 id="title"></h1><div class="meta" id="cmd"></div><div class="meta" id="meta"></div></header>
<div id="term"></div><div id="banner"></div>
<script>
const D = __DATA__;
const RULES = [[/^PS .*?> /, 'p'], [/^\\s*\\[PASS/, 'ok'], [/^\\s*\\[CHECK\\]/, 'bad'],
  [/Traceback|\\bError\\b|\\bFAIL(ED)?\\b|\\u274c|\\bexit [1-9]/, 'bad'],
  [/\\bPASS\\b|\\u2705|\\bOK\\b|\\bpassed\\b/, 'ok'], [/\\bSKIP\\b|\\b429\\b|throttl|WARN|\\u26a0/, 'warn'],
  [/^\\s*\\[(validate|record)\\]|^#+ |^\\s*\\||^={3,}|^-{3,}/, 'info']];
const cls = t => (RULES.find(([rx]) => rx.test(t)) || [0, ''])[1];
const mmss = s => { s = Math.floor(s); return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0'); };
const long = s => s < 90 ? Math.round(s) + ' s' : Math.floor(s / 60) + ' min ' + Math.round(s % 60) + ' s';
const $ = id => document.getElementById(id);
const isStatic = location.hash === '#static';
document.body.className = isStatic ? 'static' : 'replay';
$('title').textContent = D.title;
$('cmd').textContent = D.command;
$('meta').textContent = 'Recorded ' + D.recorded.replace('T', ' ') + ' · azd env ' + (D.env || '-') + ' · commit ' +
  D.commit + (isStatic ? '' : ' · waits over ' + D.idle + ' s are shortened in this replay');
function add(ev) {
  const d = document.createElement('div');
  d.textContent = ev[1]; d.className = cls(ev[1]);
  $('term').appendChild(d); $('term').scrollTop = $('term').scrollHeight; $('clock').textContent = mmss(ev[0]);
}
function finish() {
  const b = $('banner');
  b.className = D.exit === 0 ? 'ok' : 'bad';
  b.textContent = (D.exit === 0 ? '\\u2714 ' : '\\u2718 ') + 'exit ' + D.exit + ' \\u00b7 ' + long(D.seconds) + ' real time';
  $('clock').textContent = mmss(D.seconds); $('clocknote').textContent = isStatic ? 'total real time' : 'real elapsed time';
  $('term').scrollTop = $('term').scrollHeight; document.body.dataset.done = '1';
}
if (isStatic) { D.events.forEach(add); finish(); }
else {
  let i = 0, prev = 0;
  const step = () => {
    if (i >= D.events.length) { setTimeout(finish, 600); return; }
    const ev = D.events[i];
    const gap = Math.max(Math.min(Math.max(ev[0] - prev, 0), D.idle) / D.speed, D.minGap);
    prev = ev[0];
    setTimeout(() => { add(ev); i++; step(); }, gap * 1000);
  };
  setTimeout(step, 1500);
}
</script></body></html>
"""


def render(cast: pathlib.Path, idle: float, speed: float, video: bool) -> None:
    from playwright.sync_api import sync_playwright

    data = load(cast)
    data.update(idle=idle, speed=speed, minGap=MIN_GAP)
    RUNS.mkdir(parents=True, exist_ok=True)
    page_file = RUNS / f"evidence-{cast.parent.name}-{cast.stem}.html"
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page_file.write_bytes(PAGE.replace("__TITLE__", data["title"].replace("<", "&lt;"))
                          .replace("__DATA__", payload).encode("utf-8"))
    png = cast.with_suffix(".png")
    replay = 1.5 + 0.6 + sum(max(min(max(b[0] - a[0], 0), idle) / speed, MIN_GAP)
                             for a, b in zip([[0, ""]] + data["events"], data["events"]))
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport=VIEW)
        page.goto(page_file.as_uri() + "#static")
        page.wait_for_selector("body[data-done]")
        page.screenshot(path=str(png), full_page=True)
        page.close()
        print(f"[record] screenshot {png.relative_to(ROOT)}", flush=True)
        if video:
            tmp = RUNS / "video-tmp"
            ctx = browser.new_context(viewport=VIEW, record_video_dir=str(tmp), record_video_size=VIEW)
            page = ctx.new_page()
            page.goto(page_file.as_uri())
            page.wait_for_selector("body[data-done]", timeout=(replay * 1.5 + 60) * 1000)
            time.sleep(2.5)
            raw = pathlib.Path(page.video.path())
            ctx.close()
            VIDEOS.mkdir(parents=True, exist_ok=True)
            dest = VIDEOS / f"evidence-{cast.parent.name}-{cast.stem}.webm"
            shutil.move(str(raw), dest)
            shutil.rmtree(tmp, ignore_errors=True)
            print(f"[record] video {dest.relative_to(ROOT)} (~{replay:.0f} s)", flush=True)
            mp4 = to_mp4(dest)
            if mp4:
                print(f"[record] video {mp4.relative_to(ROOT)}", flush=True)
        browser.close()
    index(cast.parent)


def to_mp4(webm: pathlib.Path) -> pathlib.Path | None:
    """H.264 copy of a replay video for PowerPoint, Teams and QuickTime, which do not play WebM. Needs ffmpeg."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("[record] ffmpeg not on PATH: no .mp4 (winget install Gyan.FFmpeg, or brew install ffmpeg)", flush=True)
        return None
    dest = webm.with_suffix(".mp4")
    subprocess.run([ffmpeg, "-y", "-v", "error", "-i", str(webm), "-vf", "fps=25", "-c:v", "libx264", "-crf", "18",
                    "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(dest)], check=True)
    return dest


def index(folder: pathlib.Path) -> None:
    rows = []
    for cast in sorted(folder.glob("*.cast")):
        d = load(cast)
        secs = d["seconds"]
        took = f"{secs:.0f} s" if secs < 90 else f"{secs // 60:.0f} min {secs % 60:.0f} s"
        shot = f"[{cast.stem}.png]({cast.stem}.png)" if cast.with_suffix(".png").exists() else "-"
        rows.append(f"| {d['title']} | `{d['command']}` | {d['exit']} | {took} | {shot} |")
    text = "\n".join([
        f"# Script evidence - {folder.name}", "",
        "Each row is a real run, recorded with `demos/record-terminal.py` against the azd env shown in the "
        "screenshot header. Exit 0 means every check in that script passed.", "",
        "| Recording | Command | Exit | Real time | Screenshot |", "|---|---|---:|---:|---|", *rows, "",
        f"Videos (git-ignored, on the machine that recorded them): `demos/videos/evidence-{folder.name}-<name>.mp4` "
        "(plays in PowerPoint, Teams and any player) and the same as `.webm`. Waits over 2 s are shortened; the "
        "clock shows real elapsed time. To rebuild the screenshot and both videos from a recording: "
        "`python demos/record-terminal.py --render <name>.cast` (or `asciinema play <name>.cast` on macOS/Linux).",
        ""])
    (folder / "README.md").write_bytes(text.encode("utf-8"))


def main() -> int:
    argv = sys.argv[1:]
    cmd = argv[argv.index("--") + 1:] if "--" in argv else []
    argv = argv[:argv.index("--")] if "--" in argv else argv
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 usage="record-terminal.py NAME [--title T] [options] -- COMMAND ... | --render CAST")
    ap.add_argument("name", nargs="?", help="file name for the recording (letters, digits, dashes)")
    ap.add_argument("--title", help="heading shown above the output (default: NAME)")
    ap.add_argument("--render", metavar="CAST",
                    help="re-render the screenshot and video of a saved .cast (re-applies the redaction first)")
    ap.add_argument("--idle", type=float, default=2.0, help="longest wait kept in the video, seconds (default 2)")
    ap.add_argument("--speed", type=float, default=1.0, help="video playback speed (default 1)")
    ap.add_argument("--no-video", action="store_true", help="screenshot only")
    args = ap.parse_args(argv)
    if args.render:
        cast = pathlib.Path(args.render).resolve()
        reredact(cast)
        render(cast, args.idle, args.speed, not args.no_video)
        return 0
    if not args.name or not cmd:
        ap.error("give a NAME and the command after --")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", args.name):
        ap.error("NAME: letters, digits and dashes only")
    cast, code = record(args.name, args.title or args.name, cmd)
    try:
        render(cast, args.idle, args.speed, not args.no_video)
    except Exception as e:  # the run itself is the evidence; a rendering problem must not hide its exit code
        print(f"[record] rendering failed: {e}; retry with --render {cast.relative_to(ROOT)}", flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
