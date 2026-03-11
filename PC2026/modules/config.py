"""
Configuración centralizada: credenciales GCP, IDs de archivos, constantes.
"""
import json
import os
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Helpers para leer settings (env > st.secrets > default)
# ---------------------------------------------------------------------------

def get_setting(key: str, default=None):
    val = os.environ.get(key, "")
    if val:
        return val
    try:
        from streamlit.errors import StreamlitAPIException
        return st.secrets.get(key, default)
    except (FileNotFoundError, Exception):
        return default


def find_credentials_file() -> Path:
    configured = get_setting("PC2026_CREDENTIALS_PATH") or get_setting(
        "GOOGLE_APPLICATION_CREDENTIALS"
    )
    if configured:
        p = Path(str(configured))
        if not p.is_absolute():
            p = (BASE_DIR / p).resolve()
        return p

    candidates = [
        Path("/app/credentials.json"),
        BASE_DIR / "credentials.json",
        BASE_DIR / "venv" / "app" / "credentials.json",
    ]
    for p in candidates:
        if p.is_file():
            return p

    searched = ", ".join(str(p) for p in candidates)
    raise FileNotFoundError(
        f"No se encontro credentials.json en: {searched}"
    )


def get_gcp_credentials(scopes: list[str]):
    from google.oauth2.service_account import Credentials

    env_json = get_setting("GOOGLE_SERVICE_ACCOUNT_JSON") or get_setting(
        "GCP_SERVICE_ACCOUNT_JSON"
    )
    if env_json:
        info = json.loads(env_json)
        return Credentials.from_service_account_info(info, scopes=scopes)

    try:
        for key in ("gcp_service_account", "google_service_account", "service_account"):
            if key in st.secrets and isinstance(st.secrets[key], dict):
                return Credentials.from_service_account_info(st.secrets[key], scopes=scopes)
    except (FileNotFoundError, Exception):
        pass

    creds_path = find_credentials_file()
    return Credentials.from_service_account_file(str(creds_path), scopes=scopes)


# ---------------------------------------------------------------------------
# Constantes del proyecto
# ---------------------------------------------------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

SHEET_ID = get_setting("PC2026_SHEET_ID", "1Io07Ah3IWImvzHJLQcR_fZ22MpCFFwW0")

# ---------------------------------------------------------------------------
# LLM — Proveedor por defecto y configuración
# ---------------------------------------------------------------------------
# Valores posibles para PC2026_LLM_PROVIDER: "Ollama (Local)", "OpenAI", "Google Gemini"
LLM_PROVIDERS = ["Ollama (Local)", "OpenAI", "Google Gemini"]
LLM_PROVIDER_DEFAULT = get_setting("PC2026_LLM_PROVIDER", "Ollama (Local)")

# Ollama
OLLAMA_URL = get_setting(
    "PC2026_OLLAMA_URL", "http://host.docker.internal:11434/api/generate"
)
OLLAMA_TIMEOUT = float(get_setting("PC2026_OLLAMA_TIMEOUT_S", "60"))
OLLAMA_MODEL_DEFAULT = get_setting("PC2026_OLLAMA_MODEL", "ministral-3:8b")

# OpenAI
OPENAI_API_KEY_DEFAULT = get_setting("PC2026_OPENAI_API_KEY", "")
OPENAI_MODEL_DEFAULT = get_setting("PC2026_OPENAI_MODEL", "gpt-4o-mini")

# Gemini
GEMINI_API_KEY_DEFAULT = get_setting("PC2026_GEMINI_API_KEY", "")
GEMINI_MODEL_DEFAULT = get_setting("PC2026_GEMINI_MODEL", "gemini-2.5-flash")
