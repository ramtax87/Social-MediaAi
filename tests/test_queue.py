"""Behavioral tests for the local ledger; no external services or real media."""
import concurrent.futures
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/social-media-ai/scripts/queue.py"


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "inbox"
        self.source.mkdir()
        self.media = self.source / "picture.jpg"
        self.media.write_bytes(b"original image bytes")
        self.prepared = self.root / "prepared.jpg"
        self.prepared.write_bytes(b"prepared image bytes")
        self.caption = self.root / "caption.txt"
        self.caption.write_text("A useful caption", encoding="utf-8")
        self.db = self.root / "queue.sqlite3"

    def run_cli(self, *args, succeeds=True):
        result = subprocess.run([sys.executable, str(SCRIPT), "--db", str(self.db), *map(str, args)],
                                text=True, capture_output=True)
        if succeeds:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return json.loads(result.stderr)

    def new_job(self, future=False, destination="instagram:account-123"):
        self.run_cli("scan", self.source, "--min-age", 0)
        media_id = self.run_cli("media")[0]["id"]
        due = datetime.now(timezone.utc) + timedelta(days=1 if future else -1)
        return self.run_cli("plan", media_id, "--destination", destination, "--due", due.isoformat(),
                            "--prepared", self.prepared, "--caption-file", self.caption)

    def test_scan_deduplicates_content_and_tracks_rename(self):
        first = self.run_cli("scan", self.source, "--min-age", 0)
        self.assertEqual(first["added_count"], 1)
        self.media.rename(self.source / "renamed.jpg")
        (self.source / "copy.jpg").write_bytes(b"original image bytes")
        self.run_cli("scan", self.source, "--min-age", 0)
        rows = self.run_cli("media")
        self.assertEqual(len(rows), 1)
        self.assertTrue(Path(rows[0]["path"]).is_file())
        self.assertEqual(rows[0]["id"], first["added"][0]["id"])

    def test_scan_ignores_hidden_symlink_empty_and_recent(self):
        (self.source / ".hidden.jpg").write_bytes(b"hidden")
        (self.source / "empty.jpg").touch()
        (self.source / "link.jpg").symlink_to(self.media)
        hidden_dir = self.source / ".private"
        hidden_dir.mkdir()
        (hidden_dir / "private.jpg").write_bytes(b"private")
        self.assertEqual(self.run_cli("scan", self.source, "--recursive")["added_count"], 0)
        self.assertEqual(self.run_cli("scan", self.source, "--recursive", "--min-age", 0)["added_count"], 1)

    def test_scan_rebinds_renamed_original_when_old_filename_is_reused(self):
        job = self.new_job()
        archived = self.source / "archived-picture.jpg"
        self.media.rename(archived)
        self.media.write_bytes(b"different image in reused filename")
        self.run_cli("scan", self.source, "--min-age", 0)
        media = {row["id"]: row for row in self.run_cli("media")}
        self.assertEqual(len(media), 2)
        self.assertEqual(media[job["media_id"]]["path"], str(archived))
        self.run_cli("approve", job["id"])
        self.assertEqual(self.run_cli("claim", job["id"])["state"], "submitting")

    def test_scan_rebinds_renamed_original_when_old_path_becomes_symlink(self):
        job = self.new_job()
        archived = self.source / "archived-picture.jpg"
        self.media.rename(archived)
        self.media.symlink_to(self.prepared)
        self.run_cli("scan", self.source, "--min-age", 0)
        self.assertEqual(self.run_cli("media")[0]["path"], str(archived))
        self.run_cli("approve", job["id"])
        self.assertEqual(self.run_cli("claim", job["id"])["state"], "submitting")

    def test_plan_requires_offset_and_separate_prepared_copy(self):
        job = self.new_job()
        self.run_cli("plan", job["media_id"], "--destination", "x:y", "--due", "2030-01-01T12:00:00",
                     "--prepared", self.prepared, "--caption-file", self.caption, succeeds=False)
        self.run_cli("plan", job["media_id"], "--destination", "x:y", "--due", "2030-01-01T12:00:00Z",
                     "--prepared", self.media, "--caption-file", self.caption, succeeds=False)

    def test_same_media_can_target_different_accounts_but_no_repost(self):
        job = self.new_job()
        second = self.new_job(destination="linkedin:company-456")
        self.assertNotEqual(job["id"], second["id"])
        self.run_cli("approve", job["id"])
        self.run_cli("claim", job["id"])
        self.run_cli("finish", job["id"], "--state", "published", "--receipt", "post-001")
        self.run_cli("plan", job["media_id"], "--destination", job["destination"], "--due", job["due"],
                     "--prepared", self.prepared, "--caption-file", self.caption, succeeds=False)
        self.assertEqual(len(self.run_cli("list")), 2)

    def test_edited_prepared_caption_and_original_invalidate_approval(self):
        for path in (self.prepared, self.caption, self.media):
            with self.subTest(path=path):
                old = path.read_bytes()
                job = self.new_job()
                self.run_cli("approve", job["id"])
                path.write_bytes(b"changed after approval")
                self.run_cli("claim", job["id"], succeeds=False)
                path.write_bytes(old)

    def test_replanning_clears_approval(self):
        job = self.new_job()
        self.run_cli("approve", job["id"])
        replanned = self.new_job()
        self.assertEqual(replanned["state"], "draft")
        self.assertIsNone(replanned["approval"])
        self.run_cli("claim", job["id"], succeeds=False)

    def test_platform_metadata_is_bound_to_approval(self):
        job = self.new_job()
        metadata = self.root / "metadata.json"
        metadata.write_text(json.dumps({"title": "My video", "privacy": "private"}), encoding="utf-8")
        planned = self.run_cli("plan", job["media_id"], "--destination", job["destination"], "--due", job["due"],
                               "--prepared", self.prepared, "--caption-file", self.caption,
                               "--metadata-file", metadata)
        self.assertEqual(planned["metadata"]["privacy"], "private")
        self.run_cli("approve", planned["id"])
        metadata.write_text(json.dumps({"title": "My video", "privacy": "public"}), encoding="utf-8")
        self.run_cli("claim", planned["id"], succeeds=False)

    def test_exactly_one_concurrent_claim_succeeds(self):
        job = self.new_job()
        self.run_cli("approve", job["id"])
        command = [sys.executable, str(SCRIPT), "--db", str(self.db), "claim", job["id"]]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: subprocess.run(command, capture_output=True), range(2)))
        self.assertEqual(sorted(result.returncode for result in results), [0, 1])
        self.assertEqual(self.run_cli("list")[0]["state"], "submitting")

    def test_ambiguous_results_require_reconciliation(self):
        job = self.new_job()
        self.run_cli("approve", job["id"])
        self.run_cli("claim", job["id"])
        self.run_cli("uncertain", job["id"], "--reason", "timeout after provider accepted upload")
        self.run_cli("claim", job["id"], succeeds=False)
        self.run_cli("approve", job["id"], succeeds=False)
        self.run_cli("resolve", job["id"], "--verified-absent", succeeds=False)
        resolved = self.run_cli("resolve", job["id"], "--state", "published", "--receipt", "remote-id-001")
        self.assertEqual(resolved["state"], "published")
        self.assertEqual(resolved["receipt"], "remote-id-001")

    def test_verified_absent_requires_fresh_approval(self):
        job = self.new_job()
        self.run_cli("approve", job["id"])
        self.run_cli("claim", job["id"])
        resolved = self.run_cli("resolve", job["id"], "--verified-absent", "--evidence",
                                "Provider confirms request rejected before any post was created")
        self.assertEqual(resolved["state"], "draft")
        self.run_cli("claim", job["id"], succeeds=False)
        self.run_cli("approve", job["id"])
        self.assertEqual(self.run_cli("claim", job["id"])["state"], "submitting")

    def test_future_schedule_and_later_publication_receipts(self):
        job = self.new_job(future=True)
        self.run_cli("approve", job["id"])
        self.run_cli("claim", job["id"], succeeds=False)
        self.run_cli("claim", job["id"], "--schedule")
        scheduled = self.run_cli("finish", job["id"], "--state", "scheduled", "--receipt", "schedule-001")
        self.assertEqual(scheduled["state"], "scheduled")
        self.run_cli("claim", job["id"], "--schedule", succeeds=False)
        published = self.run_cli("finish", job["id"], "--state", "published", "--receipt", "https://social.example/post/001")
        self.assertEqual(published["state"], "published")
        with sqlite3.connect(self.db) as db:
            receipts = [json.loads(row[0])["receipt"] for row in db.execute(
                "SELECT detail FROM events WHERE job_id=? AND state IN ('scheduled','published') ORDER BY id",
                (job["id"],))]
        self.assertEqual(receipts, ["schedule-001", "https://social.example/post/001"])


if __name__ == "__main__":
    unittest.main()
