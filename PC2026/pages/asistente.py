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

from modules.config import (
    GEMINI_API_KEY_DEFAULT,
    GEMINI_MODEL_DEFAULT,
    LLM_PROVIDER_DEFAULT,
    LLM_PROVIDERS,
    OLLAMA_MODEL_DEFAULT,
    OLLAMA_TIMEOUT,
    OLLAMA_URL,
    OPENAI_API_KEY_DEFAULT,
    OPENAI_MODEL_DEFAULT,
)
from modules.data_model import DashboardData


# ---------------------------------------------------------------------------
# Contexto aumentado
# ---------------------------------------------------------------------------

def _safe(val) -> str:
    """Devuelve string limpio o vacío si NaN/None."""
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip()


@st.cache_data(ttl=300, show_spinner="Construyendo contexto de datos para el asistente...")
def _build_context(data: DashboardData) -> str:
    """Construye el contexto COMPLETO de todos los datos procesados del Excel."""
    df = data.master
    lines: list[str] = []
    available = [c for c in data.heatmap_all_cols if c in df.columns]
    prod_cols = [c for c in data.heatmap_product_cols if c in df.columns]
    svc_cols = [c for c in data.heatmap_service_cols if c in df.columns]

    # --- Detectar columnas extra disponibles ---
    col_nivel = col_valor = col_desc = col_strat = col_pasos = None
    contact_cols = []  # C-level, Dirección, Gerente, Operativo, Influenciador
    area_cols = []     # Áreas internas del cliente
    for c in df.columns:
        cl = c.lower().strip()
        if "nivel" in cl and "relacion" in cl:
            col_nivel = c
        elif "valorizacion" in cl or "valoracion" in cl:
            col_valor = c
        elif "descripci" in cl and "general" in cl:
            col_desc = c
        elif cl == "estrategia":
            col_strat = c
        elif "pasos" in cl:
            col_pasos = c
        elif cl in ("c-level", "dirección", "direccion", "gerente", "operativo", "influenciador"):
            contact_cols.append(c)
        elif cl in (a.lower() for a in [
            "CIBERSEGURIDAD", "SEGURIDAD DE LA INFORMACION", "INFRAESTRUCTURA",
            "RIESGOS", "TRANSFORMACION DIGITAL", "VP", "COMPRAS", "FINANCIERO",
            "JURIDICO", "MERCADEO",
        ]):
            area_cols.append(c)

    # =====================================================================
    # 1. RESUMEN GENERAL
    # =====================================================================
    lines.append("=== RESUMEN GENERAL DEL PLAN DE CUENTAS 2026 ===")
    lines.append(f"Total clientes: {data.n_clients}")
    lines.append(f"Total ejecutivos (BDM): {data.n_bdms}")
    lines.append(f"Zonas: {', '.join(data.zones)}")
    lines.append(f"Sectores: {', '.join(data.sectors)}")
    lines.append(f"Tipos de cuenta: {', '.join(data.account_types)}")
    lines.append(f"Productos de ciberseguridad en portafolio: {len(prod_cols)} — {', '.join(prod_cols)}")
    lines.append(f"Servicios de ciberseguridad en portafolio: {len(svc_cols)} — {', '.join(svc_cols)}")
    if "score_heatmap" in df.columns:
        lines.append(f"Score heatmap promedio global: {df['score_heatmap'].mean():.1f}")
        lines.append(f"Score heatmap máximo: {df['score_heatmap'].max()}")
        lines.append(f"Score heatmap mínimo: {df['score_heatmap'].min()}")
        lines.append(f"Cobertura promedio (soluciones activas por cliente): {df['cobertura_productos'].mean():.1f}")
    lines.append("")

    # =====================================================================
    # 2. DISTRIBUCIÓN POR ZONA (detallada)
    # =====================================================================
    lines.append("=== CLIENTES POR ZONA ===")
    for zona in data.zones:
        z_df = df[df[data.col_zona] == zona]
        lines.append(f"  {zona}: {len(z_df)} clientes | score prom: {z_df['score_heatmap'].mean():.1f} | cobertura prom: {z_df['cobertura_productos'].mean():.1f}")
        # Sectores en esta zona
        sect_counts = z_df[data.col_sector].value_counts()
        lines.append(f"    Sectores: {', '.join(f'{s}({c})' for s, c in sect_counts.items())}")
        # BDMs en esta zona
        bdm_counts = z_df[data.col_comercial].value_counts()
        lines.append(f"    Ejecutivos: {', '.join(f'{b}({c})' for b, c in bdm_counts.items())}")
    lines.append("")

    # =====================================================================
    # 3. EJECUTIVOS (BDM) — detalle completo
    # =====================================================================
    lines.append("=== EJECUTIVOS (BDM) — DETALLE ===")
    for bdm in data.bdm_names:
        b_df = df[df[data.col_comercial] == bdm]
        zona_list = b_df[data.col_zona].dropna().unique().tolist()
        lines.append(f"  {bdm}: {len(b_df)} clientes | Zona(s): {', '.join(zona_list)}")
        lines.append(f"    Score prom: {b_df['score_heatmap'].mean():.1f} | Cobertura prom: {b_df['cobertura_productos'].mean():.1f}")
        # Tipos de cuenta
        tipo_counts = b_df[data.col_tipo].value_counts()
        lines.append(f"    Tipos: {', '.join(f'{t}({c})' for t, c in tipo_counts.items())}")
        # Sectores
        sect_counts = b_df[data.col_sector].value_counts().head(5)
        lines.append(f"    Top sectores: {', '.join(f'{s}({c})' for s, c in sect_counts.items())}")
        # Estrategias
        if col_strat:
            con = b_df[col_strat].notna().sum()
            lines.append(f"    Estrategias definidas: {con}/{len(b_df)} ({int(con/max(len(b_df),1)*100)}%)")
        # Clientes de este BDM
        lines.append(f"    Clientes: {', '.join(b_df[data.col_cliente].dropna().astype(str).tolist())}")
    lines.append("")

    # =====================================================================
    # 4. SECTORES — detalle
    # =====================================================================
    lines.append("=== SECTORES ===")
    for sector, count in df[data.col_sector].value_counts().items():
        s_df = df[df[data.col_sector] == sector]
        lines.append(f"  {sector}: {count} clientes | score prom: {s_df['score_heatmap'].mean():.1f} | cobertura prom: {s_df['cobertura_productos'].mean():.1f}")
    lines.append("")

    # =====================================================================
    # 5. NIVEL DE RELACIONAMIENTO Y VALORIZACIÓN
    # =====================================================================
    if col_nivel:
        lines.append("=== NIVEL DE RELACIONAMIENTO ===")
        for nivel, count in df[col_nivel].value_counts().items():
            lines.append(f"  {nivel}: {count} clientes")
        lines.append("")

    if col_valor:
        lines.append("=== VALORIZACIÓN DE LA RELACIÓN ===")
        for val, count in df[col_valor].value_counts().items():
            lines.append(f"  {val}: {count} clientes")
        lines.append("")

    # =====================================================================
    # 6. TIPO DE CUENTA
    # =====================================================================
    lines.append("=== TIPO DE CUENTA ===")
    for tipo, count in df[data.col_tipo].value_counts().items():
        lines.append(f"  {tipo}: {count} clientes")
    lines.append("")

    # =====================================================================
    # 7. SEMÁFORO DE OPORTUNIDADES
    # =====================================================================
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
        lines.append(f"  Umbrales: Q75={q75:.0f}, Q25={q25:.0f}, MaxCobertura={max_cob}")
        for color in ["Verde", "Amarillo", "Rojo"]:
            count = int((sem == color).sum())
            lines.append(f"  {color}: {count} clientes")
        lines.append("")

        # Semáforo por zona
        lines.append("=== SEMÁFORO POR ZONA ===")
        df_sem = df.assign(_sem=sem)
        for zona in data.zones:
            zona_df = df_sem[df_sem[data.col_zona] == zona]
            if zona_df.empty:
                continue
            counts = zona_df["_sem"].value_counts()
            parts = ", ".join(f"{c}: {int(counts.get(c, 0))}" for c in ["Verde", "Amarillo", "Rojo"])
            lines.append(f"  {zona}: {parts}")
        lines.append("")

        # Semáforo por sector
        lines.append("=== SEMÁFORO POR SECTOR ===")
        for sector in data.sectors:
            s_df = df_sem[df_sem[data.col_sector] == sector]
            if s_df.empty:
                continue
            counts = s_df["_sem"].value_counts()
            parts = ", ".join(f"{c}: {int(counts.get(c, 0))}" for c in ["Verde", "Amarillo", "Rojo"])
            lines.append(f"  {sector}: {parts}")
        lines.append("")

        # Semáforo por ejecutivo
        lines.append("=== SEMÁFORO POR EJECUTIVO ===")
        for bdm in data.bdm_names:
            b_df = df_sem[df_sem[data.col_comercial] == bdm]
            if b_df.empty:
                continue
            counts = b_df["_sem"].value_counts()
            parts = ", ".join(f"{c}: {int(counts.get(c, 0))}" for c in ["Verde", "Amarillo", "Rojo"])
            lines.append(f"  {bdm}: {parts}")
        lines.append("")

    # =====================================================================
    # 8. ADOPCIÓN DE PRODUCTOS Y SERVICIOS
    # =====================================================================
    if available:
        lines.append("=== ADOPCIÓN DE PRODUCTOS (clientes con presencia) ===")
        adoption = {c: int((df[c] > 0).sum()) for c in prod_cols}
        for sol, count in sorted(adoption.items(), key=lambda x: -x[1]):
            pct = int(count / max(len(df), 1) * 100)
            lines.append(f"  {sol}: {count} clientes ({pct}%)")
        lines.append("")

        lines.append("=== ADOPCIÓN DE SERVICIOS ===")
        adoption_svc = {c: int((df[c] > 0).sum()) for c in svc_cols}
        for sol, count in sorted(adoption_svc.items(), key=lambda x: -x[1]):
            pct = int(count / max(len(df), 1) * 100)
            lines.append(f"  {sol}: {count} clientes ({pct}%)")
        lines.append("")

        # Productos sin ningún cliente
        zero_adoption = [c for c, n in adoption.items() if n == 0]
        zero_svc = [c for c, n in adoption_svc.items() if n == 0]
        if zero_adoption:
            lines.append(f"  Productos sin adopción: {', '.join(zero_adoption)}")
        if zero_svc:
            lines.append(f"  Servicios sin adopción: {', '.join(zero_svc)}")
        lines.append("")

        # Cross-sell
        if prod_cols and svc_cols:
            has_prod = (df[prod_cols] > 0).any(axis=1)
            has_svc = (df[svc_cols] > 0).any(axis=1)
            cross = int((has_prod & ~has_svc).sum())
            lines.append("=== CROSS-SELL ===")
            lines.append(f"  Clientes con productos pero SIN servicios: {cross} (oportunidad de venta cruzada)")
            lines.append(f"  Clientes con productos Y servicios: {int((has_prod & has_svc).sum())}")
            lines.append(f"  Clientes sin ningún dato de heatmap: {int((~has_prod & ~has_svc).sum())}")
            # Lista de clientes cross-sell
            cross_clients = df[has_prod & ~has_svc][data.col_cliente].dropna().tolist()
            if cross_clients:
                lines.append(f"  Clientes oportunidad cross-sell: {', '.join(str(c) for c in cross_clients[:50])}")
            lines.append("")

    # =====================================================================
    # 9. ESTRATEGIAS
    # =====================================================================
    if col_strat:
        with_strat = int(df[col_strat].notna().sum())
        lines.append("=== ESTRATEGIAS ===")
        lines.append(f"Clientes con estrategia definida: {with_strat} de {len(df)} ({int(with_strat/max(len(df),1)*100)}%)")
        lines.append(f"Clientes SIN estrategia: {len(df) - with_strat}")
        lines.append("")

        lines.append("Cobertura de estrategia por ejecutivo:")
        for bdm in data.bdm_names:
            bdm_df = df[df[data.col_comercial] == bdm]
            total = len(bdm_df)
            con = int(bdm_df[col_strat].notna().sum())
            lines.append(f"  {bdm}: {con}/{total} ({int(con/max(total,1)*100)}%)")
        lines.append("")

        lines.append("Estrategias definidas por cliente:")
        strat_rows = df[df[col_strat].notna()].sort_values("score_heatmap", ascending=False)
        for _, row in strat_rows.iterrows():
            cliente = _safe(row.get(data.col_cliente))
            strat = _safe(row.get(col_strat))[:400]
            pasos = _safe(row.get(col_pasos))[:300] if col_pasos else ""
            line = f"  [{cliente}] Estrategia: {strat}"
            if pasos:
                line += f" | Pasos: {pasos}"
            lines.append(line)
        lines.append("")

    # =====================================================================
    # 10. FICHA COMPLETA DE CADA CLIENTE (toda la información procesada)
    # =====================================================================
    lines.append("=== FICHA COMPLETA DE CADA CLIENTE ===")
    lines.append("(Cada línea contiene TODA la información disponible de un cliente)")
    lines.append("")

    for _, row in df.iterrows():
        cliente = _safe(row.get(data.col_cliente))
        if not cliente:
            continue

        parts = [f"CLIENTE:{cliente}"]

        # Datos básicos
        for label, col in [
            ("Zona", data.col_zona), ("Sector", data.col_sector),
            ("Tipo", data.col_tipo), ("BDM", data.col_comercial),
        ]:
            val = _safe(row.get(col))
            if val:
                parts.append(f"{label}:{val}")

        # Nivel de relación y valorización
        if col_nivel:
            val = _safe(row.get(col_nivel))
            if val:
                parts.append(f"NivelRelación:{val}")
        if col_valor:
            val = _safe(row.get(col_valor))
            if val:
                parts.append(f"Valorización:{val}")

        # Descripción general
        if col_desc:
            val = _safe(row.get(col_desc))
            if val:
                parts.append(f"Descripción:{val[:200]}")

        # Contactos (C-level, Dirección, etc.)
        for cc in contact_cols:
            val = _safe(row.get(cc))
            if val:
                parts.append(f"{cc}:{val}")

        # Áreas internas
        active_areas = []
        for ac in area_cols:
            val = _safe(row.get(ac))
            if val and val.lower() not in ("0", "nan", "none", ""):
                active_areas.append(f"{ac}={val}")
        if active_areas:
            parts.append(f"Áreas:[{','.join(active_areas)}]")

        # Scores
        if "score_heatmap" in df.columns:
            parts.append(f"ScoreTotal:{int(row.get('score_heatmap', 0))}")
            parts.append(f"Cobertura:{int(row.get('cobertura_productos', 0))}")

        # Detalle de cada producto/servicio con su score individual
        active_prods = []
        for p in prod_cols:
            sc = int(row.get(p, 0))
            if sc > 0:
                active_prods.append(f"{p}={sc}")
        if active_prods:
            parts.append(f"Productos:[{','.join(active_prods)}]")

        active_svcs = []
        for s in svc_cols:
            sc = int(row.get(s, 0))
            if sc > 0:
                active_svcs.append(f"{s}={sc}")
        if active_svcs:
            parts.append(f"Servicios:[{','.join(active_svcs)}]")

        # Productos/servicios donde score=0 (oportunidades)
        missing_prods = [p for p in prod_cols if int(row.get(p, 0)) == 0]
        missing_svcs = [s for s in svc_cols if int(row.get(s, 0)) == 0]
        if missing_prods and active_prods:
            parts.append(f"ProductosFaltantes:[{','.join(missing_prods)}]")
        if missing_svcs and active_svcs:
            parts.append(f"ServiciosFaltantes:[{','.join(missing_svcs)}]")

        # Estrategia
        if col_strat:
            strat = _safe(row.get(col_strat))
            if strat:
                parts.append(f"Estrategia:{strat[:300]}")
            pasos = _safe(row.get(col_pasos)) if col_pasos else ""
            if pasos:
                parts.append(f"Pasos:{pasos[:200]}")

        lines.append("  " + " | ".join(parts))

    return "\n".join(lines)


SYSTEM_PROMPT = """Eres un analista de datos del equipo de Desarrollo de Negocios de Gamma (ciberseguridad).

CONTEXTO: Tienes acceso al Plan de Cuentas y Heatmap 2026 con datos reales de clientes, ejecutivos (BDMs), zonas, sectores, productos/servicios y estrategias.

REGLAS ESTRICTAS — DEBES SEGUIRLAS SIEMPRE:
1. SOLO puedes usar la información que aparece en la sección "DATOS DEL PLAN DE CUENTAS 2026" de abajo.
2. NUNCA inventes datos, nombres de clientes, cifras o información que NO esté explícitamente en los datos proporcionados.
3. Si la pregunta requiere información que NO está en los datos, responde: "No tengo esa información en los datos del Plan de Cuentas."
4. NO uses conocimiento general ni datos externos. Tu ÚNICA fuente de verdad son los datos proporcionados abajo.
5. Siempre cita cifras exactas de los datos (scores, cantidades, porcentajes).
6. Cuando menciones un cliente, incluye su ejecutivo (BDM), zona y sector tal como aparecen en los datos.
7. Responde en español, de forma clara y estructurada.
8. Si te piden comparar o analizar, usa SOLO los números de los datos proporcionados.

Tu rol: responder preguntas sobre los datos, identificar oportunidades comerciales, analizar brechas de cobertura y sugerir estrategias basadas EXCLUSIVAMENTE en los datos reales."""


# ---------------------------------------------------------------------------
# Proveedores de LLM
# ---------------------------------------------------------------------------

def _query_ollama(system: str, user_msg: str, model: str, url: str, placeholder) -> str:
    """Envía query a Ollama usando /api/chat con system message separado."""
    chat_url = url.replace("/api/generate", "/api/chat")
    full_response = ""
    r = requests.post(
        chat_url,
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            "stream": True,
            "options": {"temperature": 0.2, "num_predict": 4096},
        },
        stream=True,
        timeout=(5, OLLAMA_TIMEOUT),
    )
    r.raise_for_status()
    for line in r.iter_lines():
        if not line:
            continue
        decoded = json.loads(line.decode("utf-8"))
        chunk = decoded.get("message", {}).get("content", "")
        full_response += chunk
        placeholder.markdown(full_response + "▌")
        if decoded.get("done", False):
            break
    return full_response


def _query_openai(system: str, user_msg: str, model: str, api_key: str, placeholder) -> str:
    """Envía query a OpenAI API con streaming y system message separado."""
    full_response = ""
    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            "temperature": 0.2,
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


def _query_gemini(system: str, user_msg: str, model: str, api_key: str, placeholder) -> str:
    """Envía query a Google Gemini API con system instruction separada."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    r = requests.post(
        url,
        params={"key": api_key},
        json={
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user_msg}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096},
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
    # --- Configuración de conexión ---
    with st.expander("⚙️ Configuración de conexión LLM", expanded=False):
        default_idx = LLM_PROVIDERS.index(LLM_PROVIDER_DEFAULT) if LLM_PROVIDER_DEFAULT in LLM_PROVIDERS else 0
        provider = st.selectbox(
            "Proveedor",
            LLM_PROVIDERS,
            index=default_idx,
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
                api_key = st.text_input("API Key", value=OPENAI_API_KEY_DEFAULT, type="password", key="ai_openai_key")
            with col_model:
                openai_models = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
                oi_idx = openai_models.index(OPENAI_MODEL_DEFAULT) if OPENAI_MODEL_DEFAULT in openai_models else 0
                model_name = st.selectbox(
                    "Modelo",
                    openai_models,
                    index=oi_idx,
                    key="ai_openai_model",
                )
            ollama_url = ""

        else:  # Gemini
            col_key, col_model = st.columns([2, 1])
            with col_key:
                api_key = st.text_input("API Key", value=GEMINI_API_KEY_DEFAULT, type="password", key="ai_gemini_key")
            with col_model:
                gemini_models = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"]
                gm_idx = gemini_models.index(GEMINI_MODEL_DEFAULT) if GEMINI_MODEL_DEFAULT in gemini_models else 0
                model_name = st.selectbox(
                    "Modelo",
                    gemini_models,
                    index=gm_idx,
                    key="ai_gemini_model",
                )
            ollama_url = ""

    # Build context (cached globally via st.cache_data, shared across sessions)
    context = _build_context(data)

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

        system_msg = (
            f"{SYSTEM_PROMPT}\n\n"
            f"--- DATOS DEL PLAN DE CUENTAS 2026 ---\n"
            f"{context}\n"
            f"--- FIN DE DATOS ---"
        )
        user_msg = (
            f"{prompt}\n\n"
            f"Responde usando SOLO los datos proporcionados arriba. No inventes información."
        )

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_response = ""

            try:
                if provider == "Ollama (Local)":
                    full_response = _query_ollama(system_msg, user_msg, model_name, ollama_url, placeholder)
                elif provider == "OpenAI":
                    if not api_key:
                        placeholder.error("Ingresa tu API Key de OpenAI en la configuración.")
                    else:
                        full_response = _query_openai(system_msg, user_msg, model_name, api_key, placeholder)
                else:  # Gemini
                    if not api_key:
                        placeholder.error("Ingresa tu API Key de Gemini en la configuración.")
                    else:
                        full_response = _query_gemini(system_msg, user_msg, model_name, api_key, placeholder)

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
