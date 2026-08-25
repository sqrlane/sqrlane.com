"""httpget.py - a GET that is guaranteed to end, and one readable error line.

One job: talk to a third-party host we do not control without letting it hold
the run open. Both source families need it - the news pull in `risk_monitor.py`
and the structured public APIs in `signals.py` - so it lives on its own rather
than in either of them.

The failure mode that actually threatens a live demo is not a dead source. A
dead source fails fast. It is a source that is merely SLOW, and there are two
kinds:

  1. it hangs   - accepts the connection and never replies. A per-request
                  timeout catches this one.
  2. it trickles- replies forever, one byte at a time. `requests`' timeout is
                  measured BETWEEN BYTES, not in total, so a source sending one
                  byte a second never trips an eight-second timeout. The call
                  never returns and the thread running it never ends.

`get_capped` handles both: a total deadline enforced from outside the read, and
a hard ceiling on the body size.
"""

import socket
import threading

import requests

from src import config


class SourceTooSlow(requests.RequestException):
    """A source that is answering, but too slowly to be worth waiting for."""


def get_capped(url, *, timeout, params=None, headers=None):
    """A GET that is guaranteed to end.

    Two details here are load-bearing and easy to undo by accident:

      - Checking a deadline BETWEEN CHUNKS does not work. The read blocks until
        its chunk is full, so a trickling source never reaches the check. The
        socket has to be shut down from outside, which is what makes the blocked
        read raise.
      - `response.close()` alone does not unblock a read already in flight.
        `raw._connection.sock.shutdown()` does.
    """
    request_headers = {"User-Agent": config.USER_AGENT}
    if headers:
        request_headers.update(headers)
    response = requests.get(url, params=params, headers=request_headers,
                            timeout=timeout, stream=True)
    expired = []

    def _give_up():
        expired.append(True)
        sock = getattr(getattr(response.raw, "_connection", None), "sock", None)
        for stop in (lambda: sock.shutdown(socket.SHUT_RDWR), lambda: sock.close(),
                     response.raw.close):
            try:
                stop()
            except Exception:                    # noqa: BLE001
                pass

    watchdog = threading.Timer(timeout, _give_up)
    watchdog.daemon = True
    watchdog.start()
    try:
        response.raise_for_status()
        chunks, total = [], 0
        for chunk in response.iter_content(8192):
            chunks.append(chunk)
            total += len(chunk)
            if total > config.HTTP_MAX_BYTES or expired:
                break
        if expired:
            raise SourceTooSlow(f"still sending after {timeout:.0f}s - gave up")
        response._content = b"".join(chunks)     # so .json() and .content still work
        return response
    except Exception as exc:                     # noqa: BLE001
        # Deliberately broad, and only on the way out. Shutting the socket from
        # under a read in flight does not raise one predictable exception - the
        # trickle case surfaces as AttributeError from inside urllib3, which an
        # (OSError, RequestException) clause lets through raw. The point of this
        # function is that a slow source produces ONE READABLE LINE, so anything
        # raised after the watchdog fired is that line; anything else is re-raised
        # untouched for the caller to report.
        if expired:
            raise SourceTooSlow(f"still sending after {timeout:.0f}s - gave up") from exc
        raise
    finally:
        watchdog.cancel()
        response.close()


def short_error(exc, host_hint: str = "") -> str:
    """Turn a wall of urllib3 traceback text into one readable line.

    A demo operator needs to know WHICH source is down and roughly why, not the
    full connection-pool stack.
    """
    name = type(exc).__name__
    text = str(exc)
    if isinstance(exc, SourceTooSlow):
        return f"{text} ({host_hint or 'the source'})"
    if "Tunnel connection failed" in text or "ProxyError" in name or "ProxyError" in text:
        return f"blocked by network/proxy policy ({host_hint or 'host unreachable'})"
    if "NameResolution" in text or "getaddrinfo" in text:
        return f"DNS lookup failed ({host_hint})"
    if "timed out" in text.lower():
        # Not "after N seconds": the live budget shortens the per-request timeout
        # as it runs down, so the configured value is often not the one that was
        # actually waited, and printing it states a number that is not true.
        return f"timed out waiting for {host_hint or 'the source'}"
    # A refusal carries its status code and nothing else worth reading: the raw
    # text is the whole request URL again, which is a wall on a dashboard and
    # unreadable on a public page.
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status:
        return f"HTTP {status} from {host_hint or 'the source'}"
    return f"{name}: {text[:110]}"


def host_of(url: str) -> str:
    """The hostname, for an error line. Never raises on a malformed url."""
    try:
        return url.split("//", 1)[1].split("/", 1)[0]
    except IndexError:
        return url[:40]
