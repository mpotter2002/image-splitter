from __future__ import annotations

import base64
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import web_app


class WebAppServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        web_app.DOWNLOAD_ROOT = Path(cls.temp_dir.name)
        web_app.DOWNLOADS.clear()
        cls.server = web_app.ImageSplitterHTTPServer(("127.0.0.1", 0), web_app.ImageSplitterHandler)
        cls.port = cls.server.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        web_app.DOWNLOADS.clear()
        cls.temp_dir.cleanup()

    def setUp(self) -> None:
        web_app.DOWNLOADS.clear()

    def request_json(self, path: str, payload: dict | None = None) -> tuple[int, dict]:
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(f"{self.base_url}{path}", data=data, headers=headers)
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def sample_payload(self) -> dict:
        image_path = Path(__file__).with_name("sample_input.png")
        image_bytes = image_path.read_bytes()
        return {
            "filename": "sample_input.png",
            "image_data_url": "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii"),
            "settings": {},
        }

    def test_health_endpoint_reports_ready(self) -> None:
        status, payload = self.request_json("/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"ok": True, "status": "ready"})

    def test_preview_and_split_happy_path(self) -> None:
        preview_status, preview = self.request_json("/api/preview", self.sample_payload())
        self.assertEqual(preview_status, 200)
        self.assertEqual(preview["component_count"], 3)
        self.assertEqual(preview["image_width"], 420)
        self.assertEqual(preview["image_height"], 180)

        split_status, split = self.request_json("/api/split", self.sample_payload())
        self.assertEqual(split_status, 200)
        self.assertEqual(split["manifest"]["component_count"], 3)
        self.assertEqual(len(split["previews"]), 3)
        self.assertTrue(split["download_url"].startswith("/api/download/"))

        with urllib.request.urlopen(f"{self.base_url}{split['download_url']}") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "application/zip")
            self.assertGreater(len(response.read()), 0)

    def test_invalid_upload_returns_safe_error(self) -> None:
        bad_payload = {
            "filename": "bad.txt",
            "image_data_url": "data:image/png;base64," + base64.b64encode(b"not an image").decode("ascii"),
            "settings": {},
        }
        status, payload = self.request_json("/api/preview", bad_payload)
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "Upload a valid PNG, JPG, WebP, or GIF image.")


if __name__ == "__main__":
    unittest.main()
