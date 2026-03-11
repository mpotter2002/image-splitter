#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import secrets
import tempfile
import time
import zipfile
from collections import OrderedDict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from split_icons import encode_png_bytes, split_image_bytes


APP_ROOT = Path(__file__).resolve().parent
WEB_ROOT = APP_ROOT / "web"
INDEX_HTML = WEB_ROOT / "index.html"
DOWNLOAD_TTL_SECONDS = 30 * 60
MAX_UPLOAD_BYTES = int(os.environ.get("IMAGE_SPLITTER_MAX_UPLOAD_BYTES", 12 * 1024 * 1024))
MAX_REQUEST_BYTES = int(os.environ.get("IMAGE_SPLITTER_MAX_REQUEST_BYTES", 18 * 1024 * 1024))
MAX_STORED_DOWNLOADS = int(os.environ.get("IMAGE_SPLITTER_MAX_STORED_DOWNLOADS", 24))
DOWNLOAD_ROOT = Path(
    os.environ.get("IMAGE_SPLITTER_DOWNLOAD_DIR", tempfile.gettempdir())
) / "image-splitter-downloads"
ALLOWED_IMAGE_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "image/heic",
    "image/heif",
}
DOWNLOADS: "OrderedDict[str, dict[str, object]]" = OrderedDict()


class RequestError(Exception):
    def __init__(self, public_message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        super().__init__(public_message)
        self.public_message = public_message
        self.status = status


def decode_data_url(data_url: str) -> bytes:
    if "," not in data_url or not data_url.startswith("data:"):
        raise RequestError("Upload a valid PNG, JPG, HEIC, WebP, or GIF image.")

    header, encoded = data_url.split(",", 1)
    mime_type = header[5:].split(";", 1)[0].lower()
    if mime_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise RequestError("Only PNG, JPG, HEIC, WebP, and GIF files are supported.")

    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise RequestError("Upload a valid PNG, JPG, HEIC, WebP, or GIF image.") from exc

    if len(decoded) > MAX_UPLOAD_BYTES:
        raise RequestError(
            f"Image is too large. Keep uploads under {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
            status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        )
    return decoded


def png_data_url(image_bytes: bytes) -> str:
    return f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}"


def public_error_message(exc: Exception) -> str:
    if isinstance(exc, RequestError):
        return exc.public_message

    message = str(exc).lower()
    if "cannot identify image file" in message:
        return "Upload a valid PNG, JPG, HEIC, WebP, or GIF image."
    if "decompressed data too large" in message:
        return "Image is too complex to process safely. Try a smaller file."
    return "Something went wrong while processing the image. Please try a different file or adjust the settings."


def cleanup_downloads() -> None:
    cutoff = time.time() - DOWNLOAD_TTL_SECONDS
    expired = [token for token, payload in DOWNLOADS.items() if float(payload["created_at"]) < cutoff]
    for token in expired:
        payload = DOWNLOADS.pop(token, None)
        if payload:
            path = payload.get("path")
            if isinstance(path, Path):
                path.unlink(missing_ok=True)

    while len(DOWNLOADS) > MAX_STORED_DOWNLOADS:
        _, payload = DOWNLOADS.popitem(last=False)
        path = payload.get("path")
        if isinstance(path, Path):
            path.unlink(missing_ok=True)


def make_zip_blob(manifest: dict, rendered_crops: list) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
        for rendered in rendered_crops:
            archive.writestr(rendered.file_name, encode_png_bytes(rendered.image))
    return buffer.getvalue()


def persist_download(blob: bytes, filename: str) -> str:
    cleanup_downloads()
    DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)

    token = secrets.token_urlsafe(12)
    zip_path = DOWNLOAD_ROOT / f"{token}.zip"
    zip_path.write_bytes(blob)
    DOWNLOADS[token] = {
        "path": zip_path,
        "filename": filename,
        "created_at": time.time(),
        "size_bytes": len(blob),
    }
    return token


class ImageSplitterHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class ImageSplitterHandler(BaseHTTPRequestHandler):
    server_version = "ImageSplitterHTTP/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self.serve_index()
            return
        if parsed.path == "/healthz":
            self.write_json({"ok": True, "status": "ready"})
            return
        if self.serve_static_file(parsed.path):
            return
        if parsed.path.startswith("/api/download/"):
            token = parsed.path.rsplit("/", 1)[-1]
            self.serve_download(token)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/preview":
            self.handle_preview()
            return
        if parsed.path == "/api/split":
            self.handle_split()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, format: str, *args) -> None:
        print(f"{self.address_string()} - {format % args}")

    def serve_index(self) -> None:
        content = INDEX_HTML.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def serve_static_file(self, path: str) -> bool:
        relative_path = path.lstrip("/") or path
        if not relative_path or relative_path.startswith("api/"):
            return False

        file_path = (WEB_ROOT / relative_path).resolve()
        try:
            file_path.relative_to(WEB_ROOT.resolve())
        except ValueError:
            return False

        if not file_path.is_file():
            return False

        suffix = file_path.suffix.lower()
        content_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".html": "text/html; charset=utf-8",
        }.get(suffix, "application/octet-stream")
        content = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)
        return True

    def serve_download(self, token: str) -> None:
        cleanup_downloads()
        payload = DOWNLOADS.get(token)
        if payload is None:
            self.send_error(HTTPStatus.NOT_FOUND, "Download expired or missing")
            return

        path = payload.get("path")
        if not isinstance(path, Path) or not path.is_file():
            DOWNLOADS.pop(token, None)
            self.send_error(HTTPStatus.NOT_FOUND, "Download expired or missing")
            return

        filename = payload["filename"]
        assert isinstance(filename, str)
        blob = path.read_bytes()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(blob)))
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(blob)

    def handle_preview(self) -> None:
        try:
            payload = self.read_json_payload()
            image_bytes = decode_data_url(str(payload["image_data_url"]))
            filename = str(payload.get("filename") or "upload.png")
            settings = payload.get("settings") or {}
            manifest, _, analysis = split_image_bytes(image_bytes, filename, "browser_preview", settings)
        except Exception as exc:
            status = exc.status if isinstance(exc, RequestError) else HTTPStatus.BAD_REQUEST
            self.write_json({"error": public_error_message(exc)}, status=status)
            return

        self.write_json(
            {
                "component_count": manifest["component_count"],
                "image_width": analysis.width,
                "image_height": analysis.height,
                "source_has_transparency": analysis.source_has_transparency,
                "settings": manifest["settings"],
                "components": manifest["components"],
            }
        )

    def handle_split(self) -> None:
        try:
            payload = self.read_json_payload()
            image_bytes = decode_data_url(str(payload["image_data_url"]))
            filename = str(payload.get("filename") or "upload.png")
            settings = payload.get("settings") or {}
            manifest, rendered_crops, _ = split_image_bytes(image_bytes, filename, "browser_output", settings)
        except Exception as exc:
            status = exc.status if isinstance(exc, RequestError) else HTTPStatus.BAD_REQUEST
            self.write_json({"error": public_error_message(exc)}, status=status)
            return

        zip_blob = make_zip_blob(manifest, rendered_crops)
        stem = Path(filename).stem or "split-icons"
        download_name = f"{stem}-split-icons.zip"
        token = persist_download(zip_blob, download_name)

        previews = []
        for rendered in rendered_crops:
            preview_bytes = encode_png_bytes(rendered.image)
            previews.append(
                {
                    "file": rendered.file_name,
                    "width": rendered.image.width,
                    "height": rendered.image.height,
                    "data_url": png_data_url(preview_bytes),
                }
            )

        self.write_json(
            {
                "manifest": manifest,
                "previews": previews,
                "download_url": f"/api/download/{token}",
                "download_name": download_name,
            }
        )

    def read_json_payload(self) -> dict:
        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            raise RequestError("Send requests as JSON.", status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise RequestError("Request body is empty.")
        if content_length > MAX_REQUEST_BYTES:
            raise RequestError(
                f"Request is too large. Keep uploads under {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
                status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            )
        body = self.rfile.read(content_length)
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise RequestError("Request body must be valid JSON.") from exc

    def write_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local browser MVP for the image splitter.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8008, help="Port to bind.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    server = ImageSplitterHTTPServer((args.host, args.port), ImageSplitterHandler)
    print(f"Serving image splitter UI at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        cleanup_downloads()


if __name__ == "__main__":
    main()
