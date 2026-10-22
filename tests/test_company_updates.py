import io
import json
import os
import sys
import unittest
import uuid
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


class CompanyUpdateTests(unittest.TestCase):
    def test_legacy_company_version_does_not_rank_below_old_upstream(self):
        self.assertFalse(main.version_gt("2026.08.28", "10.21"))
        self.assertFalse(main.version_gt("2026.10.22", "10.22"))
        self.assertTrue(main.version_gt("2026.10.23", "10.22"))
        self.assertFalse(main.version_gt("10.22", "2026.10.22.0"))
        self.assertFalse(main.version_gt("2026.10.22", "2026.10.22"))

    def test_check_only_contacts_company_version_source(self):
        with patch.object(main, "current_app_version", return_value="2026.10.22"), patch.object(main, "fetch_remote_version", return_value={"ok": True, "version": "2026.10.22"}) as fetch, patch.object(main, "fetch_update_notes_with_fallback", return_value=({"ok": True, "version": "2026.10.22", "items": [{"text": "Latest changes"}]}, {})):
            result = main.check_update()
        fetch.assert_called_once_with(main.GITHUB_VERSION_URL, timeout=5.0)
        self.assertFalse(result["update_available"])
        self.assertEqual(result["latest"]["source"], "github")
        self.assertEqual(result["update_notes"]["version"], result["current"])
        self.assertNotIn("modelscope", result)

    def test_new_company_build_advertises_matching_release(self):
        with patch.object(main, "current_app_version", return_value="10.21"), patch.object(main, "fetch_remote_version", return_value={"ok": True, "version": "2026.10.22"}), patch.object(main, "fetch_update_notes_with_fallback", return_value=({"ok": True, "version": "2026.10.22", "items": [{"text": "Video fix"}]}, {})):
            result = main.check_update()
        self.assertTrue(result["update_available"])
        self.assertEqual(result["latest"]["version"], "2026.10.22")
        self.assertEqual(result["update_notes"]["items"][0]["text"], "Video fix")

    def test_company_outage_does_not_fall_back_to_upstream(self):
        with patch.object(main, "fetch_remote_version", return_value={"ok": False, "version": "", "error": "Offline"}) as fetch:
            result = main.check_update()
        self.assertEqual(fetch.call_count, 1)
        self.assertFalse(result["reachable"])
        self.assertFalse(result["update_available"])

    def test_old_source_preference_migrates_to_company(self):
        for source in ["modelscope", "ms", "", "unknown"]:
            self.assertEqual(main.normalize_update_source(source), "github")
        self.assertEqual(main.normalize_update_source("github_archive"), "github_archive")

    def test_remote_notes_for_another_version_are_rejected(self):
        response = Mock(status_code=200, content=json.dumps({"version": "2026.08.28", "items": ["Old changes"]}).encode())
        with patch.object(main.requests, "get", return_value=response):
            result = main.fetch_remote_update_notes(main.GITHUB_UPDATE_NOTES_URL, "2026.10.22")
        self.assertFalse(result["ok"])

    def test_app_info_exposes_only_company_sources_and_current_notes(self):
        result = main.app_info()
        self.assertEqual(set(result["sources"]), {"github", "github_archive"})
        self.assertEqual(result["version"], "2026.10.22")
        self.assertEqual(result["update_notes"]["version"], result["version"])
        for source in result["sources"].values():
            self.assertIn("shaobowang999/xsjsqsc22d219-221", source["repo_url"])

    def staged_files(self, version, notes_version):
        # Keep fixture files in the ignored runtime data directory; no cleanup or
        # update installation is performed by these regression tests.
        root = Path(main.DATA_DIR) / ("update-test-" + uuid.uuid4().hex)
        (root / "static").mkdir(parents=True)
        (root / "main.py").write_text("value = 1\n", encoding="utf-8")
        (root / "VERSION").write_text(version, encoding="utf-8")
        (root / "static/update-notes.json").write_text(json.dumps({"version": notes_version, "items": []}), encoding="utf-8")
        return root

    def test_downgrade_is_blocked_before_live_installation(self):
        root = self.staged_files("2026.08.28", "2026.08.28")
        with self.assertRaisesRegex(RuntimeError, "早于当前版本"):
            main.validate_staged_update(str(root), ["main.py", "VERSION"], ["static/update-notes.json"])

    def test_mismatched_release_notes_block_installation(self):
        root = self.staged_files("2026.10.22", "2026.08.28")
        with self.assertRaisesRegex(RuntimeError, "日志与 VERSION 不一致"):
            main.validate_staged_update(str(root), ["main.py", "VERSION"], ["static/update-notes.json"])

    def test_archive_fallback_stages_only_allowed_company_files(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("repo/main.py", "value = 1\n")
            archive.writestr("repo/VERSION", "2026.10.22")
            archive.writestr("repo/static/update-notes.json", '{"version":"2026.10.22"}')
            archive.writestr("repo/API/.env", "not an update file")
            archive.writestr("repo/static/../../escape.txt", "invalid")
        root = Path(main.DATA_DIR) / ("archive-test-" + uuid.uuid4().hex)
        with patch.object(main, "github_bytes", return_value=buffer.getvalue()) as download:
            _, _, files = main.stage_update_from_source("github_archive", str(root))
        download.assert_called_once_with(main.GITHUB_ARCHIVE_URL)
        self.assertEqual(set(files), {"main.py", "VERSION", "static/update-notes.json"})
        self.assertFalse((root / "API").exists())
        self.assertFalse((root / "escape.txt").exists())


if __name__ == "__main__":
    unittest.main()
