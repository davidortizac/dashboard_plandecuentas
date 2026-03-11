"""
Conexion a Google Drive: descarga el archivo Excel preservando formato/colores.

Usa la Drive API para exportar el Google Sheet como .xlsx (mantiene colores de
celda), o descarga directamente si ya es un archivo .xlsx nativo.
"""
from __future__ import annotations

import io
import tempfile
from pathlib import Path

import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from modules.config import SCOPES, SHEET_ID, get_gcp_credentials


@st.cache_data(ttl=120, show_spinner="Descargando archivo de Google Drive...")
def download_excel_from_drive(file_id: str = SHEET_ID) -> bytes:
    """
    Descarga el archivo desde Google Drive como .xlsx (bytes).

    Si es un Google Sheet nativo, usa export (application/vnd.openxmlformats...).
    Si es un .xlsx subido directamente, usa get_media.
    """
    creds = get_gcp_credentials(SCOPES)
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    # Obtener metadata para saber el MIME type
    meta = service.files().get(fileId=file_id, fields="mimeType,name").execute()
    mime = meta.get("mimeType", "")
    name = meta.get("name", "archivo")

    buf = io.BytesIO()

    if mime == "application/vnd.google-apps.spreadsheet":
        # Es Google Sheet nativo -> exportar como xlsx
        request = service.files().export_media(
            fileId=file_id,
            mimeType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        # Es un .xlsx subido -> descargar directamente
        request = service.files().get_media(fileId=file_id)

    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    return buf.getvalue()


def save_temp_excel(data: bytes) -> Path:
    """Guarda los bytes del Excel en un archivo temporal y retorna la ruta."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    tmp.write(data)
    tmp.close()
    return Path(tmp.name)
