"""Access control and security headers of the dashboard."""

from __future__ import annotations

import base64
import binascii
import hmac
import ipaddress
import logging
from typing import Awaitable, Callable, Iterable

from aiohttp import web

from core.config import Settings

logger = logging.getLogger(__name__)

# Sent by app.js on every write. Browsers only allow custom headers on cross-origin requests after a
# CORS preflight, which this server never answers, so other sites can't change anything (CSRF).
CSRF_HEADER = 'X-Crafty-Bot'
SECURITY_HEADERS = {
    'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
                               "img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
    'Cache-Control': 'no-store',
}
PUBLIC_PATHS = {'/healthz'}

Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]


def password_matches(request: web.Request, password: str) -> bool:
    """Check the HTTP basic auth password of the request (the user name is ignored)."""
    scheme, _, encoded = request.headers.get('Authorization', '').partition(' ')
    if scheme.lower() != 'basic':
        return False
    try:
        credentials = base64.b64decode(encoded, validate=True).decode('utf-8')
    except (binascii.Error, UnicodeDecodeError):
        return False
    given = credentials.partition(':')[2]
    return hmac.compare_digest(given.encode('utf-8'), password.encode('utf-8'))


def host_allowed(host: str, allowed_hosts: Iterable[str]) -> bool:
    """Check whether the Host header names this machine (an IP address, localhost or WEB_ALLOWED_HOSTS)."""
    # Other names point to DNS rebinding, where a website the user visits makes its own domain
    # resolve to the dashboard to read it.
    hostname = host.lower()
    if hostname.startswith('['):  # [::1]:8080
        hostname = hostname[1:].partition(']')[0]
    elif hostname.count(':') == 1:
        hostname = hostname.partition(':')[0]
    if hostname in ('localhost', *allowed_hosts):
        return True
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        return False
    return True


def security_middleware(settings: Settings):
    """Middleware that enforces the password (or, without one, the Host check) and sets the security headers."""

    @web.middleware
    async def middleware(request: web.Request, handler: Handler) -> web.StreamResponse:
        if request.path in PUBLIC_PATHS:
            response = await _handle(request, handler)
        elif settings.web_password and not password_matches(request, settings.web_password):
            logger.debug('Unauthorized dashboard request from %s', request.remote)
            response = web.Response(status=401, text='Unauthorized',
                                    headers={'WWW-Authenticate': 'Basic realm="Crafty Bot"'})
        elif not settings.web_password and not host_allowed(request.host, settings.web_allowed_hosts):
            logger.warning('Rejected dashboard request for host %r from %s (add it to WEB_ALLOWED_HOSTS)',
                           request.host, request.remote)
            response = web.Response(status=403, text='Host not allowed')
        else:
            response = await _handle(request, handler)
        response.headers.update(SECURITY_HEADERS)
        return response

    return middleware


async def _handle(request: web.Request, handler: Handler) -> web.StreamResponse:
    try:
        return await handler(request)
    except web.HTTPException as exc:
        # 404, 405...: turn them into a normal response, so they get the security headers too.
        return web.Response(status=exc.status, reason=exc.reason, text=exc.text, headers=exc.headers)
