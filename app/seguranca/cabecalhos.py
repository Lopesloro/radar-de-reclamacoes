"""Cabeçalhos de defesa que saem em toda resposta."""

from __future__ import annotations

# O CSS e a fonte do Google são as únicas coisas de fora; um teste confere que a lista acompanha os templates.
_CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data:",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "base-uri 'none'",
    "object-src 'none'",
])

CABECALHOS = {
    "Content-Security-Policy": _CSP,
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}
