"""
Pagina: Perfilación de Cuentas — análisis profundo por cuenta individual.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules.data_model import DashboardData


def _radar_chart(row_data: dict, title: str) -> go.Figure:
    """Genera un radar chart con las dimensiones de la cuenta."""
    categories = list(row_data.keys())
    values = list(row_data.values())
    values.append(values[0])  # cerrar el polígono
    categories.append(categories[0])

    fig = go.Figure(data=go.Scatterpolar(
        r=values, theta=categories, fill="toself",
        line_color="#4472c4", fillcolor="rgba(68,114,196,0.3)",
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
        showlegend=False, title=title, height=350,
    )
    return fig


def render(data: DashboardData):
    df = data.master

    # --- Selector de cuenta ---
    clients = df[data.col_cliente].dropna().unique().tolist()
    selected = st.selectbox("Buscar Cliente", sorted(clients), key="prof_client")

    row = df[df[data.col_cliente] == selected]
    if row.empty:
        st.warning("Cliente no encontrado.")
        return
    row = row.iloc[0]

    # --- Ficha de la cuenta ---
    st.subheader(f"📋 {selected}")

    info_cols = {
        data.col_zona: "Zona",
        data.col_sector: "Sector",
        data.col_tipo: "Tipo de Cuenta",
        data.col_comercial: "Ejecutivo",
    }
    # Add relationship cols
    for c in df.columns:
        if "nivel" in c.lower() and "relacion" in c.lower():
            info_cols[c] = "Nivel Relacionamiento"
        if "valoriz" in c.lower() or "valorac" in c.lower():
            info_cols[c] = "Valorización"

    cols = st.columns(len(info_cols))
    for i, (col_name, label) in enumerate(info_cols.items()):
        if col_name in df.columns:
            val = row.get(col_name, "-")
            cols[i].metric(label, str(val) if not pd.isna(val) else "-")

    # Description
    desc_col = None
    for c in df.columns:
        if "descripci" in c.lower() or "descripcion" in c.lower():
            desc_col = c
            break
    if desc_col and not pd.isna(row.get(desc_col)):
        st.info(f"**Descripción:** {row[desc_col]}")

    st.divider()

    # --- Score y cobertura ---
    k1, k2, k3 = st.columns(3)
    k1.metric("Score Heatmap", int(row.get("score_heatmap", 0)))
    k2.metric("Productos/Servicios con presencia", int(row.get("cobertura_productos", 0)))
    total_hm = len(data.heatmap_all_cols)
    pct = int(row.get("cobertura_productos", 0)) / max(total_hm, 1) * 100
    k3.metric("Cobertura del Portafolio", f"{pct:.0f}%")

    st.divider()

    # --- Heatmap individual ---
    products = data.heatmap_product_cols
    services = data.heatmap_service_cols

    col_prod, col_svc = st.columns(2)

    with col_prod:
        st.write("**Productos**")
        prod_data = {}
        for p in products:
            if p in df.columns:
                score = int(row.get(p, 0))
                prod_data[p] = score
        if prod_data:
            prod_df = pd.DataFrame({"Producto": list(prod_data.keys()), "Score": list(prod_data.values())})
            prod_df = prod_df.sort_values("Score", ascending=True)

            colors = prod_df["Score"].apply(
                lambda s: "#92d050" if s >= 4 else "#5b9bd5" if s >= 3 else "#ffd966" if s >= 2 else "#ed7d31" if s >= 1 else "#e0e0e0"
            )
            fig = px.bar(
                prod_df, x="Score", y="Producto", orientation="h",
                color="Score", color_continuous_scale=["#e0e0e0", "#ff4444", "#ed7d31", "#ffd966", "#5b9bd5", "#92d050"],
                range_color=[0, 5],
            )
            fig.update_layout(height=max(350, len(prod_df) * 16), yaxis=dict(categoryorder="total ascending"), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with col_svc:
        st.write("**Servicios**")
        svc_data = {}
        for s in services:
            if s in df.columns:
                score = int(row.get(s, 0))
                svc_data[s] = score
        if svc_data:
            svc_df = pd.DataFrame({"Servicio": list(svc_data.keys()), "Score": list(svc_data.values())})
            svc_df = svc_df.sort_values("Score", ascending=True)
            fig2 = px.bar(
                svc_df, x="Score", y="Servicio", orientation="h",
                color="Score", color_continuous_scale=["#e0e0e0", "#ff4444", "#ed7d31", "#ffd966", "#5b9bd5", "#92d050"],
                range_color=[0, 5],
            )
            fig2.update_layout(height=max(250, len(svc_df) * 30), yaxis=dict(categoryorder="total ascending"), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # --- Entornos ---
    st.subheader("Entornos del Cliente")
    entorno_cols = ["PREMISAS", "CLOUD", "OT/SCADA"]
    ec1, ec2, ec3 = st.columns(3)
    for i, col in enumerate(entorno_cols):
        matched = None
        for c in df.columns:
            if col.lower() in c.lower():
                matched = c
                break
        if matched:
            val = row.get(matched, "-")
            [ec1, ec2, ec3][i].metric(col, str(val)[:50] if not pd.isna(val) else "No info")

    st.divider()

    # --- Estrategia actual ---
    st.subheader("Estrategia y Próximos Pasos")
    strat_col = None
    pasos_col = None
    for c in df.columns:
        if c.lower().strip() == "estrategia":
            strat_col = c
        if "pasos" in c.lower():
            pasos_col = c

    col_s, col_p = st.columns(2)
    with col_s:
        st.write("**Estrategia:**")
        if strat_col and not pd.isna(row.get(strat_col)):
            st.write(str(row[strat_col]))
        else:
            st.caption("Sin estrategia definida")

    with col_p:
        st.write("**Pasos a Seguir:**")
        if pasos_col and not pd.isna(row.get(pasos_col)):
            st.write(str(row[pasos_col]))
        else:
            st.caption("Sin pasos definidos")

    st.divider()

    # --- Radar comparativo ---
    st.subheader("Radar de Dimensiones")

    # Build radar from key areas
    radar_data = {}
    areas = ["CIBERSEGURIDAD", "INFRAESTRUCTURA", "RIESGOS", "TRANSFORMACION DIGITAL", "COMPRAS"]
    for area in areas:
        matched = None
        for c in df.columns:
            if area.lower() in c.lower():
                matched = c
                break
        if matched:
            color_val = row.get(matched)
            if not pd.isna(color_val) and color_val:
                radar_data[area.title()] = 3  # tiene dato
            else:
                radar_data[area.title()] = 0

    # Add heatmap summary
    if products:
        prod_scores = [int(row.get(p, 0)) for p in products if p in df.columns]
        radar_data["Productos"] = round(sum(prod_scores) / max(len(prod_scores), 1), 1)
    if services:
        svc_scores = [int(row.get(s, 0)) for s in services if s in df.columns]
        radar_data["Servicios"] = round(sum(svc_scores) / max(len(svc_scores), 1), 1)

    if radar_data:
        fig_radar = _radar_chart(radar_data, f"Perfil: {selected}")
        st.plotly_chart(fig_radar, use_container_width=True)
