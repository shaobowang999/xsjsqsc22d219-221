import sys
import io
import json
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import desktop_app
import main


class DesktopSourceLoadingTests(unittest.TestCase):
    def test_old_running_server_cannot_mask_the_new_client(self):
        response = io.BytesIO(json.dumps({"name": "三千思创", "version": "10.21"}).encode())
        with patch.object(desktop_app, "PORT", 3000), patch.object(desktop_app, "APP_URL", "http://127.0.0.1:3000/"), patch.object(desktop_app, "port_is_open", return_value=True), patch.object(desktop_app.urllib.request, "urlopen", return_value=response), patch.object(desktop_app.socket, "socket") as factory:
            factory.return_value.__enter__.return_value.getsockname.return_value = ("127.0.0.1", 54321)
            desktop_app.select_server_port()
            self.assertEqual(desktop_app.PORT, 54321)
            self.assertEqual(desktop_app.APP_URL, "http://127.0.0.1:54321/")

    def test_same_release_server_can_be_reused(self):
        response = io.BytesIO(json.dumps({"name": "三千思创", "version": "2026.10.29"}).encode())
        with patch.object(desktop_app, "PORT", 3000), patch.object(desktop_app, "APP_URL", "http://127.0.0.1:3000/"), patch.object(desktop_app, "port_is_open", return_value=True), patch.object(desktop_app.urllib.request, "urlopen", return_value=response), patch.object(desktop_app.socket, "socket") as factory:
            desktop_app.select_server_port()
            self.assertEqual(desktop_app.PORT, 3000)
            factory.assert_not_called()

    def test_current_source_overrides_an_already_imported_backend(self):
        root = Path(main.DATA_DIR) / ("launcher-test-" + uuid.uuid4().hex)
        root.mkdir(parents=True)
        (root / "main.py").write_text("app = 'updated-source-app'\n", encoding="utf-8")
        embedded = Mock(app="embedded-old-app")
        with patch.dict(sys.modules, {"main": embedded}), patch.object(desktop_app, "application_dir", return_value=root), patch.object(desktop_app, "port_is_open", return_value=False), patch.object(desktop_app.uvicorn, "Config") as config, patch.object(desktop_app.uvicorn, "Server"), patch.object(desktop_app.threading, "Thread"):
            runtime = desktop_app.DesktopRuntime()
            runtime.start_server()
            self.assertEqual(config.call_args.args[0], "updated-source-app")
            self.assertEqual(sys.modules["main"].__file__, str(root / "main.py"))
            self.assertTrue(runtime.owns_server)


if __name__ == "__main__":
    unittest.main()
