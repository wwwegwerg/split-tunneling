import base64
import errno
import hashlib
import http.client
import os
import shutil
import socket
import ssl
import sys
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import IO
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from rulesets.config import Config


class SafeRedirects(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: http.client.HTTPMessage,
        newurl: str,
    ) -> Request | None:
        if urlsplit(newurl).scheme != "https":
            raise ValueError("Refusing a non-HTTPS redirect")
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and urlsplit(req.full_url).netloc != urlsplit(newurl).netloc:
            redirected.remove_header("Authorization")
        return redirected


@dataclass(frozen=True)
class Download:
    name: str
    url: str
    path: Path
    authorization: str | None = None


def download_failure(error: OSError | http.client.HTTPException) -> tuple[str, bool]:
    """Return a safe reason and retry policy; raw messages may contain credentials."""
    if isinstance(error, HTTPError):
        return f"HTTP {error.code}", error.code in {408, 429, 500, 502, 503, 504}
    cause: object = error.reason if isinstance(error, URLError) else error
    if isinstance(cause, ssl.SSLCertVerificationError):
        return "TLS certificate verification failed", False
    if isinstance(cause, socket.gaierror):
        if cause.errno == socket.EAI_NONAME:
            return "DNS name not found", False
        if cause.errno == socket.EAI_AGAIN:
            return "temporary DNS failure", True
        return "DNS lookup failed", True
    if isinstance(cause, TimeoutError):
        return "timeout", True
    if isinstance(cause, ssl.SSLEOFError):
        return "TLS connection closed unexpectedly", True
    if isinstance(cause, ssl.SSLError):
        return "TLS connection failed", True
    if isinstance(cause, ConnectionError):
        return "connection failed", True
    if isinstance(cause, http.client.IncompleteRead):
        return "incomplete response", True
    if isinstance(cause, http.client.HTTPException):
        return "HTTP transport error", True
    if isinstance(cause, PermissionError):
        return "permission denied", False
    if isinstance(cause, (FileNotFoundError, NotADirectoryError, IsADirectoryError)):
        return "local path unavailable", False
    if isinstance(cause, OSError):
        if cause.errno in {errno.ENOSPC, errno.EDQUOT}:
            return "local storage exhausted", False
        if cause.errno == errno.EROFS:
            return "read-only filesystem", False
        if cause.errno == errno.EFBIG:
            return "file size limit exceeded", False
    return "network error", True


def download_file(task: Download) -> str:
    """Stream downloads with bounded retries; never log URLs containing credentials."""
    print(f"Downloading {task.name}", flush=True)
    headers = {"User-Agent": "split-tunneling-rules/0.1"}
    if task.authorization:
        headers["Authorization"] = task.authorization
    reason = "network error"
    for attempt in range(1, 4):
        started = time.perf_counter()
        try:
            with (
                build_opener(SafeRedirects()).open(
                    Request(task.url, headers=headers), timeout=60
                ) as response,
                task.path.open("wb") as target,
            ):
                length = response.headers.get("Content-Length")
                expected = int(length) if length is not None else None
                shutil.copyfileobj(response, target, length=1024 * 1024)
            actual = task.path.stat().st_size
            if expected is not None and actual != expected:
                raise http.client.IncompleteRead(b"", max(expected - actual, 0))
            if actual == 0:
                raise ValueError(f"{task.name}: empty download")
            with task.path.open("rb") as stream:
                return hashlib.file_digest(stream, "sha256").hexdigest()
        except (OSError, http.client.HTTPException) as error:
            reason, retryable = download_failure(error)
        retrying = retryable and attempt < 3
        elapsed = time.perf_counter() - started
        print(
            f"{task.name}: attempt {attempt}/3 failed after {elapsed:.2f}s ({reason}); "
            + ("retrying" if retrying else "no more retries"),
            file=sys.stderr,
            flush=True,
        )
        if not retrying:
            break
        time.sleep(2 ** (attempt - 1))
    raise ValueError(f"{task.name}: download failed ({reason})")


def fetch_inputs(config: Config, directory: Path) -> dict[str, str]:
    required = ("IPINFO_TOKEN", "MAXMIND_ACCOUNT_ID", "MAXMIND_LICENSE_KEY")
    missing = [name for name in required if not os.environ.get(name, "").strip()]
    if missing:
        raise ValueError("Missing secrets: " + ", ".join(missing))
    tasks = [
        Download(source.name, source.url, directory / source.name) for source in config.sources
    ]
    tasks.extend(
        [
            Download(
                "ipinfo.csv.gz",
                "https://ipinfo.io/data/ipinfo_lite.csv.gz?"
                + urlencode({"token": os.environ["IPINFO_TOKEN"]}),
                directory / "ipinfo.csv.gz",
            ),
            Download(
                "maxmind.tar.gz",
                "https://download.maxmind.com/geoip/databases/GeoLite2-Country/download"
                "?suffix=tar.gz",
                directory / "maxmind.tar.gz",
                "Basic "
                + base64.b64encode(
                    (
                        os.environ["MAXMIND_ACCOUNT_ID"] + ":" + os.environ["MAXMIND_LICENSE_KEY"]
                    ).encode()
                ).decode(),
            ),
        ]
    )
    with ThreadPoolExecutor(max_workers=8) as pool:
        hashes = dict(zip((t.name for t in tasks), pool.map(download_file, tasks), strict=True))
    extract_maxmind(directory)
    return hashes


def extract_maxmind(directory: Path) -> None:
    """Copy the Country database and its notices without extracting archive paths."""
    files = {
        "GeoLite2-Country.mmdb": "maxmind.mmdb",
        "COPYRIGHT.txt": "maxmind-COPYRIGHT.txt",
        "LICENSE.txt": "maxmind-LICENSE.txt",
    }
    with tarfile.open(directory / "maxmind.tar.gz", "r:gz") as archive:
        members = archive.getmembers()
        for name, destination in files.items():
            matches = [m for m in members if m.isfile() and Path(m.name).name == name]
            if len(matches) != 1:
                raise ValueError(f"MaxMind archive must contain exactly one {name}")
            source = archive.extractfile(matches[0])
            if source is None:
                raise ValueError(f"MaxMind archive has no readable {name}")
            with source, (directory / destination).open("wb") as target:
                shutil.copyfileobj(source, target)
