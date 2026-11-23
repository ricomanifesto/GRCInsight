"""Bounded text reads, restricted to public HTTP(S) destinations."""

import asyncio
import ipaddress
import socket

import httpx

MAX_REDIRECTS = 3
_IPV6_UNICAST = ipaddress.IPv6Network("2000::/3")


def _public_address(value: str) -> str:
    address = ipaddress.ip_address(value)
    if (
        not address.is_global
        or address.is_multicast
        or address.is_reserved
        or (
            isinstance(address, ipaddress.IPv6Address)
            and (
                address not in _IPV6_UNICAST
                or address.sixtofour is not None
                or address.teredo is not None
                or address.scope_id is not None
            )
        )
    ):
        raise ValueError("Destination address is not public unicast")
    return str(address)


async def _destination(url: httpx.URL) -> str:
    default_port = {"http": 80, "https": 443}.get(url.scheme)
    if (
        default_port is None
        or not url.is_absolute_url
        or not url.host
        or url.userinfo
        or url.port not in (None, default_port)
        or "%" in url.host
    ):
        raise ValueError("Unsupported public destination")

    host = url.raw_host.decode("ascii")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        results = await asyncio.get_running_loop().getaddrinfo(
            host, default_port, type=socket.SOCK_STREAM
        )
        # Reject mixed public/private answers rather than selecting a convenient answer.
        addresses = [_public_address(str(result[4][0])) for result in results]
        if not addresses:
            raise ValueError("Destination has no public address")
        # Lambda deployments may lack IPv6 egress; prefer IPv4 for dual-stack publishers.
        addresses.sort(key=lambda address: ":" in address)
        return addresses[0]
    return _public_address(host)


async def fetch_public_text(url: str, *, max_bytes: int, timeout: float) -> tuple[str, bool]:
    """Return bounded text and a truncation flag after checking every destination."""
    current = httpx.URL(url)
    # Includes DNS, all redirects, headers and reading, not just each socket operation.
    async with asyncio.timeout(timeout):
        for hop in range(MAX_REDIRECTS + 1):
            # A fresh client per hop prevents cookie and TLS connection reuse between hosts.
            async with httpx.AsyncClient(
                follow_redirects=False,
                trust_env=False,
                timeout=timeout,
                limits=httpx.Limits(max_keepalive_connections=0),
            ) as client:
                address = await _destination(current)
                async with client.stream(
                    "GET",
                    current.copy_with(host=address, fragment=None),
                    headers={"Host": current.netloc.decode("ascii"), "Accept-Encoding": "identity"},
                    extensions={"sni_hostname": current.raw_host.decode("ascii")},
                ) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location or hop == MAX_REDIRECTS:
                            raise ValueError("Redirect limit or missing destination")
                        # Resolve relative locations against the original hostname, not the IP.
                        current = current.join(location)
                        continue
                    if response.status_code != 200:
                        raise ValueError("Destination did not return content")
                    if response.headers.get("content-encoding", "identity").lower() != "identity":
                        raise ValueError("Compressed content is unsupported")

                    body = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=4096):
                        body.extend(chunk[: max_bytes + 1 - len(body)])
                        if len(body) > max_bytes:
                            break
                    text = bytes(body[:max_bytes]).decode(
                        response.encoding or "utf-8", errors="replace"
                    )
                    return text, len(body) > max_bytes
    raise ValueError("Redirect limit exceeded")
