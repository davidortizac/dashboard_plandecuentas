"""
Pagina: Análisis de Zonas — breakdown geográfico con métricas de cobertura.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.data_model import DashboardData


def render(data: DashboardData):
    df = data.master

    # --- Selector de zona ---
    zona_sel = st.selectbox("Selecciona Zona", ["Todas"] + data.zones, key="zona_sel")
    filtered = df if zona_sel == "Todas" else df[df[data.col_zona] == zona_sel]

    # --- KPIs de zona ---
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Clientes", len(filtered))
    k2.metric("Ejecutivos", filtered[data.col_comercial].nunique())
    k3.metric("Sectores", filtered[data.col_sector].nunique())
    avg_score = filtered["score_heatmap"].mean() if "score_heatmap" in filtered.columns else 0
    k4.metric("Score Prom. Heatmap", f"{avg_score:.1f}")

    st.divider()

    # --- Comparativa entre zonas ---
    st.subheader("Comparativa entre Zonas")
    zone_stats = (
        df.groupby(data.col_zona)
        .agg(
            Clientes=(data.col_cliente, "count"),
            Ejecutivos=(data.col_comercial, "nunique"),
            Sectores=(data.col_sector, "nunique"),
            Score_Promedio=("score_heatmap", "mean"),
            Cobertura_Promedio=("cobertura_productos", "mean"),
        )
        .reset_index()
        .round(1)
    )

    col_a, col_b = st.columns(2)
    with col_a:
        fig = px.bar(
            zone_stats, x=data.col_zona, y="Clientes",
            color=data.col_zona,
            color_discrete_sequence=["#4472c4", "#ed7d31", "#a5a5a5"],
            text="Clientes",
        )
        fig.update_layout(height=300, showlegend=False, xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        fig2 = px.bar(
            zone_stats, x=data.col_zona, y=["Score_Promedio", "Cobertura_Promedio"],
            barmode="group",
            color_discrete_sequence=["#92d050", "#5b9bd5"],
        )
        fig2.update_layout(height=300, xaxis_title="", yaxis_title="Promedio")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # --- Detalle de la zona seleccionada ---
    st.subheader(f"Detalle: {zona_sel}")

    col_c, col_d = st.columns(2)

    with col_c:
        st.write("**Clientes por Sector**")
        by_sector = filtered[data.col_sector].value_counts().head(12).reset_index()
        by_sector.columns = ["Sector", "Clientes"]
        fig3 = px.bar(
            by_sector, x="Clientes", y="Sector", orientation="h",
            color="Clientes", color_continuous_scale=["#d9e2f3", "#4472c4"],
        )
        fig3.update_layout(height=max(280, len(by_sector) * 25), yaxis=dict(autorange="reversed"), showlegend=False)
        st.plotly_chart(fig3, use_container_width=True)

    with col_d:
        st.write("**Tipo de Cuenta**")
        by_tipo = filtered[data.col_tipo].value_counts().reset_index()
        by_tipo.columns = ["Tipo", "Clientes"]
        fig4 = px.pie(
            by_tipo, values="Clientes", names="Tipo",
            color_discrete_sequence=["#92d050", "#5b9bd5", "#ffd966"],
            hole=0.4,
        )
        fig4.update_layout(height=280)
        st.plotly_chart(fig4, use_container_width=True)

    # --- Ejecutivos en la zona ---
    st.write("**Ejecutivos en esta zona:**")
    bdm_zona = (
        filtered.groupby(data.col_comercial)
        .agg(
            Clientes=(data.col_cliente, "count"),
            Score_Total=("score_heatmap", "sum"),
            Score_Prom=("score_heatmap", "mean"),
        )
        .reset_index()
        .sort_values("Clientes", ascending=False)
        .round(1)
    )
    st.dataframe(bdm_zona, use_container_width=True, hide_index=True)

    st.divider()

    # --- Tabla de clientes ---
    st.subheader("Clientes")
    show_cols = [data.col_cliente, data.col_comercial, data.col_sector,
                 data.col_tipo, "score_heatmap", "cobertura_productos"]
    show_cols = [c for c in show_cols if c in filtered.columns]
    st.dataframe(
        filtered[show_cols].sort_values("score_heatmap", ascending=False),
        use_container_width=True, height=400,
    )
