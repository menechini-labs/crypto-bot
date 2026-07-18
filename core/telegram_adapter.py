"""Telegram Bot Adapter — envio de alerts e notificações via Telegram.

Usa apenas stdlib (urllib). Sem dependência externa.
Config via env: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)

_EMOJI_MAP = {
    'buy': '\uD83D\uDFE2',  # green
    'sell': '\uD83D\uDD34',  # red
    'hold': '\uD83D\uDFE1',  # yellow
    'alert': '\u26A0\uFE0F',  # warning
    'ok': '\u2705',
    'warn': '\u26A0\uFE0F',
}


def _token() -> str:
    return os.getenv('TELEGRAM_TOKEN', '')


def _chat_id() -> str:
    return os.getenv('TELEGRAM_CHAT_ID', '')


def is_configured() -> bool:
    """Verifica se TELEGRAM_TOKEN e TELEGRAM_CHAT_ID estão configurados."""
    return bool(_token()) and bool(_chat_id())


def _escape(text: str) -> str:
    """Escape MarkdownV2 special chars."""
    special = '_*[]()~`>#+-=|{}.!'
    for ch in special:
        text = text.replace(ch, f'\\{ch}')
    return text


def send(text: str, markdown: bool = True, parse_mode: str = 'MarkdownV2') -> bool:
    """Envia mensagem Telegram.

    Args:
        text: conteúdo da mensagem
        markdown: se True, aplica escape e parse_mode
        parse_mode: 'MarkdownV2' | 'HTML' | ''

    Returns:
        True se enviado com sucesso, False caso contrário.
    """
    tok = _token()
    cid = _chat_id()
    if not tok or not cid:
        log.debug('Telegram not configured: TELEGRAM_TOKEN=%s TELEGRAM_CHAT_ID=%s', bool(tok), bool(cid))
        return False

    if markdown and parse_mode == 'MarkdownV2':
        text = _escape(text)

    payload = {
        'chat_id': cid,
        'text': text,
        'parse_mode': parse_mode if markdown else '',
        'disable_web_page_preview': True,
    }

    url = f'https://api.telegram.org/bot{tok}/sendMessage'
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            if result.get('ok'):
                log.debug('Telegram sent: %s', text[:80])
                return True
            log.warning('Telegram API error: %s', result.get('description'))
            return False
    except Exception as e:
        log.warning('Telegram send failed: %s', e)
        return False


def send_signal(symbol: str, signal: str, confidence: float, price: float, reason: str) -> bool:
    """Atalho: envia alerta de sinal formatado."""
    emoji = _EMOJI_MAP.get(signal, '\u2753')
    text = (
        f'{emoji} *Signal Alert*\n'
        f'Symbol: {symbol}\n'
        f'Signal: {signal.upper()}\n'
        f'Confidence: {confidence:.0%}\n'
        f'Price: ${price:,.2f}\n'
        f'Reason: {reason}'
    )
    return send(text)


def send_alert(title: str, message: str, severity: str = 'info') -> bool:
    """Atalho: envia alerta genérico."""
    emoji = _EMOJI_MAP.get(severity, '\u2139\uFE0F')
    text = f'{emoji} *{title}*\n{message}'
    return send(text)
