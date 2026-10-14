"""Allowlisted, read-only checks. Never fetch a URL supplied by chat content."""

import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def diagnose(client_id):
    if client_id != "CLI-1001":
        return {"status": "unsupported", "detail": "Client belum dikonfigurasi"}
    url = os.environ.get("KOMANDO_CLI1001_HEALTH_URL", "")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.fragment or parsed.port not in (None, 443)):
        return {"status": "unconfigured", "detail": "Health URL HTTPS belum ditetapkan"}
    try:
        with build_opener(NoRedirect).open(Request(url, headers={"User-Agent": "KOMANDO-Health/1"}), timeout=5) as response:
            code = response.status
    except HTTPError as exc:
        code = exc.code
    except (URLError, TimeoutError, OSError):
        return {"status": "unreachable", "detail": "Endpoint tidak dapat dihubungi"}
    return {"status": "reachable" if code < 500 else "unhealthy",
            "detail": "HTTP %s; ini bukan bukti aliran WhatsApp/dashboard berfungsi" % code}