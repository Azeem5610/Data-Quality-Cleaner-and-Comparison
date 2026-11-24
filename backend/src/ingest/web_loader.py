"""Raw website fetching. Returns the raw HTML and ALL visible text (menus, footers, etc.)."""

from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from src.ingest.errors import IngestError

REQUEST_TIMEOUT = 15  # seconds
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
USER_AGENT = (
    "Mozilla/5.0 (compatible; DataQualityDemo/0.1; +https://example.com/bot) "
    "AppleWebKit/537.36 (KHTML, like Gecko)"
)
NON_VISIBLE_TAGS = ["script", "style", "noscript", "template", "head"]


def validate_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        raise IngestError("Please enter a URL.")
    if "://" not in url:
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or "." not in parsed.netloc:
        raise IngestError("That doesn't look like a valid http(s) URL.")
    return url


def fetch_html(url: str) -> str:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
            timeout=REQUEST_TIMEOUT,
            stream=True,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise IngestError("The website took too long to respond.", 504)
    except requests.exceptions.ConnectionError:
        raise IngestError("Could not connect to that website. Check the URL and your network.", 502)
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        raise IngestError(f"The website returned an error (HTTP {status}).", 502)
    except requests.exceptions.RequestException:
        raise IngestError("Failed to fetch that URL.", 502)

    content_type = response.headers.get("Content-Type", "").lower()
    if content_type and "html" not in content_type and "xml" not in content_type:
        response.close()
        raise IngestError(f"That URL is not a web page (content type: {content_type}).")

    content = b""
    for chunk in response.iter_content(chunk_size=65536):
        content += chunk
        if len(content) > MAX_BYTES:
            response.close()
            raise IngestError("That page is too large to process (over 5 MB).")

    # requests defaults to ISO-8859-1 when no charset is declared; prefer detection then.
    encoding = response.encoding
    if not encoding or encoding.lower() == "iso-8859-1":
        encoding = response.apparent_encoding or "utf-8"
    try:
        return content.decode(encoding, errors="replace")
    except LookupError:
        return content.decode("utf-8", errors="replace")


def html_to_visible_text(html: str) -> str:
    """Naive visible-text extraction: keeps nav, cookie banners, footers, everything."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(NON_VISIBLE_TAGS):
        tag.decompose()
    lines = (line.strip() for line in soup.get_text(separator="\n").splitlines())
    return "\n".join(line for line in lines if line)


def load_web(url: str) -> tuple[str, str, str]:
    """Return (normalized_url, raw_html, raw_text)."""
    url = validate_url(url)
    html = fetch_html(url)
    text = html_to_visible_text(html)
    if not text.strip():
        raise IngestError(
            "No visible text found on that page. It may be rendered with JavaScript, "
            "which this demo does not execute."
        )
    return url, html, text