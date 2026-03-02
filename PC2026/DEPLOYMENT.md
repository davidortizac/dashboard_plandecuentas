# Manual de despliegue (PC2026)

Este repositorio contiene una app de **Streamlit** que:

- Lee datos desde **Google Sheets** usando una **cuenta de servicio** (archivo `credentials.json`).
- Muestra un dashboard (Plotly/Pandas).
- Incluye un asistente IA opcional que llama a **Ollama** por HTTP (normalmente en tu host, puerto `11434`).

> Nota: En el proyecto existen **dos variantes** de la app:
>
> - **Principal**: `PC2026/app.py`
> - **Plan de cuentas**: `PC2026/dashboard_plandecuentas/PC2026/app.py`

---

## Requisitos previos

- **Python** 3.11+ (recomendado 3.11/3.12 para compatibilidad con dependencias).
- (Opcional) **Docker Desktop** si quieres ejecutar en contenedor.
- (Para el chatbot) **Ollama** corriendo en tu máquina:
  - `ollama serve`
  - Modelo descargado (por defecto en la UI: `gemma3:4b`)
- Acceso a Google Cloud para:
  - Tener una **cuenta de servicio** con `credentials.json`.
  - **Habilitar APIs** necesarias.
  - Compartir la hoja con la cuenta de servicio.

---

## Preparación de Google (obligatorio para cargar datos)

### 1) Habilitar APIs en el proyecto de la cuenta de servicio

En Google Cloud Console, para el proyecto asociado a tu `credentials.json`:

- Habilita **Google Sheets API**
- Recomendado: habilita también **Google Drive API**

Si no lo haces, verás errores tipo:

- `APIError: [403]: Google Sheets API has not been used in project ... or it is disabled`

### 2) Compartir la hoja con la cuenta de servicio

Abre tu Google Sheet y compártela con el email de la cuenta de servicio (en `credentials.json`, campo `client_email`, suele ser algo como `...@...iam.gserviceaccount.com`), con permisos de **lector** (o superior si lo necesitas).

Si no lo haces, verás errores tipo:

- `PermissionError` al abrir el spreadsheet.

---

## Ubicación de `credentials.json` (secreto)

**Nunca lo subas a GitHub.** Debe estar fuera de control de versiones.

### App principal (`PC2026/app.py`)

Esta app intenta encontrar credenciales en este orden:

1. `/app/credentials.json` (típico dentro de Docker)
2. `PC2026/credentials.json` (recomendado en local)
3. `PC2026/venv/app/credentials.json` (útil si ya lo tienes ahí)

### App plan de cuentas (`PC2026/dashboard_plandecuentas/PC2026/app.py`)

Esta variante lee `credentials.json` **relativo al directorio donde corres la app**.

Recomendación: coloca el archivo en:

- `PC2026/dashboard_plandecuentas/PC2026/credentials.json`

---

## Ejecución local (Linux / WSL)

Ejemplo para la app principal.

```bash
cd /mnt/e/IA/GAMMA/PC2026

# (si no existe) crear venv
python3 -m venv venv

# activar venv
source venv/bin/activate

# instalar dependencias
pip install -r requirements.txt

# ejecutar
streamlit run app.py
```

Abre `http://localhost:8501`.

> Si ves `gio: http://localhost:8501: Operation not supported`, es solo que WSL no puede abrir el navegador automáticamente. Abre el link manualmente desde Windows.

### Ejecutar la variante plan de cuentas (local)

```bash
cd /mnt/e/IA/GAMMA/PC2026/dashboard_plandecuentas/PC2026
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

---

## Ejecución local (Windows PowerShell)

Ejemplo para la app principal.

```powershell
cd e:\IA\GAMMA\PC2026

python -m venv venv
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
streamlit run app.py
```

Abre `http://localhost:8501`.

---

## Ejecución con Docker (app principal)

### 1) Build

Desde `PC2026/`:

```bash
cd PC2026
docker build -t pc2026-dashboard .
```

### 2) Run (montando credenciales)

#### Windows / macOS (Docker Desktop)

```bash
docker run --rm -p 8501:8501 \
  -v "$(pwd)/credentials.json:/app/credentials.json:ro" \
  pc2026-dashboard
```

#### Linux (si `host.docker.internal` no existe)

Si vas a usar el chatbot con Ollama en el host, suele ayudar:

```bash
docker run --rm -p 8501:8501 \
  --add-host=host.docker.internal:host-gateway \
  -v "$(pwd)/credentials.json:/app/credentials.json:ro" \
  pc2026-dashboard
```

Abre `http://localhost:8501`.

---

## Chatbot (Ollama) – notas

La app hace POST a:

- `http://host.docker.internal:11434/api/generate`

Para que funcione:

- Asegúrate de tener Ollama corriendo: `ollama serve`
- Descarga el modelo que uses (ej. `gemma3:4b`)
- Si lo ejecutas dentro de Docker en Linux, usa `--add-host=host.docker.internal:host-gateway`

---

## Troubleshooting rápido

### Error: `FileNotFoundError: /app/credentials.json`

Estás ejecutando en local y el código esperaba una ruta de Docker, o no tienes el archivo en ninguna ubicación válida.

- En local: coloca `credentials.json` en `PC2026/credentials.json` (recomendado) o en `PC2026/venv/app/credentials.json`.
- En Docker: monta el archivo a `/app/credentials.json` con `-v ...:/app/credentials.json:ro`.

### Error: `APIError: [403]: Google Sheets API ... disabled`

- Habilita **Google Sheets API** en el proyecto de Google Cloud del `credentials.json`.
- Espera 1–2 minutos y reintenta.

### Error: `PermissionError` al abrir la hoja

- Comparte el Google Sheet con el `client_email` de la cuenta de servicio (lector o superior).

### Error: “Error conectando a Ollama”

- Verifica `ollama serve`
- Verifica que `http://localhost:11434` responda en tu host.
- En Docker Linux: añade `--add-host=host.docker.internal:host-gateway`.

