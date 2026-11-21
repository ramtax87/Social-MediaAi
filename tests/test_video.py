import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch


MODULE = Path(__file__).resolve().parents[1] / "skills/social-media-ai/scripts/video.py"
spec = importlib.util.spec_from_file_location("social_video", MODULE)
video = importlib.util.module_from_spec(spec)
spec.loader.exec_module(video)
INFO = {"video_stream": 0, "audio_stream": 1, "codec": "h264", "color_transfer": "bt709"}


class VideoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "original $(unsafe).mov"
        self.source.write_bytes(b"original")
        self.output = self.root / "output.mp4"

    @patch.object(video, "executable", side_effect=lambda name: name)
    def test_argument_arrays_preserve_paths_and_optional_audio(self, _):
        args = video.command(self.source, self.output, INFO, "vertical", True, True, True)
        self.assertEqual(args[args.index("-i") + 1], str(self.source))
        self.assertIn("pad=1080:1920", args[args.index("-vf") + 1])
        self.assertIn("afftdn", args[args.index("-af") + 1])
        silent = video.command(self.source, self.output, {**INFO, "audio_stream": None})
        self.assertNotIn("-af", silent)
        self.assertNotIn("-c:a", silent)
        self.assertNotIn("crop", args[args.index("-vf") + 1])

    def test_existing_output_is_not_overwritten(self):
        self.output.write_bytes(b"existing")
        with self.assertRaisesRegex(ValueError, "already exists"):
            video.prepare(self.source, self.output)
        self.assertEqual(self.output.read_bytes(), b"existing")
        with self.assertRaisesRegex(ValueError, "already exists"):
            video.prepare(self.output, self.output)

    @patch.object(video, "probe", return_value=INFO)
    @patch.object(video, "executable", side_effect=lambda name: name)
    def test_dry_run_writes_nothing(self, *_):
        result = video.prepare(self.source, self.output, dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertFalse(self.output.exists())
        self.assertEqual(self.source.read_bytes(), b"original")

    @patch.object(video, "probe", return_value=INFO)
    @patch.object(video, "executable", side_effect=lambda name: name)
    def test_failed_transcode_cleans_temporary_files(self, *_):
        def fail(args, **kwargs):
            Path(args[-1]).write_bytes(b"partial")
            raise subprocess.CalledProcessError(1, args, stderr="encoder failure")
        with patch.object(video.subprocess, "run", side_effect=fail):
            with self.assertRaises(subprocess.CalledProcessError):
                video.prepare(self.source, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob(".social-media-ai-*")), [])

    @patch.object(video, "probe", return_value=INFO)
    @patch.object(video, "executable", side_effect=lambda name: name)
    def test_output_created_by_other_worker_is_not_replaced(self, *_):
        def encode(args, **kwargs):
            Path(args[-1]).write_bytes(b"new video")
            self.output.write_bytes(b"other worker")
        with patch.object(video.subprocess, "run", side_effect=encode):
            with self.assertRaises(FileExistsError):
                video.prepare(self.source, self.output)
        self.assertEqual(self.output.read_bytes(), b"other worker")

    @patch.object(video, "probe", return_value={**INFO, "color_transfer": "smpte2084"})
    def test_hdr_is_not_silently_converted(self, _):
        with self.assertRaisesRegex(ValueError, "HDR"):
            video.prepare(self.source, self.output)

    @patch.object(video.shutil, "which", return_value=None)
    def test_missing_dependency_is_actionable(self, _):
        with self.assertRaisesRegex(ValueError, "Install FFmpeg"):
            video.probe(self.source)

    @patch.object(video, "executable", return_value="ffprobe")
    def test_probe_skips_cover_art_and_reports_rotation(self, _):
        data = {"streams": [
            {"index": 0, "codec_type": "video", "disposition": {"attached_pic": 1}},
            {"index": 2, "codec_type": "video", "codec_name": "h264", "side_data_list": [{"rotation": 90}]},
        ], "format": {"duration": "2.0", "format_name": "mov,mp4,m4a,3gp,3g2,mj2"}}
        with patch.object(video.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, json.dumps(data))):
            result = video.probe(self.source)
        self.assertEqual(result["video_stream"], 2)
        self.assertEqual(result["rotation_degrees"], 90)
        self.assertIsNone(result["audio_stream"])


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg and FFprobe not installed")
class RealVideoTests(unittest.TestCase):
    def test_odd_anamorphic_video_and_audio_are_cleaned(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, output = root / "source.mkv", root / "output.mp4"
            subprocess.run([
                "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=323x243:rate=5:duration=0.6",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=0.6", "-vf", "setsar=4/3",
                "-c:v", "ffv1", "-c:a", "pcm_s16le", "-metadata", "location=private-location",
                "-metadata", "title=private-title", str(source),
            ], check=True, capture_output=True)
            original = source.read_bytes()
            result = video.prepare(source, output, denoise=True, audio_denoise=True, normalize_audio=True)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(result["output"]["codec"], "h264")
            self.assertEqual(result["output"]["width"] % 2, 0)
            self.assertEqual(result["output"]["height"] % 2, 0)
            self.assertEqual(result["output"]["sample_aspect_ratio"], "1:1")
            self.assertIsNotNone(result["output"]["audio_stream"])
            metadata = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(output)],
                                      check=True, capture_output=True, text=True).stdout
            self.assertNotIn("private-location", metadata)
            self.assertNotIn("private-title", metadata)

    def test_preset_pads_to_square(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, output = root / "source.mp4", root / "output.mp4"
            subprocess.run([
                "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=5:duration=0.4",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
            ], check=True, capture_output=True)
            result = video.prepare(source, output, preset="square")
            self.assertEqual((result["output"]["width"], result["output"]["height"]), (1080, 1080))
            self.assertIsNone(result["output"]["audio_stream"])

    def test_phone_rotation_is_applied_before_metadata_removal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, rotated, output = root / "source.mp4", root / "rotated.mp4", root / "output.mp4"
            subprocess.run([
                "ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=5:duration=0.4",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
            ], check=True, capture_output=True)
            subprocess.run([
                "ffmpeg", "-v", "error", "-display_rotation:v:0", "90", "-i", str(source), "-c", "copy", str(rotated),
            ], check=True, capture_output=True)
            self.assertEqual(abs(float(video.probe(rotated)["rotation_degrees"])), 90)
            result = video.prepare(rotated, output)
            self.assertEqual((result["output"]["width"], result["output"]["height"]), (240, 320))
            self.assertEqual(float(result["output"]["rotation_degrees"]), 0)


if __name__ == "__main__":
    unittest.main()
