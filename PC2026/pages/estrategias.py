"""
Pagina: Estrategias BDM — gestión y visualización de estrategias por cuenta.
Vista centrada en los ejecutivos y sus planes de acción.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.data_model import DashboardData


def render(data: DashboardData):
    df = data.master

    # Detectar columnas de estrategia
    strat_col = None
    pasos_col = None
    for c in df.columns:
        if c.lower().strip() == "estrategia":
            strat_col = c
        if "pasos" in c.lower():
            pasos_col = c

    # --- Selector de ejecutivo ---
    bdm_options = ["Todos"] + data.bdm_names
    selected_bdm = st.selectbox("Ejecutivo / BDM", bdm_options, key="strat_bdm")

    filtered = df if selected_bdm == "Todos" else df[df[data.col_comercial] == selected_bdm]

    # --- KPIs ---
    total = len(filtered)
    with_strat = filtered[strat_col].notna().sum() if strat_col else 0
    with_pasos = filtered[pasos_col].notna().sum() if pasos_col else 0
    pct_strat = int(with_strat / max(total, 1) * 100)
    pct_pasos = int(with_pasos / max(total, 1) * 100)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Cuentas", total)
    k2.metric("Con Estrategia", f"{with_strat} ({pct_strat}%)")
    k3.metric("Con Pasos Definidos", f"{with_pasos} ({pct_pasos}%)")
    avg_score = filtered["score_heatmap"].mean() if "score_heatmap" in filtered.columns else 0
    k4.metric("Score Prom. Heatmap", f"{avg_score:.1f}")

    st.divider()

    # --- Cobertura de estrategias por BDM ---
    if selected_bdm == "Todos" and strat_col:
        st.subheader("Cobertura de Estrategias por Ejecutivo")
        strat_by_bdm = (
            df.groupby(data.col_comercial)
            .agg(
                Total=(data.col_cliente, "count"),
                Con_Estrategia=(strat_col, lambda x: x.notna().sum()),
            )
            .reset_index()
        )
        strat_by_bdm["Sin_Estrategia"] = strat_by_bdm["Total"] - strat_by_bdm["Con_Estrategia"]
        strat_by_bdm["Pct"] = (strat_by_bdm["Con_Estrategia"] / strat_by_bdm["Total"] * 100).round(0)

        fig = px.bar(
            strat_by_bdm.sort_values("Total", ascending=True),
            x=["Con_Estrategia", "Sin_Estrategia"],
            y=data.col_comercial,
            orientation="h",
            color_discrete_map={"Con_Estrategia": "#92d050", "Sin_Estrategia": "#d9d9d9"},
            labels={"value": "Cuentas", "variable": ""},
        )
        fig.update_layout(
            height=max(350, len(strat_by_bdm) * 30),
            yaxis=dict(categoryorder="total ascending"),
            barmode="stack",
        )
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

    # --- Lista de cuentas con estrategias ---
    st.subheader("Estrategias por Cuenta")

    # Filtro adicional
    show_mode = st.radio(
        "Mostrar",
        ["Todas", "Con estrategia", "Sin estrategia"],
        horizontal=True,
        key="strat_filter",
    )

    if strat_col:
        if show_mode == "Con estrategia":
            filtered = filtered[filtered[strat_col].notna()]
        elif show_mode == "Sin estrategia":
            filtered = filtered[filtered[strat_col].isna()]

    # Ordenar por score
    filtered = filtered.sort_values("score_heatmap", ascending=False)

    # Mostrar tarjetas de estrategia
    for _, row in filtered.iterrows():
        cliente = row.get(data.col_cliente, "?")
        if pd.isna(cliente):
            continue

        with st.expander(
            f"**{cliente}** — {row.get(data.col_sector, '')} | "
            f"Score: {int(row.get('score_heatmap', 0))} | "
            f"{row.get(data.col_tipo, '')}",
            expanded=False,
        ):
            ic1, ic2, ic3, ic4 = st.columns(4)
            ic1.write(f"**Ejecutivo:** {row.get(data.col_comercial, '-')}")
            ic2.write(f"**Zona:** {row.get(data.col_zona, '-')}")
            ic3.write(f"**Score:** {int(row.get('score_heatmap', 0))}")
            ic4.write(f"**Cobertura:** {int(row.get('cobertura_productos', 0))} soluciones")

            strat_text = row.get(strat_col) if strat_col else None
            pasos_text = row.get(pasos_col) if pasos_col else None

            col_s, col_p = st.columns(2)
            with col_s:
                st.write("**📌 Estrategia:**")
                if not pd.isna(strat_text) and strat_text:
                    st.write(str(strat_text))
                else:
                    st.caption("_Sin estrategia definida_")

            with col_p:
                st.write("**🎯 Pasos a seguir:**")
                if not pd.isna(pasos_text) and pasos_text:
                    st.write(str(pasos_text))
                else:
                    st.caption("_Sin pasos definidos_")

            # Productos activos
            active = []
            for p in data.heatmap_all_cols:
                if p in df.columns and not pd.isna(row.get(p)) and int(row.get(p, 0)) > 0:
                    active.append(p)
            if active:
                st.write(f"**Soluciones activas ({len(active)}):** {', '.join(active)}")

    # --- Export ---
    st.divider()
    export_cols = [data.col_cliente, data.col_comercial, data.col_zona, data.col_sector,
                   data.col_tipo, "score_heatmap", "cobertura_productos"]
    if strat_col:
        export_cols.append(strat_col)
    if pasos_col:
        export_cols.append(pasos_col)
    export_cols = [c for c in export_cols if c in filtered.columns]

    st.download_button(
        "📥 Descargar CSV",
        filtered[export_cols].to_csv(index=False).encode("utf-8"),
        file_name=f"estrategias_{selected_bdm}.csv",
        mime="text/csv",
    )
