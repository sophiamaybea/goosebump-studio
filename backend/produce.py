#!/usr/bin/env python3
"""Measure a mix and render counterfactual producer variants.

Never overwrites the source. Original stays A. Renders are experiments.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=True, text=True, capture_output=True)


def ffprobe(path: Path) -> dict:
    proc = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,bit_rate:stream=codec_type,sample_rate,channels,codec_name",
        "-of", "json", str(path),
    ])
    return json.loads(proc.stdout)


def measure(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"missing file: {path}")
    probe = ffprobe(path)
    loud = run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128=framelog=verbose", "-f", "null", "-"])
    integrated = lra = true_peak = None
    for line in loud.stderr.splitlines():
        if "I:" in line and "LUFS" in line and integrated is None:
            integrated = line.strip()
        if "LRA:" in line and lra is None:
            lra = line.strip()
        if "Peak:" in line and "dBFS" in line:
            true_peak = line.strip()
    vol = run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"])
    volume_lines = [
        ln.strip() for ln in vol.stderr.splitlines()
        if "max_volume" in ln or "mean_volume" in ln
    ]
    return {
        "path": str(path),
        "sha256": sha256(path),
        "probe": probe,
        "loudness_lines": [integrated, lra, true_peak],
        "volume_lines": volume_lines[:8],
        "note": "Physics snapshot only. Not a nervous-system measurement.",
    }


VARIANTS = {
    "B_density_down": "volume=-3dB",
    "C_bass_cut": "highpass=f=120",
    "D_vocal_closer_proxy": "equalizer=f=3000:t=q:w=1:g=1.5,volume=1dB",
    "F_narrower": "extrastereo=m=0.6",
    "G_pre_drop_proxy": "highpass=f=90,volume=-2dB,extrastereo=m=0.75",
}


def render(path: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    src_hash = sha256(path)
    note = out_dir / "A_ORIGINAL_DO_NOT_OVERWRITE.txt"
    note.write_text(
        f"source={path}\nsha256={src_hash}\n"
        "A is the original file. These renders are counterfactuals.\n"
        "E_resolution_delay is omitted because a stereo file cannot delay harmony.\n"
    )
    made = []
    for name, filt in VARIANTS.items():
        dest = out_dir / f"{name}.wav"
        run(["ffmpeg", "-y", "-hide_banner", "-i", str(path), "-af", filt, "-c:a", "pcm_s16le", str(dest)])
        made.append({"name": name, "filter": filt, "path": str(dest), "sha256": sha256(dest)})
    return {"source_sha256": src_hash, "renders": made, "guard": str(note)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Goosebump producer physics and counterfactuals")
    sub = parser.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure")
    m.add_argument("audio")
    r = sub.add_parser("render")
    r.add_argument("audio")
    r.add_argument("--out", required=True)
    args = parser.parse_args()
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is required")
    path = Path(args.audio)
    if args.cmd == "measure":
        json.dump(measure(path), sys.stdout, indent=2)
    else:
        json.dump(render(path, Path(args.out)), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
