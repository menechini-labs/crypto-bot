import { useEffect, useState } from "react";
import { apiGet } from "./api";

function ReliabilityBadge({ sourceId, score }: { sourceId: string; score: number }) {
  const tone = score >= 0.7 ? 'pos' : score >= 0.5 ? 'warn' : 'neg';
  return (
    <span className={`rel-badge rel-badge--${tone}`} title={`source: ${sourceId}`}>
      <span className="rel-badge__dot" />{(score * 100).toFixed(0)}%
    </span>
  );
}

interface NewsItem {
  source: string;
  source_id: string;
  title: string;
  url: string;
  published: string;
  sentiment: "positive" | "negative" | "neutral";
  score: number;
  impact: boolean;
  symbols: string[];
}

interface NewsResponse {
  status: string;
  count: number;
  sentiment: { positive: number; negative: number; neutral: number };
  impact_headlines: NewsItem[];
  items: NewsItem[];
}

export default function NewsFeed() {
  const [data, setData] = useState<NewsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setData(await apiGet<NewsResponse>("/api/news?limit=40"));
      } catch (e) {
        setError(e instanceof Error ? e.message : "erro ao carregar notícias");
      }
    })();
  }, []);

  if (error)
    return (
      <div className="error" role="alert">
        {error}
      </div>
    );
  if (!data) return <div className="loading">Carregando notícias…</div>;

  const s = data.sentiment;
  return (
    <div className="news-feed">
      <div className="news-feed__head">
        <h2>News & Sentiment</h2>
        <div className="news-feed__sentiment">
          <span className="tag tag--pos">▲ {s.positive}</span>
          <span className="tag tag--neu">▬ {s.neutral}</span>
          <span className="tag tag--neg">▼ {s.negative}</span>
        </div>
      </div>

      {data.impact_headlines.length > 0 && (
        <div className="news-feed__impact">
          <h3>Alto impacto</h3>
          <ul>
            {data.impact_headlines.map((h, i) => (
              <li key={i}>
                <a href={h.url} target="_blank" rel="noreferrer">
                  {h.title}
                </a>
                <span className={`news-sent news-sent--${h.sentiment}`}>{h.sentiment}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <ul className="news-feed__list">
        {data.items.map((it, i) => (
          <li key={i} className="news-item">
            <div className="news-item__top">
              <span className="news-item__source">{it.source}</span>
              <ReliabilityBadge sourceId={it.source_id} score={it.score} />
              <span className={`news-item__sent news-item__sent--${it.sentiment}`}>
                {it.sentiment}
              </span>
              {it.impact && <span className="news-item__impact">IMPACTO</span>}
              {it.symbols.map((sym) => (
                <span key={sym} className="news-item__sym">
                  {sym}
                </span>
              ))}
            </div>
            <a className="news-item__title" href={it.url} target="_blank" rel="noreferrer">
              {it.title}
            </a>
            <span className="news-item__date muted">{it.published}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
