#!/usr/bin/env python3
"""Inspect or conservatively prepare a video; requires FFmpeg and FFprobe on PATH."""

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile


PRESETS = {
    "square": (1080, 1080),
    "portrait": (1080, 1350),
    "vertical": (1080, 1920),
    "landscape": (1920, 1080),
}


def executable(name):
    found = shutil.which(name)
    if not found:
        raise ValueError(f"{name} is missing. Install FFmpeg (including FFprobe) and add it to PATH.")
    return found


def input_path(value):
    path = Path(value).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError("Input must be a local regular video file.")
    return path


def probe(path):
    result = subprocess.run(
        [executable("ffprobe"), "-v", "error", "-show_format", "-show_streams",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True, timeout=60,
    )
    data = json.loads(result.stdout)
    videos = [s for s in data.get("streams", []) if s.get("codec_type") == "video"
              and not s.get("disposition", {}).get("attached_pic")]
    if not videos:
        raise ValueError("Input contains no playable video stream.")
    # Reject still images: FFprobe also reports them as video streams.
    if data.get("format", {}).get("format_name", "").endswith("_pipe") or data.get("format", {}).get("format_name") == "image2":
        raise ValueError("This helper prepares video files, not still images.")
    video = videos[0]
    audio = next((s for s in data["streams"] if s.get("codec_type") == "audio"), None)
    return {
        "path": str(path), "video_stream": video["index"], "codec": video.get("codec_name"),
        "width": video.get("width"), "height": video.get("height"),
        "sample_aspect_ratio": video.get("sample_aspect_ratio"),
        "duration_seconds": data.get("format", {}).get("duration"),
        "audio_stream": audio["index"] if audio else None,
        "rotation_degrees": next((s["rotation"] for s in video.get("side_data_list", [])
                                  if "rotation" in s), video.get("tags", {}).get("rotate", 0)),
        "color_transfer": video.get("color_transfer"),
    }


def command(source, destination, info, preset="original", denoise=False,
            audio_denoise=False, normalize_audio=False):
    # Square-pixel conversion accounts for anamorphic input; round to even sizes
    # for yuv420p. FFmpeg's default autorotation runs before these filters.
    filters = ["scale=w='max(2,trunc(iw*if(gt(sar,0),sar,1)/2)*2)':h='max(2,trunc(ih/2)*2)'", "setsar=1"]
    if preset != "original":
        width, height = PRESETS[preset]
        filters += [
            f"scale=w='min({width},iw)':h='min({height},ih)':force_original_aspect_ratio=decrease:force_divisible_by=2",
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black", "setsar=1",
        ]
    if denoise:
        filters.append("hqdn3d=1.5:1.5:3:3")
    args = [executable("ffmpeg"), "-nostdin", "-hide_banner", "-loglevel", "error", "-n",
            "-i", str(source), "-map", f"0:{info['video_stream']}", "-vf", ",".join(filters),
            "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p"]
    if info["audio_stream"] is not None:
        args += ["-map", f"0:{info['audio_stream']}", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
        audio_filters = []
        if audio_denoise:
            audio_filters.append("afftdn=nr=6:nf=-30")
        if normalize_audio:
            audio_filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
        if audio_filters:
            args += ["-af", ",".join(audio_filters)]
    args += ["-map_metadata", "-1", "-map_metadata:s", "-1", "-map_chapters", "-1",
             "-metadata:s:v:0", "rotate=0", "-movflags", "+faststart", "-f", "mp4", str(destination)]
    return args


def prepare(source, destination, preset="original", denoise=False,
            audio_denoise=False, normalize_audio=False, dry_run=False):
    source = input_path(source)
    output = Path(destination).expanduser().absolute()
    if output.suffix.lower() != ".mp4":
        raise ValueError("Output must have an .mp4 extension.")
    if output.exists() or output.is_symlink():
        raise ValueError("Output already exists. Choose a new filename; originals are never overwritten.")
    info = probe(source)
    if info.get("color_transfer") in {"smpte2084", "arib-std-b67"}:
        raise ValueError("HDR input requires a reviewed HDR-to-SDR workflow; this helper does not tone-map HDR.")
    kwargs = dict(preset=preset, denoise=denoise, audio_denoise=audio_denoise,
                  normalize_audio=normalize_audio)
    planned = command(source, output, info, **kwargs)
    if dry_run:
        return {"dry_run": True, "command": shlex.join(planned), "argv": planned}
    output.parent.mkdir(parents=True, exist_ok=True)
    # Same-filesystem hard link publishes a complete file atomically without
    # replacing an output another worker created while FFmpeg was running.
    with tempfile.TemporaryDirectory(prefix=".social-media-ai-", dir=output.parent) as temporary:
        staged = Path(temporary) / "prepared.mp4"
        subprocess.run(command(source, staged, info, **kwargs), check=True,
                       capture_output=True, text=True)
        if not staged.is_file() or staged.stat().st_size == 0:
            raise ValueError("FFmpeg produced no usable output.")
        verified = probe(staged)
        if verified["codec"] != "h264":
            raise ValueError("Prepared output did not verify as H.264 video.")
        os.link(staged, output)
    verified["path"] = str(output)
    return {"output": verified, "review": "Inspect the video and listen to its audio before scheduling."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    inspect_parser = actions.add_parser("inspect", help="Show video dimensions, duration and stream details")
    inspect_parser.add_argument("input")
    clean = actions.add_parser("prepare", help="Create a separate social-ready MP4 without cropping")
    clean.add_argument("input")
    clean.add_argument("output")
    clean.add_argument("--preset", choices=["original", *PRESETS], default="original")
    clean.add_argument("--denoise", action="store_true", help="Apply mild video denoising")
    clean.add_argument("--audio-denoise", action="store_true", help="Apply mild audio denoising")
    clean.add_argument("--normalize-audio", action="store_true", help="Apply one-pass loudness normalization")
    clean.add_argument("--dry-run", action="store_true", help="Inspect input and print the command without writing")
    args = parser.parse_args(argv)
    try:
        if args.action == "inspect":
            result = probe(input_path(args.input))
        else:
            result = prepare(args.input, args.output, args.preset, args.denoise,
                             args.audio_denoise, args.normalize_audio, args.dry_run)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        detail = getattr(error, "stderr", None) or str(error)
        print(f"Video preparation failed: {detail[-2000:]}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
