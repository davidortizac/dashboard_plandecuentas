"""
Pagina: Semaforo de Oportunidades — vista tipo traffic light por cliente y sector.

Clasifica cada cuenta segun su score de heatmap y cobertura en:
  🟢 Alto potencial (score alto, buena cobertura)
  🟡 Oportunidad media (score/cobertura parcial)
  🔴 Sin cobertura o bajo interes
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.data_model import DashboardData


def _classify_semaforo(row, q75, q25, max_cob):
    score = row.get("score_heatmap", 0)
    cob = row.get("cobertura_productos", 0)
    if score >= q75 and cob >= max_cob * 0.3:
        return "Verde"
    elif score >= q25 or cob >= max_cob * 0.1:
        return "Amarillo"
    else:
        return "Rojo"


SEMAFORO_COLORS = {"Verde": "#92d050", "Amarillo": "#ffd966", "Rojo": "#ff4444"}
SEMAFORO_ORDER = ["Verde", "Amarillo", "Rojo"]


def render(data: DashboardData):
    df = data.master.copy()

    if "score_heatmap" not in df.columns:
        st.warning("No hay datos de heatmap disponibles para generar el semáforo.")
        return

    # Calcular semáforo
    q75 = df["score_heatmap"].quantile(0.75)
    q25 = df["score_heatmap"].quantile(0.25)
    max_cob = df["cobertura_productos"].max() if df["cobertura_productos"].max() > 0 else 1

    df["semaforo"] = df.apply(lambda r: _classify_semaforo(r, q75, q25, max_cob), axis=1)

    # --- KPIs ---
    counts = df["semaforo"].value_counts()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("🟢 Alto Potencial", int(counts.get("Verde", 0)))
    k2.metric("🟡 Oportunidad", int(counts.get("Amarillo", 0)))
    k3.metric("🔴 Sin Cobertura", int(counts.get("Rojo", 0)))
    k4.metric("Score Promedio", f"{df['score_heatmap'].mean():.1f}")

    st.divider()

    # --- Filtros ---
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        zona_filter = st.multiselect("Zona", data.zones, default=data.zones, key="sem_zona")
    with fc2:
        tipo_filter = st.multiselect("Tipo Cuenta", data.account_types, default=data.account_types, key="sem_tipo")
    with fc3:
        sem_filter = st.multiselect("Semáforo", SEMAFORO_ORDER, default=SEMAFORO_ORDER, key="sem_color")

    mask = (
        df[data.col_zona].isin(zona_filter)
        & df[data.col_tipo].isin(tipo_filter)
        & df["semaforo"].isin(sem_filter)
    )
    filtered = df[mask]

    # --- Semáforo por sector ---
    st.subheader("Semáforo por Sector")
    sector_sem = (
        filtered.groupby([data.col_sector, "semaforo"])
        .size()
        .reset_index(name="count")
    )
    if not sector_sem.empty:
        fig = px.bar(
            sector_sem, x="count", y=data.col_sector, color="semaforo",
            orientation="h",
            color_discrete_map=SEMAFORO_COLORS,
            category_orders={"semaforo": SEMAFORO_ORDER},
        )
        n_sectors = sector_sem[data.col_sector].nunique()
        fig.update_layout(
            height=max(350, n_sectors * 25),
            yaxis=dict(autorange="reversed", categoryorder="total ascending"),
            xaxis_title="Clientes",
            legend_title="Semáforo",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Semáforo por ejecutivo ---
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Semáforo por Ejecutivo")
        bdm_sem = (
            filtered.groupby([data.col_comercial, "semaforo"])
            .size()
            .reset_index(name="count")
        )
        if not bdm_sem.empty:
            fig2 = px.bar(
                bdm_sem, x="count", y=data.col_comercial, color="semaforo",
                orientation="h",
                color_discrete_map=SEMAFORO_COLORS,
                category_orders={"semaforo": SEMAFORO_ORDER},
            )
            n_bdms = bdm_sem[data.col_comercial].nunique()
            fig2.update_layout(
                height=max(350, n_bdms * 30),
                yaxis=dict(autorange="reversed", categoryorder="total ascending"),
                xaxis_title="Clientes", legend_title="",
            )
            st.plotly_chart(fig2, use_container_width=True)

    with col_b:
        st.subheader("Distribución General")
        fig3 = px.pie(
            values=[int(counts.get(s, 0)) for s in SEMAFORO_ORDER],
            names=SEMAFORO_ORDER,
            color=SEMAFORO_ORDER,
            color_discrete_map=SEMAFORO_COLORS,
            hole=0.45,
        )
        fig3.update_layout(height=350)
        st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # --- Tabla detalle ---
    st.subheader("Detalle de Cuentas")
    display_cols = [data.col_cliente, data.col_comercial, data.col_zona,
                    data.col_sector, data.col_tipo, "score_heatmap",
                    "cobertura_productos", "semaforo"]
    display_cols = [c for c in display_cols if c in filtered.columns]
    st.dataframe(
        filtered[display_cols].sort_values("score_heatmap", ascending=False),
        use_container_width=True,
        height=400,
    )
