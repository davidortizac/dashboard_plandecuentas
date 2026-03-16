"""
Dashboard Plan de Cuentas & Heatmap 2026
=========================================
Aplicación de perfilación de cuentas comerciales para Gamma.
Lee "PLAN DE CUENTAS Y HEATMAP 2026.xlsx" desde Google Drive y genera
análisis de scoring, semáforo de oportunidades y gestión de estrategias.
"""
import streamlit as st

# ---------------------------------------------------------------------------
# Config de pagina (DEBE ir primero)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Plan de Cuentas 2026 — Gamma",
    page_icon="📊",
    layout="wide",
)

from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=300_000)  # refresh cada 5 min

from modules.data_model import load_dashboard_data

# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------
try:
    data = load_dashboard_data()
except FileNotFoundError as e:
    msg = str(e)
    if "credentials" in msg:
        st.error(
            "No se encontró el archivo de credenciales de Google (`credentials.json`). "
            "Revisa `DEPLOYMENT.md` para la configuración."
        )
    else:
        st.error("Archivo no encontrado. Revisa la configuración.")
    st.code(msg)
    st.stop()
except Exception as e:
    st.error(
        "No se pudo cargar la data desde Google Drive. "
        "Verifica: API de Drive habilitada, archivo compartido con la cuenta de servicio."
    )
    st.code(str(e))
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar: navegación + info
# ---------------------------------------------------------------------------
st.sidebar.title("📊 Plan de Cuentas 2026")
st.sidebar.caption(
    f"{data.n_clients} clientes | {data.n_bdms} AMs | {len(data.zones)} zonas"
)

PAGES = {
    "📊 DASHBOARD": "dashboard",
    "🚦 SEMÁFORO": "semaforo",
    "🗺️ ZONAS": "zonas",
    "💼 SOLUCIONES": "soluciones",
    "🔍 PERFILACIÓN": "perfilacion",
    "📌 ESTRATEGIAS": "estrategias",
    "🤖 ASISTENTE IA": "asistente",
}

st.sidebar.divider()
selected = st.sidebar.radio("Navegación", list(PAGES.keys()), label_visibility="collapsed")

st.sidebar.divider()
st.sidebar.markdown(
    "**Gamma** — Desarrollo de Negocios\n\n"
    "Dashboard de perfilación y estrategia comercial."
)

# ---------------------------------------------------------------------------
# Render de la página seleccionada
# ---------------------------------------------------------------------------
from pages import dashboard, semaforo, zonas, soluciones, perfilacion, estrategias, asistente

page_modules = {
    "dashboard": dashboard,
    "semaforo": semaforo,
    "zonas": zonas,
    "soluciones": soluciones,
    "perfilacion": perfilacion,
    "estrategias": estrategias,
    "asistente": asistente,
}

# ---------------------------------------------------------------------------
# Header sticky (permanece visible al hacer scroll)
# ---------------------------------------------------------------------------
page_key = PAGES[selected]
page_label = [k for k, v in PAGES.items() if v == page_key][0]

st.markdown(
    f"""
    <div class="sticky-header">
        <h2 style="margin:0; padding:0;">{page_label}</h2>
    </div>
    <style>
    .sticky-header {{
        position: sticky;
        top: 0;
        z-index: 999;
        background: var(--background-color, #0e1117);
        padding: 0.75rem 0 0.5rem 0;
        border-bottom: 1px solid rgba(250,250,250,0.1);
    }}
    /* Soporte para tema claro */
    @media (prefers-color-scheme: light) {{
        .sticky-header {{
            background: var(--background-color, #ffffff);
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

page_modules[page_key].render(data)
