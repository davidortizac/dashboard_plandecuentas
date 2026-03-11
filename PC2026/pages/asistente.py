"""
Pagina: Asistente IA — chat con LLM usando datos del Excel como contexto aumentado.

Soporta:
- Ollama (local)
- OpenAI (API key)
- Google Gemini (API key)
"""
from __future__ import annotations

import json

import pandas as pd
import requests
import streamlit as st

from modules.config import OLLAMA_MODEL_DEFAULT, OLLAMA_TIMEOUT, OLLAMA_URL
from modules.data_model import DashboardData


# ---------------------------------------------------------------------------
# Contexto aumentado
# ---------------------------------------------------------------------------

def _build_context(data: DashboardData) -> str:
    """Construye el contexto completo de datos reales para el modelo."""
    df = data.master
    lines = []

    # --- Resumen general ---
    lines.append("=== RESUMEN GENERAL DEL PLAN DE CUENTAS 2026 ===")
    lines.append(f"Total clientes: {data.n_clients}")
    lines.append(f"Ejecutivos (BDM): {data.n_bdms}")
    lines.append(f"Zonas: {', '.join(data.zones)}")
    lines.append(f"Sectores únicos: {df[data.col_sector].nunique()}")
    lines.append(f"Tipos de cuenta: {', '.join(data.account_types)}")
    lines.append(f"Productos en portafolio: {len(data.heatmap_product_cols)}")
    lines.append(f"Servicios en portafolio: {len(data.heatmap_service_cols)}")
    lines.append("")

    # --- Distribución por zona ---
    lines.append("=== CLIENTES POR ZONA ===")
    for zona, count in df[data.col_zona].value_counts().items():
        avg_s = df[df[data.col_zona] == zona]["score_heatmap"].mean()
        lines.append(f"  {zona}: {count} clientes (score promedio: {avg_s:.1f})")
    lines.append("")

    # --- Distribución por ejecutivo ---
    lines.append("=== CLIENTES POR EJECUTIVO (BDM) ===")
    for bdm, count in df[data.col_comercial].value_counts().items():
        bdm_df = df[df[data.col_comercial] == bdm]
        avg_s = bdm_df["score_heatmap"].mean()
        avg_c = bdm_df["cobertura_productos"].mean()
        lines.append(f"  {bdm}: {count} clientes | score prom: {avg_s:.1f} | cobertura prom: {avg_c:.1f}")
    lines.append("")

    # --- Top sectores ---
    lines.append("=== TOP SECTORES ===")
    for sector, count in df[data.col_sector].value_counts().head(20).items():
        avg_s = df[df[data.col_sector] == sector]["score_heatmap"].mean()
        lines.append(f"  {sector}: {count} clientes (score prom: {avg_s:.1f})")
    lines.append("")

    # --- Nivel de relacionamiento ---
    for c in df.columns:
        if "nivel" in c.lower() and "relacion" in c.lower():
            lines.append("=== NIVEL DE RELACIONAMIENTO ===")
            for nivel, count in df[c].value_counts().items():
                lines.append(f"  {nivel}: {count} clientes")
            lines.append("")
            break

    # --- Tipo de cuenta ---
    lines.append("=== TIPO DE CUENTA ===")
    for tipo, count in df[data.col_tipo].value_counts().items():
        lines.append(f"  {tipo}: {count} clientes")
    lines.append("")

    # --- Semáforo ---
    if "score_heatmap" in df.columns:
        q75 = df["score_heatmap"].quantile(0.75)
        q25 = df["score_heatmap"].quantile(0.25)
        max_cob = max(df["cobertura_productos"].max(), 1)

        def _sem(row):
            s, c = row.get("score_heatmap", 0), row.get("cobertura_productos", 0)
            if s >= q75 and c >= max_cob * 0.3:
                return "Verde"
            elif s >= q25 or c >= max_cob * 0.1:
                return "Amarillo"
            return "Rojo"

        sem = df.apply(_sem, axis=1)
        lines.append("=== SEMÁFORO DE OPORTUNIDADES ===")
        lines.append(f"  Umbrales: Q75={q75:.0f}, Q25={q25:.0f}, Max cobertura={max_cob}")
        for color in ["Verde", "Amarillo", "Rojo"]:
            count = int((sem == color).sum())
            lines.append(f"  {color}: {count} clientes")
        lines.append(f"  Score heatmap promedio global: {df['score_heatmap'].mean():.1f}")
        lines.append(f"  Cobertura promedio global: {df['cobertura_productos'].mean():.1f} soluciones")
        lines.append("")

        # Semáforo por zona
        lines.append("=== SEMÁFORO POR ZONA ===")
        df_sem = df.copy()
        df_sem["_sem"] = sem
        for zona in data.zones:
            zona_df = df_sem[df_sem[data.col_zona] == zona]
            if zona_df.empty:
                continue
            counts = zona_df["_sem"].value_counts()
            parts = ", ".join(f"{c}: {int(counts.get(c, 0))}" for c in ["Verde", "Amarillo", "Rojo"])
            lines.append(f"  {zona}: {parts}")
        lines.append("")

    # --- Adopción de productos/servicios ---
    available = [c for c in data.heatmap_all_cols if c in df.columns]
    if available:
        lines.append("=== ADOPCIÓN DE PRODUCTOS (clientes con presencia) ===")
        adoption = {c: int((df[c] > 0).sum()) for c in available if c in data.heatmap_product_cols}
        for sol, count in sorted(adoption.items(), key=lambda x: -x[1]):
            lines.append(f"  {sol}: {count} clientes")
        lines.append("")

        lines.append("=== ADOPCIÓN DE SERVICIOS ===")
        adoption_svc = {c: int((df[c] > 0).sum()) for c in available if c in data.heatmap_service_cols}
        for sol, count in sorted(adoption_svc.items(), key=lambda x: -x[1]):
            lines.append(f"  {sol}: {count} clientes")
        lines.append("")

        # Cross-sell
        prod_cols = [c for c in data.heatmap_product_cols if c in df.columns]
        svc_cols = [c for c in data.heatmap_service_cols if c in df.columns]
        if prod_cols and svc_cols:
            has_prod = (df[prod_cols] > 0).any(axis=1)
            has_svc = (df[svc_cols] > 0).any(axis=1)
            cross = int((has_prod & ~has_svc).sum())
            lines.append(f"=== CROSS-SELL ===")
            lines.append(f"  Clientes con productos pero SIN servicios: {cross} (oportunidad de venta)")
            lines.append(f"  Clientes con productos Y servicios: {int((has_prod & has_svc).sum())}")
            lines.append(f"  Clientes sin ningún dato de heatmap: {int((~has_prod & ~has_svc).sum())}")
            lines.append("")

    # --- Top 30 clientes por score ---
    if "score_heatmap" in df.columns:
        lines.append("=== TOP 30 CLIENTES POR SCORE HEATMAP ===")
        top = df.nlargest(30, "score_heatmap")
        for _, row in top.iterrows():
            cliente = row.get(data.col_cliente, "?")
            score = int(row.get("score_heatmap", 0))
            cob = int(row.get("cobertura_productos", 0))
            bdm = row.get(data.col_comercial, "?")
            sector = row.get(data.col_sector, "?")
            zona = row.get(data.col_zona, "?")
            tipo = row.get(data.col_tipo, "?")
            lines.append(f"  {cliente} | Score:{score} | Cobertura:{cob} | BDM:{bdm} | Sector:{sector} | Zona:{zona} | Tipo:{tipo}")
        lines.append("")

    # --- Estrategias ---
    strat_col = pasos_col = None
    for c in df.columns:
        if c.lower().strip() == "estrategia":
            strat_col = c
        if "pasos" in c.lower():
            pasos_col = c

    if strat_col:
        with_strat = df[strat_col].notna().sum()
        lines.append("=== ESTRATEGIAS ===")
        lines.append(f"Clientes con estrategia: {with_strat} de {len(df)} ({int(with_strat/max(len(df),1)*100)}%)")

        # Cobertura por BDM
        lines.append("Cobertura de estrategia por ejecutivo:")
        for bdm in data.bdm_names:
            bdm_df = df[df[data.col_comercial] == bdm]
            total = len(bdm_df)
            con = bdm_df[strat_col].notna().sum()
            lines.append(f"  {bdm}: {con}/{total} ({int(con/max(total,1)*100)}%)")
        lines.append("")

        # Muestra de estrategias
        lines.append("Estrategias definidas (todos los clientes con estrategia):")
        strat_rows = df[df[strat_col].notna()].sort_values("score_heatmap", ascending=False)
        for _, row in strat_rows.iterrows():
            cliente = row.get(data.col_cliente, "?")
            strat = str(row[strat_col])[:300]
            pasos = str(row.get(pasos_col, ""))[:200] if pasos_col else ""
            line = f"  [{cliente}] Estrategia: {strat}"
            if pasos and pasos != "nan" and pasos != "None":
                line += f" | Pasos: {pasos}"
            lines.append(line)
        lines.append("")

    # --- Lista completa de clientes con detalle ---
    lines.append("=== LISTA COMPLETA DE CLIENTES ===")
    for _, row in df.iterrows():
        cliente = row.get(data.col_cliente, "?")
        if pd.isna(cliente):
            continue
        parts = [str(cliente)]
        for field, col in [
            ("Zona", data.col_zona), ("Sector", data.col_sector),
            ("Tipo", data.col_tipo), ("BDM", data.col_comercial),
        ]:
            val = row.get(col, "")
            if not pd.isna(val):
                parts.append(f"{field}:{val}")

        # Nivel de relación
        for c in df.columns:
            if "nivel" in c.lower() and "relacion" in c.lower():
                val = row.get(c, "")
                if not pd.isna(val):
                    parts.append(f"Relación:{val}")
                break

        if "score_heatmap" in df.columns:
            parts.append(f"Score:{int(row.get('score_heatmap', 0))}")
            parts.append(f"Cobertura:{int(row.get('cobertura_productos', 0))}")

        # Productos activos
        active = []
        for p in available:
            if not pd.isna(row.get(p)) and int(row.get(p, 0)) > 0:
                active.append(p)
        if active:
            parts.append(f"Soluciones:[{','.join(active)}]")

        lines.append("  " + " | ".join(parts))

    return "\n".join(lines)


SYSTEM_PROMPT = """Eres un analista experto en desarrollo de negocios y ciberseguridad de Gamma.
Tienes acceso al Plan de Cuentas y Heatmap 2026, que contiene la información completa de todos los clientes,
ejecutivos comerciales (BDMs), zonas, sectores, productos/servicios de ciberseguridad, y estrategias.

Tu rol es:
- Responder preguntas sobre los datos de manera precisa, con números y datos específicos
- Ayudar a identificar oportunidades comerciales y brechas de cobertura
- Sugerir estrategias basadas en los datos reales
- Analizar patrones de cobertura, adopción de soluciones y gaps
- Comparar ejecutivos, zonas, sectores o clientes cuando se solicite

REGLAS:
- Basa tus respuestas SOLO en los datos proporcionados en el contexto
- Siempre incluye cifras y datos concretos para respaldar tus respuestas
- Si no tienes la información para responder, dilo claramente
- Responde en español
- Sé conciso pero completo
- Cuando menciones clientes, incluye su ejecutivo, zona y sector"""


# ---------------------------------------------------------------------------
# Proveedores de LLM
# ---------------------------------------------------------------------------

def _query_ollama(prompt: str, model: str, url: str, placeholder) -> str:
    """Envía query a Ollama con streaming."""
    full_response = ""
    r = requests.post(
        url,
        json={
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": 0.3, "num_predict": 4096},
        },
        stream=True,
        timeout=(5, OLLAMA_TIMEOUT),
    )
    r.raise_for_status()
    for line in r.iter_lines():
        if not line:
            continue
        decoded = json.loads(line.decode("utf-8"))
        chunk = decoded.get("response", "")
        full_response += chunk
        placeholder.markdown(full_response + "▌")
        if decoded.get("done", False):
            break
    return full_response


def _query_openai(prompt: str, model: str, api_key: str, placeholder) -> str:
    """Envía query a OpenAI API con streaming."""
    full_response = ""
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 4096,
            "stream": True,
        },
        stream=True,
        timeout=(5, 120),
    )
    r.raise_for_status()
    for line in r.iter_lines():
        if not line:
            continue
        text = line.decode("utf-8")
        if text.startswith("data: "):
            text = text[6:]
        if text.strip() == "[DONE]":
            break
        try:
            chunk_data = json.loads(text)
            delta = chunk_data.get("choices", [{}])[0].get("delta", {})
            chunk = delta.get("content", "")
            if chunk:
                full_response += chunk
                placeholder.markdown(full_response + "▌")
        except json.JSONDecodeError:
            continue
    return full_response


def _query_gemini(prompt: str, model: str, api_key: str, placeholder) -> str:
    """Envía query a Google Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    r = requests.post(
        url,
        params={"key": api_key},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4096},
        },
        timeout=120,
    )
    r.raise_for_status()
    resp = r.json()
    text = resp.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    placeholder.markdown(text)
    return text


def _get_ollama_models(url: str) -> list[str]:
    """Obtiene la lista de modelos disponibles en Ollama."""
    try:
        r = requests.get(url.replace("/api/generate", "/api/tags"), timeout=3)
        if r.status_code == 200:
            return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render(data: DashboardData):
    st.header("🤖 Asistente IA")

    # --- Configuración de conexión ---
    with st.expander("⚙️ Configuración de conexión LLM", expanded=False):
        provider = st.selectbox(
            "Proveedor",
            ["Ollama (Local)", "OpenAI", "Google Gemini"],
            key="ai_provider",
        )

        if provider == "Ollama (Local)":
            col_url, col_model = st.columns([2, 1])
            with col_url:
                ollama_url = st.text_input(
                    "URL de Ollama",
                    value=OLLAMA_URL,
                    key="ai_ollama_url",
                    help="URL del servidor Ollama. Usa host.docker.internal si corre en Docker.",
                )
            with col_model:
                available_models = _get_ollama_models(ollama_url)
                if available_models:
                    default_idx = 0
                    for i, m in enumerate(available_models):
                        if OLLAMA_MODEL_DEFAULT in m:
                            default_idx = i
                            break
                    model_name = st.selectbox(
                        "Modelo", available_models, index=default_idx, key="ai_model_select",
                    )
                    st.success(f"Conectado — {len(available_models)} modelos")
                else:
                    model_name = st.text_input("Modelo", value=OLLAMA_MODEL_DEFAULT, key="ai_model_fallback")
                    st.error("Sin conexión a Ollama")

        elif provider == "OpenAI":
            col_key, col_model = st.columns([2, 1])
            with col_key:
                api_key = st.text_input("API Key", type="password", key="ai_openai_key")
            with col_model:
                model_name = st.selectbox(
                    "Modelo",
                    ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
                    key="ai_openai_model",
                )
            ollama_url = ""

        else:  # Gemini
            col_key, col_model = st.columns([2, 1])
            with col_key:
                api_key = st.text_input("API Key", type="password", key="ai_gemini_key")
            with col_model:
                model_name = st.selectbox(
                    "Modelo",
                    ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"],
                    key="ai_gemini_model",
                )
            ollama_url = ""

    # Build context (cached in session)
    if "ai_context" not in st.session_state:
        with st.spinner("Construyendo contexto de datos..."):
            st.session_state.ai_context = _build_context(data)

    context = st.session_state.ai_context

    st.caption(
        f"Proveedor: **{provider}** | Modelo: **{model_name}** | "
        f"Contexto: {data.n_clients} clientes, {len(data.heatmap_all_cols)} soluciones"
    )

    st.divider()

    # --- Chat ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Pregunta sobre los datos del Plan de Cuentas..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        full_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"--- DATOS DEL PLAN DE CUENTAS 2026 ---\n"
            f"{context}\n"
            f"--- FIN DE DATOS ---\n\n"
            f"Pregunta del usuario: {prompt}\n\n"
            f"Responde de forma clara y estructurada, usando datos específicos del contexto:"
        )

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""

            try:
                if provider == "Ollama (Local)":
                    full_response = _query_ollama(full_prompt, model_name, ollama_url, placeholder)
                elif provider == "OpenAI":
                    if not api_key:
                        placeholder.error("Ingresa tu API Key de OpenAI en la configuración.")
                    else:
                        full_response = _query_openai(full_prompt, model_name, api_key, placeholder)
                else:  # Gemini
                    if not api_key:
                        placeholder.error("Ingresa tu API Key de Gemini en la configuración.")
                    else:
                        full_response = _query_gemini(full_prompt, model_name, api_key, placeholder)

                if full_response:
                    placeholder.markdown(full_response)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": full_response}
                    )

            except requests.exceptions.ConnectionError:
                placeholder.error(
                    f"No se pudo conectar al proveedor ({provider}). "
                    f"Verifica la conexión y configuración."
                )
            except requests.exceptions.Timeout:
                placeholder.error("Timeout — el modelo tardó demasiado en responder.")
            except requests.exceptions.HTTPError as e:
                placeholder.error(f"Error HTTP: {e}")
            except Exception as e:
                placeholder.error(f"Error: {e}")

    # --- Preguntas sugeridas ---
    if not st.session_state.messages:
        st.divider()
        st.subheader("Preguntas sugeridas")

        suggestions = [
            "¿Cuáles son los 5 clientes con mayor score y qué ejecutivo los atiende?",
            "¿Qué zona tiene mejor cobertura de soluciones y cuál necesita más atención?",
            "¿Cuáles son los productos de ciberseguridad con menor adopción?",
            "¿Qué ejecutivo tiene más clientes sin estrategia definida?",
            "Compara la zona Norte vs Centro en clientes, sectores y score promedio",
            "¿Qué clientes del sector Financiero tienen oportunidad de cross-sell en servicios?",
            "Resume el estado general del Plan de Cuentas 2026",
            "¿Cuáles son los sectores con más clientes en semáforo rojo?",
        ]

        cols = st.columns(2)
        for i, s in enumerate(suggestions):
            with cols[i % 2]:
                st.markdown(f"- _{s}_")

    # --- Limpiar chat ---
    if st.session_state.messages:
        if st.button("🗑️ Limpiar conversación", key="clear_chat"):
            st.session_state.messages = []
            st.rerun()
