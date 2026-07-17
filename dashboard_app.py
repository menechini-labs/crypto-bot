#!/usr/bin/env python3
"""
Dashboard Streamlit para visualizar resultados do backtest / walk-forward.

Le os arquivos gerados pelo run_backtest.py:
  - report.json       (backtest simples)
  - walkforward.json  (walk-forward validation)

Execucao:  streamlit run dashboard_app.py
"""
from __future__ import annotations

import json
import pathlib

import pandas as pd
import streamlit as st

HERE = pathlib.Path(__file__).parent


@st.cache_data
def load_json(name: str):
    p = HERE / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def main() -> None:
    st.set_page_config(page_title="Crypto-Bot Scoring Dashboard", layout="wide")
    st.title("📊 Crypto-Bot — Scoring & Backtest Dashboard")

    tab1, tab2 = st.tabs(["Backtest", "Walk-Forward"])

    # ---- Tab 1: Backtest simples ----
    with tab1:
        data = load_json("report.json")
        if not data:
            st.warning("report.json nao encontrado. Rode: `python3 run_backtest.py`")
        else:
            summary = data.get("summary", {})
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Ciclos", summary.get("total_cycles", 0))
            c2.metric("Win Rate", f"{summary.get('win_rate_pct', 0)}%")
            c3.metric("Retorno Total", f"{summary.get('total_return_pct', 0)}%")
            c4.metric("Sharpe (aprox)", summary.get("sharpe_approx", 0))

            last = data.get("last_cycle")
            if last:
                st.subheader("Ultimo Ciclo — Score Breakdown")
                score = last.get("score", {})
                det = score.get("details", {})
                comp = det.get("components", {})
                df_comp = pd.DataFrame(
                    [(k, v) for k, v in comp.items()],
                    columns=["Componente", "Score (0-1)"],
                )
                st.bar_chart(df_comp.set_index("Componente"))
                st.json(score)

    # ---- Tab 2: Walk-Forward ----
    with tab2:
        wf = load_json("walkforward.json")
        if not wf:
            st.warning("walkforward.json nao encontrado. Rode: `python3 run_backtest.py --walk-forward`")
        else:
            st.metric("Folds", wf.get("folds", 0))
            st.metric("Retorno medio / fold", f"{wf.get('avg_return_per_fold', 0)}%")
            st.metric("Win Rate medio", f"{wf.get('avg_win_rate', 0)}%")

            equity = wf.get("equity_curve", [])
            if equity:
                st.subheader("Curva de Equity (Walk-Forward)")
                eq_df = pd.DataFrame({"fold": list(range(1, len(equity) + 1)), "equity_pct": equity})
                st.line_chart(eq_df.set_index("fold"))

            per_fold = wf.get("per_fold", [])
            if per_fold:
                st.subheader("Detalhe por Fold")
                fold_df = pd.DataFrame(per_fold)
                fold_df.insert(0, "fold", list(range(1, len(per_fold) + 1)))
                st.dataframe(fold_df, use_container_width=True)


if __name__ == "__main__":
    main()
