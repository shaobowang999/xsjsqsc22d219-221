"""Exercise native disk writes and streaming headers without starting the app."""
import ast
import base64
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
import uuid

ROOT = Path(__file__).resolve().parents[1]


def load_definition(filename, name, namespace):
    tree = ast.parse((ROOT / filename).read_text(encoding='utf-8-sig'))
    definition = next(node for node in tree.body if getattr(node, 'name', '') == name)
    definition.decorator_list = []
    exec(compile(ast.Module(body=[definition], type_ignores=[]), filename, 'exec'), namespace)
    return namespace[name]


class CanvasDownloadTests(unittest.TestCase):
    def test_save_writes_exact_bytes_and_preserves_existing_files(self):
        folder = ROOT / 'output' / ('download-test-' + uuid.uuid4().hex)
        folder.mkdir(parents=True)
        namespace = dict(Path=Path, base64=base64, os=os, sys=SimpleNamespace(platform='test'), webview=Mock())
        api = load_definition('desktop_app.py', 'DesktopFiles', namespace)()
        # Isolate the default Downloads directory from the user's real folders.
        namespace['Path'] = Mock(wraps=Path)
        namespace['Path'].home.return_value = folder
        encoded = base64.b64encode(b'\x89PNG\r\n\x1a\ncanvas-test').decode()
        first = api.save_download(encoded, '../image.png')
        second = api.save_download(encoded, 'image.png')
        self.assertTrue(first['ok'])
        self.assertTrue(second['ok'])
        self.assertEqual(Path(first['path']).parent, folder / 'Downloads')
        self.assertNotEqual(first['path'], second['path'])
        self.assertEqual(Path(first['path']).read_bytes(), base64.b64decode(encoded))
        namespace['webview'].windows = [Mock()]
        namespace['webview'].windows[0].create_file_dialog.return_value = None
        self.assertTrue(api.save_download(encoded, 'image.png', True)['cancelled'])
        chosen = folder / 'chosen.png'
        namespace['webview'].windows[0].create_file_dialog.return_value = (str(chosen),)
        saved_as = api.save_download(encoded, 'image.png', True)
        self.assertTrue(saved_as['ok'])
        self.assertEqual(chosen.read_bytes(), base64.b64decode(encoded))
        self.assertFalse(api.save_download('invalid base64!', 'bad.png')['ok'])

    def test_remote_download_exposes_length_for_progress_and_closes_stream(self):
        upstream = Mock()
        upstream.headers = {'content-type':'image/png','content-length':'6'}
        upstream.status_code = 200
        upstream.iter_content.return_value = iter([b'abc', b'def'])
        requests = Mock()
        requests.get.return_value = upstream
        import urllib.parse
        namespace = dict(
            Request=object, requests=requests, os=os, urllib=urllib,
            rewrite_runninghub_file_url=lambda url:url,
            output_file_from_url=lambda url:None,
            local_media_file_by_basename=lambda name:None,
            filename_from_media_url=lambda url, fallback: fallback,
            sanitize_export_filename=lambda name, fallback:name,
            StreamingResponse=lambda body, **kwargs:SimpleNamespace(body=body, **kwargs),
        )
        download = load_definition('main.py', 'download_output', namespace)
        result = download(SimpleNamespace(headers={}), 'https://example.test/image.png', 'image.png')
        self.assertEqual(result.headers['Content-Length'], '6')
        self.assertEqual(b''.join(result.body), b'abcdef')
        upstream.close.assert_called_once()
        self.assertEqual(requests.get.call_args.kwargs['headers']['Accept-Encoding'], 'identity')


if __name__ == '__main__':
    unittest.main()
