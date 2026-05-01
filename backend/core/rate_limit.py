"""Configuração do SlowAPI para rate-limiting nas rotas.

Funciona por IP do cliente. Limites mais estritos em /auth/login
e /ocr/plate (caro).
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
    headers_enabled=False,
)
