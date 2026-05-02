"""OpenSearch client factory with basic-auth, retries, and sane timeouts."""

from __future__ import annotations

from urllib.parse import urlparse

from opensearchpy import OpenSearch, RequestsHttpConnection

from .config import Config


def make_client(cfg: Config) -> OpenSearch:
    parsed = urlparse(cfg.opensearch_url)
    use_ssl = parsed.scheme == "https"
    port = parsed.port or (443 if use_ssl else 80)
    return OpenSearch(
        hosts=[{"host": parsed.hostname, "port": port}],
        http_auth=(cfg.opensearch_user, cfg.opensearch_password),
        use_ssl=use_ssl,
        verify_certs=use_ssl,
        ssl_show_warn=False,
        connection_class=RequestsHttpConnection,
        timeout=120,
        max_retries=5,
        retry_on_timeout=True,
    )
