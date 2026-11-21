"""Local onboarding behavior; no social connections, network calls, or uploads."""
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/social-media-ai/scripts/setup.py"
spec = importlib.util.spec_from_file_location("social_setup", SCRIPT)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "inbox"
        self.source.mkdir()
        self.workspace = self.root / "workspace"

    def initialize(self):
        return setup.initialize(self.workspace, self.source)

    def profile(self):
        return json.loads((self.workspace / "profile.json").read_text())

    def save(self, profile):
        (self.workspace / "profile.json").write_text(json.dumps(profile))

    def snapshot(self):
        return {str(path.relative_to(self.workspace)): (path.read_bytes(), path.stat().st_mtime_ns)
                for path in self.workspace.rglob("*") if path.is_file()}

    def test_initializes_paused_review_profile_and_real_ledger(self):
        result = self.initialize()
        self.assertEqual(result["status"], "initialized")
        profile = self.profile()
        self.assertTrue(profile["paused"])
        self.assertEqual(profile["authorization"]["mode"], "review")
        self.assertEqual(profile["source_folder"], str(self.source))
        self.assertEqual(profile["workspace_folder"], str(self.workspace))
        for name in setup.FOLDERS:
            self.assertTrue((self.workspace / name).is_dir())
        with sqlite3.connect(self.workspace / "queue.sqlite3") as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 0)

    def test_repeat_preserves_profile_and_does_not_reset_recursion_or_consent(self):
        self.initialize()
        profile = self.profile()
        profile["recursive"] = True
        profile["authorization"] = {"mode": "automatic", "scope": "existing scope", "recorded_at": "2030-01-01"}
        self.save(profile)
        before = self.snapshot()
        result = self.initialize()
        self.assertEqual(result["status"], "resumed")
        self.assertEqual(before, self.snapshot())

    def test_different_source_requires_explicit_profile_change(self):
        self.initialize()
        other = self.root / "another-inbox"
        other.mkdir()
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "different source"):
            setup.initialize(self.workspace, other)
        self.assertEqual(before, self.snapshot())

    def test_source_and_workspace_cannot_overlap(self):
        for workspace, source in ((self.source, self.source), (self.source / "runtime", self.source), (self.root, self.source)):
            with self.subTest(workspace=workspace), self.assertRaisesRegex(ValueError, "non-nested"):
                setup.initialize(workspace, source)
        self.assertFalse((self.source / "runtime").exists())

    def test_repo_and_installed_skill_cannot_hold_runtime_workspace(self):
        for workspace in (setup.SKILL / "runtime", SCRIPT.parents[3] / "runtime"):
            with self.subTest(workspace=workspace), self.assertRaisesRegex(ValueError, "outside the repository"):
                setup.initialize(workspace, self.source)

    def test_other_git_repository_cannot_hold_private_workspace(self):
        another_repo = self.root / "another-project"
        another_repo.mkdir()
        (another_repo / ".git").mkdir()
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            setup.initialize(another_repo / "runtime", self.source)

    def test_archive_checkout_without_git_cannot_hold_private_workspace(self):
        checkout = self.root / "downloaded-archive"
        copied_skill = checkout / "skills" / "social-media-ai"
        shutil.copytree(setup.SKILL, copied_skill, ignore=shutil.ignore_patterns("__pycache__"))
        (checkout / "scripts").mkdir()
        (checkout / "scripts" / "install.py").write_text("# Archive installer")
        (checkout / "README.md").write_text("# Social-MediaAi")
        self.assertFalse((checkout / ".git").exists())
        with patch.object(setup, "SKILL", copied_skill):
            with self.assertRaisesRegex(ValueError, "outside the repository"):
                setup.initialize(checkout / "runtime", self.source)
        self.assertFalse((checkout / "runtime").exists())

    def test_installed_skill_does_not_protect_entire_codex_directory(self):
        codex = self.root / ".codex"
        copied_skill = codex / "skills" / "social-media-ai"
        shutil.copytree(setup.SKILL, copied_skill, ignore=shutil.ignore_patterns("__pycache__"))
        with patch.object(setup, "SKILL", copied_skill):
            workspace, source = setup.paths(codex / "private-workspace", self.source)
        self.assertEqual(workspace, codex / "private-workspace")
        self.assertEqual(source, self.source)

    def test_missing_source_does_not_create_workspace(self):
        with self.assertRaisesRegex(ValueError, "does not exist"):
            setup.initialize(self.workspace, self.root / "missing")
        self.assertFalse(self.workspace.exists())

    def test_unknown_existing_runtime_is_not_overwritten(self):
        self.workspace.mkdir()
        existing = self.workspace / "queue.sqlite3"
        existing.write_bytes(b"important existing ledger")
        with self.assertRaisesRegex(ValueError, "existing runtime files"):
            self.initialize()
        self.assertEqual(existing.read_bytes(), b"important existing ledger")
        self.assertFalse((self.workspace / "profile.json").exists())

    def test_doctor_is_read_only_and_lists_missing_setup(self):
        self.initialize()
        before = self.snapshot()
        with patch.object(setup.shutil, "which", return_value=None):
            result = setup.doctor(self.workspace)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(result["posting_readiness"], "not_verified")
        self.assertEqual(result["local_status"], "needs_attention")
        next_ids = {item["id"] for item in result["next_steps"]}
        self.assertTrue({"timezone", "account_records", "style", "schedule", "ffmpeg", "ffprobe"} <= next_ids)
        self.assertTrue(all(item["status"] == "not_checked" for item in result["agent_checks"]))
        self.assertIn("media_upload_path", {item["id"] for item in result["agent_checks"]})

    def test_doctor_missing_profile_does_not_create_files(self):
        result = setup.doctor(self.workspace)
        self.assertFalse(self.workspace.exists())
        self.assertEqual(result["local_status"], "needs_attention")

    def test_doctor_never_echoes_credentials_or_trusts_saved_connected_status(self):
        self.initialize()
        profile = self.profile()
        profile["timezone"] = "UTC"
        profile["connections"] = [{"platform": "instagram", "account_id": "123", "display_name": "Example",
                                    "supported_formats": ["image"], "status": "connected", "access_token": "DO_NOT_OUTPUT_SECRET"}]
        profile["captions"]["language"] = "English"
        profile["schedule"].update(days=["MO"], local_times=["09:00"], scheduler_id="saved-task-id")
        self.save(profile)
        result = setup.doctor(self.workspace)
        self.assertNotIn("DO_NOT_OUTPUT_SECRET", json.dumps(result))
        self.assertEqual(result["connections"][0]["live_status"], "not_checked")
        self.assertEqual(result["posting_readiness"], "not_verified")
        self.assertEqual(result["local_status"], "local_checks_passed")

    def test_automatic_mode_requires_recorded_scope_and_invalid_time_is_reported(self):
        self.initialize()
        profile = self.profile()
        profile["authorization"] = {"mode": "automatic", "scope": None, "recorded_at": None}
        profile["schedule"].update(days=["Monday"], local_times=["25:90"])
        profile["timezone"] = "Invalid/Place"
        self.save(profile)
        result = setup.doctor(self.workspace)
        checks = {item["name"]: item["status"] for item in result["local_checks"]}
        for name in ("authorization_record", "schedule", "timezone"):
            self.assertEqual(checks[name], "needs_attention")

    def test_malformed_optional_sections_are_reported_without_dumping_contents(self):
        self.initialize()
        profile = self.profile()
        profile["authorization"] = {"mode": {"secret": "PRIVATE_VALUE"}}
        profile["schedule"] = []
        profile["connections"] = [None, {"account_id": {"access_token": "PRIVATE_VALUE"}}]
        self.save(profile)
        result = setup.doctor(self.workspace)
        self.assertEqual(result["local_status"], "needs_attention")
        self.assertNotIn("PRIVATE_VALUE", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
