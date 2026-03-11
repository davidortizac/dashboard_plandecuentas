"""
Pagina: Dashboard General — KPIs, distribucion por comercial, zona, sector, tipo.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.data_model import DashboardData


def render(data: DashboardData):
    df = data.master

    # --- KPIs ---
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Clientes", data.n_clients)
    k2.metric("Ejecutivos (BDM)", data.n_bdms)
    k3.metric("Zonas", len(data.zones))
    k4.metric("Sectores", df[data.col_sector].nunique())

    with_strategy = df[df.get("ESTRATEGIA", pd.Series(dtype=str)).notna()].shape[0] if "ESTRATEGIA" in df.columns else 0
    pct = int(with_strategy / max(len(df), 1) * 100)
    k5.metric("Con Estrategia", f"{with_strategy} ({pct}%)")

    st.divider()

    # --- Fila 1: Clientes por Comercial + por Zona ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Clientes por Ejecutivo")
        by_bdm = (
            df[data.col_comercial]
            .value_counts()
            .reset_index()
        )
        by_bdm.columns = ["Ejecutivo", "Clientes"]
        fig = px.bar(
            by_bdm, x="Clientes", y="Ejecutivo", orientation="h",
            color="Clientes",
            color_continuous_scale=["#5b9bd5", "#2e75b5"],
        )
        fig.update_layout(height=max(350, len(by_bdm) * 28), yaxis=dict(autorange="reversed"), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Distribución por Zona")
        by_zona = df[data.col_zona].value_counts().reset_index()
        by_zona.columns = ["Zona", "Clientes"]
        fig_zona = px.pie(
            by_zona, values="Clientes", names="Zona",
            color_discrete_sequence=["#4472c4", "#ed7d31", "#a5a5a5", "#ffc000"],
            hole=0.4,
        )
        fig_zona.update_layout(height=350)
        st.plotly_chart(fig_zona, use_container_width=True)

    st.divider()

    # --- Fila 2: Tipo de Cuenta + Nivel de Relacionamiento ---
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Tipo de Cuenta")
        by_tipo = df[data.col_tipo].value_counts().reset_index()
        by_tipo.columns = ["Tipo", "Clientes"]
        # Simplify labels
        by_tipo["Tipo_short"] = by_tipo["Tipo"].apply(
            lambda x: x.split(":")[0].strip() if ":" in str(x) else str(x)
        )
        fig_tipo = px.bar(
            by_tipo, x="Tipo_short", y="Clientes", color="Tipo",
            color_discrete_sequence=["#92d050", "#5b9bd5", "#ffd966"],
        )
        fig_tipo.update_layout(height=300, showlegend=True, xaxis_title="")
        st.plotly_chart(fig_tipo, use_container_width=True)

    with col_b:
        st.subheader("Nivel de Relacionamiento")
        rel_col = None
        for c in df.columns:
            if "nivel" in c.lower() and "relacion" in c.lower():
                rel_col = c
                break
        if rel_col and rel_col in df.columns:
            by_rel = df[rel_col].value_counts().reset_index()
            by_rel.columns = ["Nivel", "Clientes"]
            color_map = {
                "ALTO": "#92d050", "MEDIO": "#ffd966",
                "BAJO": "#ed7d31", "NINGUNO": "#d9d9d9",
            }
            fig_rel = px.bar(
                by_rel, x="Nivel", y="Clientes", color="Nivel",
                color_discrete_map=color_map,
            )
            fig_rel.update_layout(height=300, showlegend=False, xaxis_title="")
            st.plotly_chart(fig_rel, use_container_width=True)

    st.divider()

    # --- Fila 3: Top sectores ---
    st.subheader("Top Sectores")
    by_sector = df[data.col_sector].value_counts().head(15).reset_index()
    by_sector.columns = ["Sector", "Clientes"]
    fig_sec = px.bar(
        by_sector, x="Clientes", y="Sector", orientation="h",
        color="Clientes", color_continuous_scale=["#d9e2f3", "#4472c4"],
    )
    fig_sec.update_layout(height=max(300, len(by_sector) * 28), yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_sec, use_container_width=True)
