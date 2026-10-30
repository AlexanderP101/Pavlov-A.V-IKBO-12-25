"""Автоматические тесты логики эмулятора."""

import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.main import ShellEmulator, VirtualFileSystem, XmlLogger


class EmulatorTests(unittest.TestCase):
    """Проверки команд, ZIP-VFS и XML-журнала."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        archive_path = self.root / "vfs.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("docs/readme.txt", "hello")
        self.vfs = VirtualFileSystem(str(archive_path))
        self.logger = XmlLogger(str(self.root / "log.xml"))
        self.shell = ShellEmulator(self.vfs, self.logger)

    def test_ls_is_stub(self):
        success, output = self.shell.execute('ls "my folder"')
        self.assertTrue(success)
        self.assertEqual(output, "ls: аргументы: my folder")

    def test_cd_is_stub(self):
        success, output = self.shell.execute("cd /tmp")
        self.assertTrue(success)
        self.assertEqual(output, "cd: аргументы: /tmp")

    def test_unknown_command_fails(self):
        success, output = self.shell.execute("unknown")
        self.assertFalse(success)
        self.assertIn("неизвестная команда", output)

    def test_wrong_arguments_fail(self):
        success, output = self.shell.execute("vfs-save")
        self.assertFalse(success)
        self.assertIn("использование", output)

    def test_vfs_save_preserves_archive_bytes(self):
        destination = self.root / "copy.zip"
        success, output = self.shell.execute(f"vfs-save {destination}")
        self.assertTrue(success)
        self.assertTrue(destination.exists())
        self.assertEqual(
            destination.read_bytes(), self.vfs.archive_bytes
        )
        self.assertIn("VFS сохранена", output)

    def test_log_is_xml(self):
        self.shell.execute("ls")
        content = (self.root / "log.xml").read_text(encoding="utf-8")
        self.assertIn("<events", content)
        self.assertIn("<command>ls</command>", content)
        self.assertIn("timestamp=", content)

    def test_invalid_archive_fails(self):
        broken = self.root / "broken.zip"
        broken.write_text("not a zip", encoding="utf-8")
        with self.assertRaises(ValueError):
            VirtualFileSystem(str(broken))


if __name__ == "__main__":
    unittest.main()
