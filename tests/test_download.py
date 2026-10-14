import errno
import hashlib
import http.client
import io
import socket
import ssl
import tarfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.client import HTTPMessage
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

from rulesets.download import Download, SafeRedirects, download_file, extract_maxmind


def http_response(body: bytes, length: int) -> http.client.HTTPResponse:
    class FakeSocket:
        def makefile(self, mode: str) -> io.BytesIO:
            headers = f"HTTP/1.1 200 OK\r\nContent-Length: {length}\r\n\r\n".encode()
            return io.BytesIO(headers + body)

    response = http.client.HTTPResponse(FakeSocket())
    response.begin()
    return response


class DownloadTests(unittest.TestCase):
    def test_failure_policy_logs_safe_causes_attempts_and_duration(self) -> None:
        url = "https://example.test/data?token=probe-token"
        authorization = "Basic probe-authorization"
        sensitive = f"{url} Authorization: {authorization}"
        cases = [
            (
                URLError(ssl.SSLCertVerificationError(1, sensitive)),
                "TLS certificate verification failed",
                1,
                False,
            ),
            (
                URLError(socket.gaierror(socket.EAI_NONAME, sensitive)),
                "DNS name not found",
                1,
                False,
            ),
            (
                URLError(socket.gaierror(socket.EAI_AGAIN, sensitive)),
                "temporary DNS failure",
                3,
                False,
            ),
            (
                URLError(ssl.SSLEOFError(8, sensitive)),
                "TLS connection closed unexpectedly",
                3,
                False,
            ),
            (URLError(TimeoutError(sensitive)), "timeout", 3, False),
            (ConnectionResetError(errno.ECONNRESET, sensitive), "connection failed", 3, False),
            (HTTPError(url, 401, sensitive, HTTPMessage(), None), "HTTP 401", 1, False),
            (HTTPError(url, 503, sensitive, HTTPMessage(), None), "HTTP 503", 3, False),
            (URLError(sensitive), "network error", 3, False),
            (OSError(errno.ENOSPC, sensitive), "local storage exhausted", 1, True),
            (PermissionError(errno.EACCES, sensitive), "permission denied", 1, True),
        ]
        for error, reason, attempts, writing in cases:
            log = io.StringIO()
            with (
                self.subTest(reason=reason),
                TemporaryDirectory() as temporary,
                redirect_stdout(log),
                redirect_stderr(log),
                patch("rulesets.download.build_opener") as opener,
                patch("rulesets.download.shutil.copyfileobj") as copy,
                patch("rulesets.download.time.sleep") as sleep,
            ):
                if writing:
                    opener.return_value.open.return_value = http_response(b"data", 4)
                    copy.side_effect = error
                else:
                    opener.return_value.open.side_effect = error
                with self.assertRaises(ValueError) as failure:
                    download_file(
                        Download("probe-source", url, Path(temporary) / "data", authorization)
                    )
                self.assertEqual(opener.return_value.open.call_count, attempts)
                self.assertEqual(
                    [call.args[0] for call in sleep.call_args_list], [1, 2][: attempts - 1]
                )
                self.assertIn(reason, str(failure.exception))
                self.assertIsNone(failure.exception.__context__)
                for attempt in range(1, attempts + 1):
                    self.assertIn(f"probe-source: attempt {attempt}/3", log.getvalue())
                self.assertRegex(log.getvalue(), r"after \d+(?:\.\d+)?s")
                self.assertIn(reason, log.getvalue())
                for secret in (url, "probe-token", authorization):
                    self.assertNotIn(secret, str(failure.exception) + log.getvalue())

    def test_maxmind_preserves_notices_without_extracting_archive_paths(self) -> None:
        files = {
            "GeoLite2-Country.mmdb": b"database",
            "COPYRIGHT.txt": b"copyright notice\n",
            "LICENSE.txt": b"license terms\n",
        }
        with TemporaryDirectory() as temporary:
            directory = Path(temporary) / "inputs"
            directory.mkdir()
            with tarfile.open(directory / "maxmind.tar.gz", "w:gz") as archive:
                for name, data in files.items():
                    member = tarfile.TarInfo(f"../unexpected/{name}")
                    member.size = len(data)
                    archive.addfile(member, io.BytesIO(data))
            extract_maxmind(directory)
            for name, data in files.items():
                output = "maxmind.mmdb" if name.endswith(".mmdb") else f"maxmind-{name}"
                self.assertEqual((directory / output).read_bytes(), data)
            self.assertFalse((Path(temporary) / "unexpected").exists())

    def test_retry_replaces_partial_file_and_returns_complete_source_hash(self) -> None:
        body = b"complete source\n"
        with (
            TemporaryDirectory() as temporary,
            patch("rulesets.download.build_opener") as opener,
            patch("rulesets.download.time.sleep") as sleep,
        ):
            path = Path(temporary) / "data"
            opener.return_value.open.side_effect = [
                http_response(b"partial", 1000),
                http_response(body, len(body)),
            ]
            digest = download_file(Download("domains", "https://example.test/data", path))
            self.assertEqual(path.read_bytes(), body)
            self.assertEqual(digest, hashlib.sha256(body).hexdigest())
            self.assertEqual(opener.return_value.open.call_count, 2)
            sleep.assert_called_once_with(1)

    def test_cross_host_redirect_does_not_forward_database_credentials(self) -> None:
        request = Request(
            "https://download.example/database", headers={"Authorization": "Basic secret"}
        )
        response = SafeRedirects().redirect_request(
            request, io.BytesIO(), 302, "Found", HTTPMessage(), "https://storage.example/file"
        )
        self.assertIsNotNone(response)
        self.assertIsNone(response.get_header("Authorization"))
        with self.assertRaises(ValueError):
            SafeRedirects().redirect_request(
                request, io.BytesIO(), 302, "Found", HTTPMessage(), "http://storage.example/file"
            )
