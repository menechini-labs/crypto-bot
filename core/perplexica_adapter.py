"""Perplexica Search Adapter — busca web para contexto de trading.

Usa DuckDuckGo HTML scraping (stdlib, sem API key) como fallback
 quando Perplexica API não está disponível.

Ideal para enriquecer NewsAgent com contexto adicional de busca.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

_PERPLEXICA_BASE = 'http://localhost:3001'
_PERSEVERANCE_SECS = 3  # timeout curto — busca é complementar


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str = 'perplexica'
    fetched_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            'title': self.title,
            'url': self.url,
            'snippet': self.snippet,
            'source': self.source,
            'fetched_at': self.fetched_at,
        }


def _ddg_search(query: str, max_results: int = 3) -> list[SearchResult]:
    """Fallback: scrape DuckDuckGo HTML results (stdlib only)."""
    url = 'https://html.duckduckgo.com/html/?q=' + urllib.parse.quote(query)
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (compatible; cryptobot/0.1)',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_PERSEVERANCE_SECS) as resp:
            html = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        log.warning('ddg_search failed: %s', e)
        return []

    results: list[SearchResult] = []
    # Parse minimal: extract result blocks
    for block in html.split('<div class="result__body')[1:]:
        title = ''
        snippet = ''
        url_link = ''

        # Title
        tidx = block.find('class="result__title"')
        if tidx > 0:
            from_ = block.find('>', tidx)
            to_ = block.find('</a>', from_)
            title = block[from_ + 1:to_]
            # Extract actual URL from href
            hstart = block.find('href="', tidx)
            if hstart > 0:
                hstart += 6
                hend = block.find('"', hstart)
                url_link = block[hstart:hend]
                url_link = urllib.parse.unquote(url_link.split('uddg=')[-1] if 'uddg=' in url_link else url_link)

        # Snippet
        sidx = block.find('class="result__snippet"')
        if sidx > 0:
            sfrom = block.find('>', sidx)
            sto = block.find('</a>', sfrom)
            snippet = block[sfrom + 1:sto] if sto > 0 else block[sfrom + 1:sfrom + 200]

        results.append(
            SearchResult(
                title=title.strip(),
                url=url_link.strip(),
                snippet=snippet.strip(),
                source='duckduckgo',
            )
        )
        if len(results) >= max_results:
            break

    return results


def search(query: str, max_results: int = 3) -> list[SearchResult]:
    """Busca contexto de trading. Tenta Perplexica, fallback DuckDuckGo.

    Args:
        query: texto da busca (ex: 'BTC regulation news today')
        max_results: máx resultados (default 3)

    Returns:
        Lista de SearchResult ordenada por relevância.
    """
    # Tenta Perplexica
    try:
        payload = json.dumps(
            {
                'query': query,
                'model': 'gpt-3.5-turbo',
                'focus': 'web',
            }
        ).encode()
        req = urllib.request.Request(
            f'{_PERPLEXICA_BASE}/api/search',
            data=payload,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'crypto-bot/0.1',
            },
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=_PERSEVERANCE_SECS) as resp:
            data = json.loads(resp.read().decode())
            raw_results = data.get('results', []) if isinstance(data, dict) else data
            return [
                SearchResult(
                    title=r.get('title', ''),
                    url=r.get('url', ''),
                    snippet=r.get('content', r.get('snippet', '')),
                    source='perplexica',
                )
                for r in raw_results[:max_results]
            ]
    except Exception as e:
        log.debug('Perplexica unavailable (%s), fallback DDG', e)

    return _ddg_search(query, max_results=max_results)


def search_crypto_news(symbol: str = 'BTC', max_results: int = 3) -> list[SearchResult]:
    """Atalho: busca notícias específicas de um symbol."""
    return search(f'{symbol} crypto news today', max_results=max_results)
