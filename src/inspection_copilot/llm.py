"""Claude API clients, created in one place.

TLS: the clients verify certificates against the operating system's trust store (via
`truststore`) instead of the certificate bundle shipped with Python packages. On machines
where antivirus or a corporate proxy inspects HTTPS (it re-signs traffic with its own root
certificate, which only the OS trusts), the default bundle fails with CERTIFICATE_VERIFY_FAILED.
In Linux containers the OS store is the normal system CA bundle, so behaviour is unchanged.
"""

import ssl
from functools import lru_cache

import anthropic
import truststore
from anthropic import DefaultAsyncHttpxClient, DefaultHttpxClient

from inspection_copilot.config import get_settings


class MissingApiKeyError(RuntimeError):
    pass


def _api_key() -> str:
    key = get_settings().anthropic_api_key
    if key is None or not key.get_secret_value():
        raise MissingApiKeyError("ANTHROPIC_API_KEY is not set (put it in .env)")
    return key.get_secret_value()


def _ssl_context() -> ssl.SSLContext:
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


@lru_cache
def get_client() -> anthropic.Anthropic:
    """Synchronous client, for scripts and evaluation runs."""
    return anthropic.Anthropic(
        api_key=_api_key(), http_client=DefaultHttpxClient(verify=_ssl_context())
    )


@lru_cache
def get_async_client() -> anthropic.AsyncAnthropic:
    """Async client, for the FastAPI service (does not block the event loop)."""
    return anthropic.AsyncAnthropic(
        api_key=_api_key(), http_client=DefaultAsyncHttpxClient(verify=_ssl_context())
    )
