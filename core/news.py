"""News agent — aggregated crypto headlines via free, no-auth RSS feeds.

Fetches CoinDesk + Cointelegraph RSS, parses titles/dates, applies a
lightweight keyword-based sentiment + impact tag. No API key required.
Paper-only product; news is informational signal, never executed directly.
"""

from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

logger = None  # lazy import to avoid noise at import time

NEWS_FEEDS = [
    {
        'id': 'coindesk',
        'name': 'CoinDesk',
        'url': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
    },
    {'id': 'cointelegraph', 'name': 'Cointelegraph', 'url': 'https://cointelegraph.com/rss'},
]

# Sentiment lexicon (simple, English). Positive / negative weight words.
POSITIVE = [
    'surge',
    'rally',
    'gain',
    'gains',
    'soar',
    'soars',
    'jump',
    'jumps',
    'bull',
    'bullish',
    'breakout',
    'record',
    'high',
    'adoption',
    'approval',
    'approved',
    'upgrade',
    'optimistic',
    'recovery',
    'pump',
    'moon',
    'buy',
    'profit',
    'profits',
]
NEGATIVE = [
    'crash',
    'plunge',
    'drop',
    'drops',
    'fall',
    'falls',
    'bear',
    'bearish',
    'hack',
    'hacked',
    'exploit',
    'scam',
    'fraud',
    'ban',
    'banned',
    'lawsuit',
    'sec',
    'fed',
    'dump',
    'sell-off',
    'selloff',
    'loss',
    'losses',
    'collapse',
    'fear',
    'warning',
    'warn',
    'downgrade',
    'liquidation',
    'liquidated',
    'default',
    'bankrupt',
    'fud',
]
# Impact: mentions of major assets or macro events raise impact flag.
HIGH_IMPACT = [
    'bitcoin',
    'btc',
    'ethereum',
    'eth',
    'sec',
    'fed',
    'federal reserve',
    'inflation',
    'gdp',
    'interest rate',
    'rate hike',
    'etf',
    'halving',
    'binance',
    'coinbase',
    'regulation',
]


@dataclass
class NewsItem:
    source: str
    title: str
    url: str
    published: str
    sentiment: str  # "positive" | "negative" | "neutral"
    score: float
    impact: bool
    symbols: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'source': self.source,
            'title': self.title,
            'url': self.url,
            'published': self.published,
            'sentiment': self.sentiment,
            'score': round(self.score, 3),
            'impact': self.impact,
            'symbols': self.symbols,
        }


_SYMBOL_RE = re.compile(r'\b(BTC|ETH|SOL|BNB|ADA|XRP|DOGE|USDT)\b', re.I)


def _strip_tags(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text)
    return html.unescape(text).strip()


def _sentiment_of(title: str) -> tuple[str, float, bool]:
    t = title.lower()
    pos = sum(t.count(w) for w in POSITIVE)
    neg = sum(t.count(w) for w in NEGATIVE)
    score = (pos - neg) / max(1, (pos + neg))
    if pos > neg:
        sent = 'positive'
    elif neg > pos:
        sent = 'negative'
    else:
        sent = 'neutral'
    impact = any(w in t for w in HIGH_IMPACT)
    return sent, score, impact


def _fetch_feed(feed: dict, limit: int = 15, timeout: int = 8) -> list[NewsItem]:
    out: list[NewsItem] = []
    try:
        req = urllib.request.Request(feed['url'], headers={'User-Agent': 'Mozilla/5.0'})
        raw = urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', 'ignore')
        root = ET.fromstring(raw)
        for item in root.iter('item'):
            title_el = item.findtext('title') or ''
            link_el = item.findtext('link') or ''
            pub_el = item.findtext('pubDate') or ''
            title = _strip_tags(title_el)
            if not title:
                continue
            sent, score, impact = _sentiment_of(title)
            symbols = sorted({m.group(0).upper() for m in _SYMBOL_RE.finditer(title)})
            out.append(
                NewsItem(
                    source=feed['name'],
                    title=title,
                    url=link_el.strip(),
                    published=pub_el,
                    sentiment=sent,
                    score=score,
                    impact=impact,
                    symbols=symbols,
                )
            )
            if len(out) >= limit:
                break
    except (urllib.error.URLError, ET.ParseError, ValueError) as e:
        # Log but never crash the agent cycle on a single feed failure.
        try:
            import logging

            logging.getLogger('crypto-bot').warning('news feed %s failed: %s', feed['id'], e)
        except Exception:
            pass
    return out


def fetch_news(per_feed: int = 15, sources: list[str] | None = None) -> list[NewsItem]:
    """Fetch aggregated news across configured free RSS feeds.

    Returns a merged, recency-preserved list of NewsItem (newest first when
    parsable, else feed order). Tolerant to individual feed failures.
    """
    items: list[NewsItem] = []
    for feed in NEWS_FEEDS:
        if sources and feed['id'] not in sources:
            continue
        items.extend(_fetch_feed(feed, limit=per_feed))
    # Best-effort sort by published date (RFC822). Fallback: keep order.
    try:
        from email.utils import parsedate_to_datetime

        def _key(it: NewsItem):
            try:
                return parsedate_to_datetime(it.published).timestamp()
            except Exception:
                return 0.0

        items.sort(key=_key, reverse=True)
    except Exception:
        pass
    return items


def news_summary(limit: int = 30) -> dict:
    items = fetch_news(per_feed=15)
    items = items[:limit]
    pos = sum(1 for i in items if i.sentiment == 'positive')
    neg = sum(1 for i in items if i.sentiment == 'negative')
    neu = sum(1 for i in items if i.sentiment == 'neutral')
    impact = [i.to_dict() for i in items if i.impact][:10]
    return {
        'status': 'ok',
        'count': len(items),
        'sentiment': {'positive': pos, 'negative': neg, 'neutral': neu},
        'impact_headlines': impact,
        'items': [i.to_dict() for i in items],
    }
