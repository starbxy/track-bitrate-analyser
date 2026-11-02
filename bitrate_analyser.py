"""Bitrate analyser: runs ffprobe (and optionally ffmpeg spectrograms) over every track in a directory."""

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

AUDIO_EXTS = {".mp3", ".flac", ".wav", ".m4a", ".aac", ".ogg", ".opus", ".aiff", ".aif"}


def probe(path: Path) -> dict:
    """Return codec, bitrates, sample rate, channels and duration for one file."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "format=bit_rate,duration:stream=codec_name,bit_rate,sample_rate,channels",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")

    data = json.loads(result.stdout)
    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format", {})

    def kbps(value):
        return round(int(value) / 1000) if value not in (None, "N/A") else None

    return {
        "file": path.name,
        "codec": stream.get("codec_name"),
        "stream_kbps": kbps(stream.get("bit_rate")),
        "overall_kbps": kbps(
            fmt.get("bit_rate")
        ),  # includes artwork/tags, reads slightly high
        "sample_rate_hz": int(stream["sample_rate"])
        if stream.get("sample_rate")
        else None,
        "channels": stream.get("channels"),
        "duration_s": round(float(fmt["duration"]), 1) if fmt.get("duration") else None,
    }


def spectrogram(path: Path, out_dir: Path) -> Path:
    """Write a spectrogram PNG; check where the bright content stops on the frequency axis."""
    out = out_dir / f"{path.stem}.png"
    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(path),
        "-lavfi",
        "showspectrumpic=s=1024x512:legend=1",
        str(out),
    ]
    subprocess.run(cmd, check=True)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyse bitrate of all tracks in a directory."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default="tracks",
        help="folder of tracks (default: tracks)",
    )
    parser.add_argument(
        "-s",
        "--spectrograms",
        action="store_true",
        help="also generate spectrogram PNGs",
    )
    parser.add_argument(
        "-o", "--output", default="analysis", help="output folder (default: analysis)"
    )
    args = parser.parse_args()

    for tool in ("ffprobe", "ffmpeg"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found. Install with: brew install ffmpeg")

    src = Path(args.directory)
    if not src.is_dir():
        sys.exit(f"Directory not found: {src}")

    files = sorted(p for p in src.glob("*") if p.suffix.lower() in AUDIO_EXTS)
    if not files:
        sys.exit(f"No audio files found in {src}")

    out_dir = Path(args.output)
    out_dir.mkdir(exist_ok=True)
    spec_dir = out_dir / "spectrograms"
    if args.spectrograms:
        spec_dir.mkdir(exist_ok=True)

    rows = []
    for path in files:
        try:
            row = probe(path)
            if args.spectrograms:
                spectrogram(path, spec_dir)
        except (RuntimeError, subprocess.CalledProcessError) as e:
            print(f"! {path.name}: {e}", file=sys.stderr)
            continue
        rows.append(row)

    header = f"{'file':<45} {'codec':<7} {'stream':>7} {'overall':>8} {'rate':>7} {'ch':>3} {'secs':>8}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['file'][:44]:<45} {r['codec']!s:<7} "
            f"{r['stream_kbps'] or '-'!s:>7} {r['overall_kbps'] or '-'!s:>8} "
            f"{r['sample_rate_hz'] or '-'!s:>7} {r['channels'] or '-'!s:>3} "
            f"{r['duration_s'] or '-'!s:>8}"
        )

    csv_path = out_dir / "bitrates.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{len(rows)} tracks analysed. CSV: {csv_path}")
    if args.spectrograms:
        print(f"Spectrograms: {spec_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
