import pandas as pd
import streamlit as st
import plotly.express as px
import requests
import json

st.set_page_config(page_title="Dashboard Comercial 2026", layout="wide")

# ---------- Carga de datos ----------
SHEET_ID = "1Io07Ah3IWImvzHJLQcR_fZ22MpCFFwW0"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

@st.cache_data(ttl=600)  # Cache por 10 minutos
def load_data():
    try:
        # Intentar cargar desde Google Sheets
        xls = pd.ExcelFile(SHEET_URL)
        clientes = pd.read_excel(xls, "clientes")
        oportunidades = pd.read_excel(xls, "oportunidades")
        return clientes, oportunidades
    except Exception as e:
        print(f"Error cargando desde Google Sheets: {e}")
        # Fallback: Carga local si falla la conexión
        try:
            xls = pd.ExcelFile("dashboard_dataset_2026.xlsx")
            clientes = pd.read_excel(xls, "clientes")
            oportunidades = pd.read_excel(xls, "oportunidades")
            return clientes, oportunidades
        except Exception:
            clientes = pd.read_csv("clientes_2026.csv")
            oportunidades = pd.read_csv("oportunidades_2026.csv")
            return clientes, oportunidades

clientes, oportunidades = load_data()

# ---------- Normalización ----------
def norm_str(s):
    if pd.isna(s):
        return s
    return str(s).strip()

for col in ["cliente", "ejecutivo", "sector", "zona", "tipo_cuenta", "nivel_relacion", "valoracion_relacion"]:
    if col in clientes.columns:
        clientes[col] = clientes[col].apply(norm_str)

for col in ["cliente", "servicio", "categoria"]:
    if col in oportunidades.columns:
        oportunidades[col] = oportunidades[col].apply(norm_str)

# Si no existe zona, la inventamos vacía para que no reviente filtros
if "zona" not in clientes.columns:
    clientes["zona"] = "N/A"

# ---------- Scoring ----------
TIPO_SCORE = {"A": 3, "B": 2, "C": 1}
REL_SCORE = {"ALTO": 3, "MEDIO": 2, "BAJO": 1}
OPP_SCORE = {"FOCO": 3, "RENOVACION": 2, "NOTA": 1, "NO_ACTIVO": 0}

clientes["score_tipo"] = clientes.get("tipo_cuenta", "").map(TIPO_SCORE).fillna(0).astype(int)
clientes["score_rel"] = clientes.get("nivel_relacion", "").str.upper().map(REL_SCORE).fillna(0).astype(int)

# Score oportunidades por cliente
opp_tmp = oportunidades.copy()
opp_tmp["score_opp"] = opp_tmp.get("categoria", "").str.upper().map(OPP_SCORE).fillna(0).astype(int)
opp_score_by_client = opp_tmp.groupby("cliente", as_index=False)["score_opp"].sum()

clientes = clientes.merge(opp_score_by_client, on="cliente", how="left")
clientes["score_opp"] = clientes["score_opp"].fillna(0).astype(int)

clientes["score_prioridad"] = clientes["score_tipo"] + clientes["score_rel"] + clientes["score_opp"]

# ---------- Sidebar filtros ----------
st.sidebar.title("Filtros")

ejecutivos = sorted([e for e in clientes["ejecutivo"].dropna().unique().tolist() if e != ""])
sectores = sorted([s for s in clientes["sector"].dropna().unique().tolist() if s != ""])
zonas = sorted([z for z in clientes["zona"].dropna().unique().tolist() if z != ""])
tipos = sorted([t for t in clientes["tipo_cuenta"].dropna().unique().tolist() if t != ""])
rels = sorted([r for r in clientes["nivel_relacion"].dropna().unique().tolist() if r != ""])

sel_ej = st.sidebar.multiselect("Ejecutivo", ejecutivos, default=ejecutivos)
sel_sec = st.sidebar.multiselect("Sector", sectores, default=sectores)
sel_zon = st.sidebar.multiselect("Zona", zonas, default=zonas)
sel_tip = st.sidebar.multiselect("Tipo cuenta", tipos, default=tipos)
sel_rel = st.sidebar.multiselect("Relación", rels, default=rels)

# ---------- Chatbot IA ----------
st.sidebar.divider()
st.sidebar.subheader("🤖 Asistente IA")

# Configuración del modelo
model_name = st.sidebar.text_input("Modelo Ollama", value="gemma:2b", help="Asegúrate de tener este modelo en Ollama ejecutándose localmente.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Mostrar historial (en un expander para no ocupar todo el sidebar)
with st.sidebar.expander("Chat", expanded=True):
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Pregunta sobre los datos..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Preparar contexto
        context_data = f"""
        Resumen del Dashboard:
        - Total Clientes Filtrados: {c_f['cliente'].nunique()}
        - Oportunidades Filtradas: {len(o_f)}
        - Score Promedio: {c_f['score_prioridad'].mean():.2f if len(c_f) > 0 else 0}
        - Top 5 Clientes: {', '.join(c_f.sort_values('score_prioridad', ascending=False).head(5)['cliente'].tolist())}
        """
        
        full_prompt = f"Contexto: {context_data}\n\nPregunta: {prompt}\n\nResponde concisamente como analista de datos."

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            try:
                # Conexión a Ollama (host.docker.internal para salir del contenedor)
                r = requests.post(
                    "http://host.docker.internal:11434/api/generate",
                    json={"model": model_name, "prompt": full_prompt, "stream": True},
                    stream=True
                )
                r.raise_for_status()
                
                for line in r.iter_lines():
                    if line:
                        decoded = json.loads(line.decode('utf-8'))
                        chunk = decoded.get("response", "")
                        full_response += chunk
                        message_placeholder.markdown(full_response + "▌")
                        if decoded.get("done", False):
                            break
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                err_msg = f"Error conectando a Ollama: {e}. Verifica que Ollama esté corriendo y el modelo '{model_name}' exista."
                message_placeholder.error(err_msg)

# Filtrar clientes
c_f = clientes[
    clientes["ejecutivo"].isin(sel_ej) &
    clientes["sector"].isin(sel_sec) &
    clientes["zona"].isin(sel_zon) &
    clientes["tipo_cuenta"].isin(sel_tip) &
    clientes["nivel_relacion"].isin(sel_rel)
].copy()

# Filtrar oportunidades según clientes filtrados
o_f = oportunidades[oportunidades["cliente"].isin(c_f["cliente"].unique())].copy()

# ---------- Tabs ----------
st.title("📊 Dashboard Comercial 2026")

tab1, tab2, tab3, tab4 = st.tabs(["Vista Operativa", "Heatmap", "Priorización", "BDM / Ejecutivo"])

# ===================== TAB 1: VISTA OPERATIVA =====================
with tab1:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total cuentas", int(c_f["cliente"].nunique()))
    col2.metric("Total oportunidades (filtradas)", int(len(o_f)))
    col3.metric("Score prioridad promedio", round(c_f["score_prioridad"].mean(), 2) if len(c_f) else 0)
    # Riesgo: alta oportunidad pero relación baja
    riesgo = c_f[(c_f["nivel_relacion"].str.upper() == "BAJO") & (c_f["score_opp"] >= 3)]["cliente"].nunique()
    col4.metric("Cuentas en riesgo (relación baja + opp)", int(riesgo))

    st.divider()

    left, right = st.columns(2)

    with left:
        df_ej = c_f.groupby("ejecutivo", as_index=False).agg(
            cuentas=("cliente", "nunique"),
            score_total=("score_prioridad", "sum")
        ).sort_values("cuentas", ascending=False)

        fig = px.bar(df_ej, x="cuentas", y="ejecutivo", orientation="h",
                     title="Cuentas por ejecutivo", hover_data=["score_total"])
        st.plotly_chart(fig, use_container_width=True)

    with right:
        df_sec = c_f.groupby("sector", as_index=False).agg(
            cuentas=("cliente", "nunique"),
            score_total=("score_prioridad", "sum")
        ).sort_values("cuentas", ascending=False)

        fig2 = px.bar(df_sec, x="sector", y="cuentas", title="Cuentas por sector",
                      hover_data=["score_total"])
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Top cuentas por prioridad")
    topn = st.slider("Top N", min_value=5, max_value=50, value=20, step=5)
    show_cols = [c for c in ["cliente","ejecutivo","sector","zona","tipo_cuenta","nivel_relacion","score_opp","score_prioridad"] if c in c_f.columns]
    st.dataframe(c_f.sort_values("score_prioridad", ascending=False).head(topn)[show_cols], use_container_width=True)

# ===================== TAB 2: HEATMAP =====================
with tab2:
    st.subheader("Heatmap Cliente vs Servicio")

    # Convertir categoria a valor numérico para heatmap
    o_h = o_f.copy()
    o_h["valor"] = o_h["categoria"].str.upper().map(OPP_SCORE).fillna(0).astype(int)

    # Pivot: filas cliente, columnas servicio
    if len(o_h) == 0:
        st.info("No hay oportunidades para los filtros actuales.")
    else:
        pivot = o_h.pivot_table(index="cliente", columns="servicio", values="valor", aggfunc="max", fill_value=0)

        # Limitar cantidad de clientes (porque heatmap grande se vuelve ilegible)
        max_clients = st.slider("Máximo clientes a mostrar (ordenados por score)", 10, 200, 50, 10)
        top_clients = c_f.sort_values("score_prioridad", ascending=False)["cliente"].unique().tolist()[:max_clients]
        pivot = pivot.loc[pivot.index.isin(top_clients)]

        fig_h = px.imshow(
            pivot,
            aspect="auto",
            title="Heatmap (0=No activo, 1=Nota, 2=Renovación, 3=Foco)"
        )
        st.plotly_chart(fig_h, use_container_width=True)

        st.caption("Tip: usa los filtros de la izquierda para ver solo tu cartera o un sector específico.")

# ===================== TAB 3: PRIORIZACIÓN =====================
with tab3:
    st.subheader("Priorización de cuentas (acción comercial)")
    st.write("Ordenado por **Score de Prioridad** (tipo cuenta + relación + oportunidades).")

    only_risk = st.checkbox("Ver solo riesgo (relación BAJA y score_opp >= 3)", value=False)
    df_p = c_f.copy()
    if only_risk:
        df_p = df_p[(df_p["nivel_relacion"].str.upper() == "BAJO") & (df_p["score_opp"] >= 3)]

    show_cols = [c for c in ["cliente","ejecutivo","sector","zona","tipo_cuenta","nivel_relacion","valoracion_relacion","estrategia","pasos_a_seguir","score_opp","score_prioridad"] if c in df_p.columns]
    st.dataframe(df_p.sort_values("score_prioridad", ascending=False)[show_cols], use_container_width=True)

    st.download_button(
        "Descargar priorización CSV",
        df_p.sort_values("score_prioridad", ascending=False)[show_cols].to_csv(index=False).encode("utf-8"),
        file_name="priorizacion_2026.csv",
        mime="text/csv"
    )

# ===================== TAB 4: BDM / EJECUTIVO =====================
with tab4:
    st.subheader("Detalle por ejecutivo (BDM)")

    chosen = st.selectbox("Selecciona un ejecutivo", sorted(c_f["ejecutivo"].dropna().unique().tolist()))
    df_bdm = c_f[c_f["ejecutivo"] == chosen].copy()

    colA, colB, colC = st.columns(3)
    colA.metric("Cuentas", int(df_bdm["cliente"].nunique()))
    colB.metric("Score total cartera", int(df_bdm["score_prioridad"].sum()))
    colC.metric("Promedio score", round(df_bdm["score_prioridad"].mean(), 2) if len(df_bdm) else 0)

    st.write("Top cuentas del ejecutivo")
    show_cols = [c for c in ["cliente","sector","tipo_cuenta","nivel_relacion","score_prioridad"] if c in df_bdm.columns]
    st.dataframe(df_bdm.sort_values("score_prioridad", ascending=False)[show_cols].head(25), use_container_width=True)

    # Oportunidades por servicio del ejecutivo
    of_bdm = o_f[o_f["cliente"].isin(df_bdm["cliente"].unique())].copy()
    if len(of_bdm):
        of_bdm["valor"] = of_bdm["categoria"].str.upper().map(OPP_SCORE).fillna(0).astype(int)
        svc = of_bdm.groupby("servicio", as_index=False).agg(
            total=("cliente", "nunique"),
            score=("valor", "sum")
        ).sort_values("score", ascending=False)

        fig_s = px.bar(svc, x="servicio", y="score", title="Oportunidades por servicio (score acumulado)")
        st.plotly_chart(fig_s, use_container_width=True)
    else:
        st.info("Este ejecutivo no tiene oportunidades bajo los filtros actuales.")
