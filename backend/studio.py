#!/usr/bin/env python3
"""Goosebump studio. Original is locked. Every edit is a new take.

Grok is the editor brain. This script is the hands.
It applies only an allowlisted plan. It never calls an external model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


ALLOWLIST = {
    "gain_db",
    "highpass_hz",
    "lowpass_hz",
    "eq_hz",
    "eq_gain_db",
    "width",
    "compress",
    "trim_start",
    "trim_end",
    "fade_in",
    "fade_out",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def init_session(audio: Path, root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    if not audio.is_file():
        raise SystemExit(f"missing audio: {audio}")
    digest = sha256(audio)
    locked = root / "A_original" / audio.name
    locked.parent.mkdir(parents=True, exist_ok=True)
    if not locked.exists():
        shutil.copy2(audio, locked)
        locked.chmod(0o444)
    meta = {
        "source": str(audio),
        "locked": str(locked),
        "sha256": digest,
        "rule": "Never overwrite A_original. Grok plans. Studio renders. Human marks.",
    }
    (root / "session.json").write_text(json.dumps(meta, indent=2))
    (root / "takes").mkdir(exist_ok=True)
    (root / "plans").mkdir(exist_ok=True)
    return meta


def filters_from_plan(plan: dict, duration: float) -> str:
    unknown = [k for k in plan if k not in ALLOWLIST and k not in {"name", "hypothesis", "predicted_proxy"}]
    if unknown:
        raise SystemExit(f"refused unknown plan keys: {unknown}")
    parts: list[str] = []
    if plan.get("highpass_hz"):
        parts.append(f"highpass=f={float(plan['highpass_hz'])}")
    if plan.get("lowpass_hz"):
        parts.append(f"lowpass=f={float(plan['lowpass_hz'])}")
    if plan.get("eq_hz") is not None and plan.get("eq_gain_db") is not None:
        parts.append(f"equalizer=f={float(plan['eq_hz'])}:t=q:w=1:g={float(plan['eq_gain_db'])}")
    if plan.get("compress"):
        parts.append("acompressor=threshold=-18dB:ratio=3:attack=8:release=80")
    if plan.get("width") is not None:
        parts.append(f"extrastereo=m={float(plan['width'])}")
    if plan.get("gain_db") is not None:
        parts.append(f"volume={float(plan['gain_db'])}dB")
    fade_in = float(plan.get("fade_in") or 0)
    fade_out = float(plan.get("fade_out") or 0)
    if fade_in > 0:
        parts.append(f"afade=t=in:st=0:d={fade_in}")
    if fade_out > 0 and duration > fade_out:
        parts.append(f"afade=t=out:st={max(0.0, duration - fade_out)}:d={fade_out}")
    return ",".join(parts) if parts else "anull"


def duration_of(path: Path) -> float:
    proc = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)])
    return float(json.loads(proc.stdout)["format"]["duration"])


def apply_plan(root: Path, plan: dict) -> dict:
    meta = json.loads((root / "session.json").read_text())
    src = Path(meta["locked"])
    takes = sorted((root / "takes").glob("take-*.wav"))
    n = len(takes) + 1
    dest = root / "takes" / f"take-{n:03d}.wav"
    dur = duration_of(src)
    start = float(plan.get("trim_start") or 0)
    end = plan.get("trim_end")
    filt = filters_from_plan(plan, dur)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-ss", str(start), "-i", str(src)]
    if end is not None:
        cmd += ["-to", str(float(end))]
    cmd += ["-af", filt, "-c:a", "pcm_s16le", str(dest)]
    run(cmd)
    receipt = {
        "take": str(dest),
        "sha256": sha256(dest),
        "source_sha256": meta["sha256"],
        "plan": plan,
        "ffmpeg_filter": filt,
        "hypothesis": plan.get("hypothesis", ""),
        "predicted_proxy": plan.get("predicted_proxy", ""),
        "human_mark": None,
    }
    (root / "plans" / f"take-{n:03d}.json").write_text(json.dumps(receipt, indent=2))
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Goosebump studio hands")
    sub = parser.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("audio")
    i.add_argument("--session", required=True)
    a = sub.add_parser("apply")
    a.add_argument("--session", required=True)
    a.add_argument("--plan", required=True)
    args = parser.parse_args()
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is required")
    if args.cmd == "init":
        json.dump(init_session(Path(args.audio), Path(args.session)), sys.stdout, indent=2)
    else:
        plan = json.loads(Path(args.plan).read_text())
        json.dump(apply_plan(Path(args.session), plan), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
