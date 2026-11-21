"""Installer behavior in temporary directories; no real skill installation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/install.py"
SPEC = importlib.util.spec_from_file_location("social_install", SCRIPT)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "checkout" / "skills" / installer.NAME
        self.source.mkdir(parents=True)
        (self.source / "SKILL.md").write_text("original skill", encoding="utf-8")
        self.parent = self.root / "custom-agent" / "skills"
        self.destination = self.parent / installer.NAME

    def install(self, **options):
        return installer.install(self.source, self.parent, **options)

    def test_custom_install_and_repeat_are_idempotent(self):
        self.assertEqual(self.install()["status"], "installed")
        before = (self.destination / "SKILL.md").stat().st_mtime_ns
        self.assertEqual(self.install()["status"], "already installed")
        self.assertEqual((self.destination / "SKILL.md").stat().st_mtime_ns, before)
        self.assertFalse((self.parent.parent / "skill-backups").exists())

    def test_different_install_requires_update_and_keeps_custom_files(self):
        self.install()
        custom = self.destination / "notes.txt"
        custom.write_text("user customizations", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "--update"):
            self.install()
        self.assertEqual(custom.read_text(), "user customizations")
        (self.source / "SKILL.md").write_text("new skill", encoding="utf-8")
        result = self.install(update=True)
        backup = Path(result["backup"])
        self.assertFalse(backup.is_relative_to(self.parent))
        self.assertEqual((backup / "SKILL.md").read_text(), "original skill")
        self.assertEqual((backup / "notes.txt").read_text(), "user customizations")
        self.assertEqual((self.destination / "SKILL.md").read_text(), "new skill")

    def test_failed_replacement_restores_old_install(self):
        self.install()
        (self.source / "SKILL.md").write_text("new skill", encoding="utf-8")
        rename = Path.rename

        def fail_staged(path, target):
            if path.parent.name.startswith(".social-media-ai-install-"):
                raise OSError("simulated final rename failure")
            return rename(path, target)

        with patch.object(Path, "rename", fail_staged):
            with self.assertRaisesRegex(OSError, "simulated final rename failure"):
                self.install(update=True)
        self.assertEqual((self.destination / "SKILL.md").read_text(), "original skill")
        self.assertEqual(list(self.parent.parent.glob(".social-media-ai-install-*")), [])

    def test_failed_staging_does_not_move_existing_install(self):
        self.install()
        (self.source / "SKILL.md").write_text("new skill", encoding="utf-8")
        with patch.object(installer.shutil, "copytree", side_effect=OSError("copy failed")):
            with self.assertRaisesRegex(OSError, "copy failed"):
                self.install(update=True)
        self.assertEqual((self.destination / "SKILL.md").read_text(), "original skill")
        self.assertFalse((self.parent.parent / "skill-backups").exists())

    def test_check_is_read_only_and_reports_current_or_different(self):
        self.assertEqual(self.install(check=True)["status"], "missing")
        self.assertFalse(self.parent.exists())
        self.install()
        self.assertEqual(self.install(check=True)["status"], "current")
        (self.source / "SKILL.md").write_text("new skill", encoding="utf-8")
        self.assertEqual(self.install(check=True)["status"], "different")
        self.assertEqual((self.destination / "SKILL.md").read_text(), "original skill")

    def test_python_caches_are_not_installed_or_compared(self):
        (self.source / "__pycache__").mkdir()
        (self.source / "__pycache__" / "cache.pyc").write_bytes(b"cache")
        self.install()
        self.assertFalse((self.destination / "__pycache__").exists())
        (self.destination / "__pycache__").mkdir()
        (self.destination / "__pycache__" / "runtime.pyc").write_bytes(b"runtime cache")
        self.assertEqual(self.install()["status"], "already installed")

    def test_symlink_install_and_self_install_are_rejected(self):
        self.parent.mkdir(parents=True)
        self.destination.symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.install(update=True)
        self.assertTrue(self.destination.is_symlink())
        with self.assertRaisesRegex(ValueError, "separate directories"):
            installer.install(self.source, self.source.parent, update=True)


if __name__ == "__main__":
    unittest.main()
