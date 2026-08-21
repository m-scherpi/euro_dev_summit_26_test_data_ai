"""Minimal OpenSearch REST client over the Python standard library.

Deliberately tiny and deliberately shared between the indexer and the verifier:
it carries HTTP, basic authentication and TLS trust, and nothing else. No
coordinate handling, no document shaping, no axis order. Those live in
`index_stations.py` and are re-derived independently in `verify_index.py`,
because a verifier that imports the generator's geometry code only proves that
the code agrees with itself (CLAUDE.md section 4).

Why stdlib instead of `opensearch-py`: this use case has to come up on a bare
VM with nothing but a Python interpreter. `urllib` speaks HTTPS against a
private CA if you hand it a CA file, which is exactly what the demo TLS
certificates of a local cluster need.
"""

from __future__ import annotations

import base64
import json
import ssl
import urllib.error
import urllib.request

# The security demo configuration ships one admin user. `admin/admin` stopped
# working in OpenSearch 2.12: the demo installer runs the password through a
# strength check and rejects it. The password below is committed on purpose -
# see the README section on credentials.
DEFAULT_USER = "admin"
DEFAULT_PASSWORD = "DevSummit#2026!os"
DEFAULT_HOST = "https://localhost:9200"


class OpenSearchError(RuntimeError):
    """An OpenSearch request failed. Carries status and response body."""

    def __init__(self, status: int, body: str, url: str) -> None:
        super().__init__(f"{status} from {url}: {body[:800]}")
        self.status = status
        self.body = body
        self.url = url


class OpenSearchClient:
    """Just enough client for creating an index, bulk loading and searching."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        user: str | None = DEFAULT_USER,
        password: str | None = DEFAULT_PASSWORD,
        ca_cert: str | None = None,
        verify_tls: bool = True,
        timeout: float = 60.0,
    ) -> None:
        self.host = host.rstrip("/")
        self.timeout = timeout
        self._headers = {"Content-Type": "application/json"}
        if user:
            token = base64.b64encode(f"{user}:{password or ''}".encode()).decode()
            self._headers["Authorization"] = f"Basic {token}"

        self._ssl_context: ssl.SSLContext | None = None
        if self.host.startswith("https://"):
            if verify_tls:
                # A local cluster runs on a private CA, so trusting the system
                # store is not enough - the caller has to name the CA file.
                self._ssl_context = ssl.create_default_context(cafile=ca_cert)
            else:
                self._ssl_context = ssl.create_default_context()
                self._ssl_context.check_hostname = False
                self._ssl_context.verify_mode = ssl.CERT_NONE

    def request(
        self,
        method: str,
        path: str,
        body: str | bytes | None = None,
        content_type: str | None = None,
    ) -> dict:
        """Send one request and return the decoded JSON response."""
        url = f"{self.host}/{path.lstrip('/')}"
        data = body.encode() if isinstance(body, str) else body
        headers = dict(self._headers)
        if content_type:
            headers["Content-Type"] = content_type
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(
                req, timeout=self.timeout, context=self._ssl_context
            ) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:  # 4xx/5xx carry a useful body
            raise OpenSearchError(
                exc.code, exc.read().decode("utf-8", "replace"), url
            ) from None
        except urllib.error.URLError as exc:
            raise OpenSearchError(0, f"{exc.reason}", url) from None
        return json.loads(raw) if raw else {}

    # -- convenience wrappers ------------------------------------------------

    def info(self) -> dict:
        return self.request("GET", "/")

    def index_exists(self, index: str) -> bool:
        try:
            self.request("GET", f"/{index}")
        except OpenSearchError as exc:
            if exc.status == 404:
                return False
            raise
        return True

    def delete_index(self, index: str) -> None:
        self.request("DELETE", f"/{index}")

    def create_index(self, index: str, definition: dict) -> dict:
        return self.request("PUT", f"/{index}", json.dumps(definition))

    def get_mapping(self, index: str) -> dict:
        return self.request("GET", f"/{index}/_mapping")

    def bulk(self, ndjson: str) -> dict:
        # The bulk endpoint insists on its own content type and a trailing newline.
        if not ndjson.endswith("\n"):
            ndjson += "\n"
        return self.request(
            "POST", "/_bulk", ndjson, content_type="application/x-ndjson"
        )

    def refresh(self, index: str) -> dict:
        return self.request("POST", f"/{index}/_refresh")

    def count(self, index: str, query: dict | None = None) -> int:
        body = json.dumps({"query": query}) if query else None
        return int(self.request("POST", f"/{index}/_count", body)["count"])

    def search(self, index: str, body: dict) -> dict:
        return self.request("POST", f"/{index}/_search", json.dumps(body))
