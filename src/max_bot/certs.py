import time
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen

CERT_URLS: dict[str, str] = {
    "russian_trusted_root_ca.crt": "https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt",
    "russian_trusted_sub_ca.crt": "https://gu-st.ru/content/lending/russian_trusted_sub_ca_pem.crt",
}

CERTS_DIR = Path(__file__).resolve().parent.parent.parent / "etc" / "max_api" / "certs"

_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MaxSmartCity-cert-fetch/1.0)",
    "Accept": "*/*",
}
_MAX_ATTEMPTS = 3
_RETRY_DELAY_SECONDS = 1.0


class CertFetchError(RuntimeError):
    """Raised when a downloaded file doesn't look like a PEM certificate."""


@dataclass(frozen=True, slots=True)
class FetchedCert:
    filename: str
    path: Path


def _fetch(url: str) -> bytes:
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            request = Request(url, headers=_REQUEST_HEADERS)
            with urlopen(request, timeout=10) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            if attempt == _MAX_ATTEMPTS:
                raise OSError(str(exc)) from exc
            time.sleep(_RETRY_DELAY_SECONDS)
    raise AssertionError("unreachable")


def fetch_russian_trusted_ca_certs(target_dir: Path = CERTS_DIR) -> list[FetchedCert]:
    target_dir.mkdir(parents=True, exist_ok=True)
    fetched = []
    for filename, url in CERT_URLS.items():
        try:
            data = _fetch(url)
        except OSError as exc:
            raise CertFetchError(
                f"Could not download {url} after {_MAX_ATTEMPTS} attempts ({exc}). This is usually a "
                "VPN/proxy or antivirus intercepting the TLS handshake to gu-st.ru - try again with it "
                "disabled, or download the file in a browser and save it to "
                f"{target_dir / filename}."
            ) from exc
        if b"BEGIN CERTIFICATE" not in data:
            raise CertFetchError(f"Unexpected response from {url}: does not look like a PEM certificate")
        path = target_dir / filename
        path.write_bytes(data)
        fetched.append(FetchedCert(filename=filename, path=path))
    return fetched
