"""
Pagina: Portafolio de Soluciones — penetración de productos/servicios,
oportunidades de cross-sell, y gaps de cobertura.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.data_model import DashboardData, get_heatmap_matrix

COLORSCALE = [
    [0.0, "#f5f5f5"],
    [0.2, "#ff4444"],
    [0.4, "#ed7d31"],
    [0.6, "#ffd966"],
    [0.8, "#5b9bd5"],
    [1.0, "#92d050"],
]


def render(data: DashboardData):
    df = data.master
    all_hm = data.heatmap_all_cols
    products = data.heatmap_product_cols
    services = data.heatmap_service_cols

    if not all_hm:
        st.warning("No hay datos de heatmap para analizar soluciones.")
        return

    # --- KPIs de portafolio ---
    available = [c for c in all_hm if c in df.columns]
    total_cells = len(df) * len(available)
    active_cells = int((df[available] > 0).sum().sum()) if available else 0
    penetration = active_cells / max(total_cells, 1) * 100

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Productos/Servicios", len(available))
    k2.metric("Clientes Analizados", len(df[df["score_heatmap"] > 0]))
    k3.metric("Penetración Global", f"{penetration:.1f}%")
    top_product = df[available].sum().idxmax() if available else "-"
    k4.metric("Producto Líder", top_product)

    st.divider()

    # --- Ranking de productos por adopción ---
    st.subheader("Adopción de Soluciones")

    col_a, col_b = st.columns([2, 1])

    with col_a:
        adoption = df[available].apply(lambda col: (col > 0).sum()).sort_values(ascending=True)
        adoption_df = pd.DataFrame({"Solución": adoption.index, "Clientes": adoption.values})

        # Separar productos y servicios
        adoption_df["Tipo"] = adoption_df["Solución"].apply(
            lambda x: "Servicio" if x in services else "Producto"
        )

        fig = px.bar(
            adoption_df, x="Clientes", y="Solución", orientation="h",
            color="Tipo",
            color_discrete_map={"Producto": "#4472c4", "Servicio": "#ed7d31"},
        )
        fig.update_layout(
            height=max(500, len(adoption_df) * 18),
            yaxis=dict(categoryorder="total ascending"),
            xaxis_title="Clientes con presencia",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.write("**Top 10 por Score Acumulado**")
        score_total = df[available].sum().sort_values(ascending=False).head(10)
        for i, (sol, score) in enumerate(score_total.items(), 1):
            clients = int((df[sol] > 0).sum())
            st.write(f"**{i}. {sol}**")
            st.caption(f"Score: {int(score)} | {clients} clientes")

    st.divider()

    # --- Heatmap visual ---
    st.subheader("Mapa de Calor: Clientes × Soluciones")

    view_mode = st.radio(
        "Vista", ["Productos", "Servicios", "Todo"], horizontal=True, key="sol_view"
    )
    if view_mode == "Productos":
        cols_to_show = [c for c in products if c in df.columns]
    elif view_mode == "Servicios":
        cols_to_show = [c for c in services if c in df.columns]
    else:
        cols_to_show = available

    matrix = get_heatmap_matrix(data, data.col_cliente)
    if not matrix.empty:
        # Filter columns
        show_cols = [c for c in cols_to_show if c in matrix.columns]
        if show_cols:
            mat = matrix[show_cols]
            max_rows = st.slider("Máximo filas", 10, min(200, len(mat)), min(40, len(mat)), key="sol_rows")
            mat = mat.head(max_rows)

            fig_hm = go.Figure(data=go.Heatmap(
                z=mat.values,
                x=[c[:25] for c in mat.columns.tolist()],
                y=mat.index.tolist(),
                colorscale=COLORSCALE,
                zmin=0, zmax=5,
                hoverongaps=False,
                colorbar=dict(
                    title="Score",
                    tickvals=[0, 1, 2, 3, 4, 5],
                    ticktext=["Sin dato", "Crítico", "Riesgo", "Atención", "Alto", "Foco"],
                ),
            ))
            fig_hm.update_layout(
                height=max(500, max_rows * 20),
                xaxis=dict(side="top", tickangle=-45),
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig_hm, use_container_width=True)

    st.divider()

    # --- Gaps / Oportunidades de cross-sell ---
    st.subheader("Oportunidades de Cross-Sell")
    st.write("Clientes con alta cobertura en productos pero baja en servicios (o viceversa).")

    if products and services:
        prod_available = [c for c in products if c in df.columns]
        svc_available = [c for c in services if c in df.columns]

        cross = pd.DataFrame()
        cross[data.col_cliente] = df[data.col_cliente]
        cross["Score Productos"] = df[prod_available].sum(axis=1) if prod_available else 0
        cross["Score Servicios"] = df[svc_available].sum(axis=1) if svc_available else 0
        cross["Cobertura Prod"] = (df[prod_available] > 0).sum(axis=1) if prod_available else 0
        cross["Cobertura Svc"] = (df[svc_available] > 0).sum(axis=1) if svc_available else 0
        cross = cross[(cross["Score Productos"] > 0) | (cross["Score Servicios"] > 0)]

        if not cross.empty:
            fig_scatter = px.scatter(
                cross,
                x="Score Productos", y="Score Servicios",
                hover_data=[data.col_cliente],
                color="Cobertura Prod",
                color_continuous_scale=["#ff4444", "#ffd966", "#92d050"],
                size="Cobertura Svc",
                size_max=15,
            )
            fig_scatter.update_layout(height=450)
            st.plotly_chart(fig_scatter, use_container_width=True)

            st.write("**Clientes con productos pero sin servicios** (oportunidad de venta):")
            gap = cross[(cross["Score Productos"] > 0) & (cross["Score Servicios"] == 0)]
            gap = gap.sort_values("Score Productos", ascending=False)
            if not gap.empty:
                st.dataframe(gap.head(20), use_container_width=True, hide_index=True)
            else:
                st.info("Todos los clientes con productos ya tienen algún servicio.")
