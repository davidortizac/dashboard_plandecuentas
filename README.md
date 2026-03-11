# 📊 Plan de Cuentas & Heatmap 2026 — Gamma

Dashboard de perfilación de cuentas comerciales y gestión de estrategias para el equipo de Desarrollo de Negocios de Gamma (ciberseguridad).

Lee en tiempo real el archivo **"PLAN DE CUENTAS Y HEATMAP 2026.xlsx"** desde Google Drive, extrae los colores de celda del heatmap, los traduce a scores numéricos y genera análisis accionables.

## Versiones

| Rama | Versión | Descripción |
|------|---------|-------------|
| `main` | Original | Dashboard básico con vista única |
| `v1.0` | Snapshot | Copia del código original antes de la reconstrucción |
| `v1.1` | **Actual** | Reconstrucción completa: arquitectura modular, 7 páginas, asistente IA multi-proveedor |

## Características (v1.1)

### 7 Páginas

| Página | Descripción |
|--------|-------------|
| **📊 Dashboard** | KPIs generales, clientes por ejecutivo, zona, sector, tipo de cuenta, nivel de relacionamiento |
| **🚦 Semáforo** | Clasificación Verde/Amarillo/Rojo por score y cobertura. Filtrable por zona y tipo. Vista por sector y ejecutivo |
| **🗺️ Zonas** | Comparativa entre zonas geográficas con métricas de score y cobertura |
| **💼 Soluciones** | Penetración de 44 productos/servicios, mapa de calor, análisis de cross-sell |
| **🔍 Perfilación** | Ficha 360° por cuenta: info general, heatmap individual, entornos, radar chart, estrategia |
| **📌 Estrategias** | Gestión de estrategias por ejecutivo. Cobertura, tarjetas expandibles por cuenta |
| **🤖 Asistente IA** | Chat con contexto aumentado de todos los datos. Soporta Ollama, OpenAI y Gemini |

### Motor de Análisis

- **Scoring por colores de celda**: Traduce los colores de fondo del Excel a una escala 0-5 (verde=5, azul=4, amarillo=3, naranja=2, rojo=1)
- **Coincidencia por proximidad RGB**: Si el color exacto no está en el mapa, busca el más cercano por distancia euclidiana
- **Semáforo adaptativo**: Usa percentiles (Q75/Q25) para clasificar, se ajusta automáticamente a los datos
- **Cross-sell**: Identifica clientes con productos pero sin servicios contratados
- **Contexto aumentado para IA**: Resumen completo de 214 clientes con scores, coberturas, estrategias y soluciones activas

## Stack Técnico

- **Python 3.11** + Streamlit 1.42
- **Plotly** para visualizaciones interactivas
- **openpyxl** para lectura de colores de celda
- **Google Drive API** para descarga en tiempo real
- **Docker** para despliegue
- **Ollama / OpenAI / Gemini** para asistente IA

## Requisitos Previos

- **Docker Desktop** (recomendado) o Python 3.11+
- **credentials.json** de Google Cloud (cuenta de servicio con acceso al archivo)
- **Ollama** (opcional, para asistente IA local): `ollama serve` + `ollama pull gemma3:4b`

## Instalación y Uso

### Docker (recomendado)

```bash
cd PC2026

# Construir imagen
docker build -t pc2026-dashboard .

# Ejecutar (montar credentials.json)
docker run -d \
  --name pc2026-dashboard-app \
  -p 8501:8501 \
  -v $(pwd)/credentials.json:/app/credentials.json:ro \
  --add-host=host.docker.internal:host-gateway \
  pc2026-dashboard
```

Abrir: [http://localhost:8501](http://localhost:8501)

### Local (Python)

```bash
cd PC2026
pip install -r requirements.txt
streamlit run app.py
```

## Configuración del Asistente IA

En la página **🤖 Asistente IA**, abre **⚙️ Configuración de conexión LLM**:

| Proveedor | Configuración | Modelos disponibles |
|-----------|--------------|---------------------|
| **Ollama (Local)** | URL del servidor (auto-detecta modelos) | gemma3:4b, llama3, mistral, etc. |
| **OpenAI** | API Key | gpt-4o-mini, gpt-4o, gpt-4-turbo |
| **Google Gemini** | API Key | gemini-2.0-flash, gemini-1.5-pro |

El asistente recibe como contexto un resumen completo de todos los datos del Plan de Cuentas: clientes, ejecutivos, zonas, sectores, scores, adopción de soluciones y estrategias.

## Estructura del Proyecto

```
PC2026/
├── .streamlit/              # Config Streamlit
│   ├── config.toml          # showSidebarNavigation = false
│   └── secrets.toml         # Placeholder para secrets
├── modules/                 # Lógica de negocio
│   ├── config.py            # Credenciales GCP, constantes, settings
│   ├── data_model.py        # Pipeline de datos, modelo unificado
│   ├── excel_processor.py   # Lectura Excel + extracción de colores
│   ├── google_drive.py      # Descarga desde Google Drive API
│   └── scoring.py           # Modelo de scoring por colores (escala 0-5)
├── pages/                   # Páginas del dashboard
│   ├── dashboard.py         # Vista general (KPIs, distribuciones)
│   ├── semaforo.py          # Semáforo de oportunidades
│   ├── zonas.py             # Análisis geográfico
│   ├── soluciones.py        # Portafolio y cross-sell
│   ├── perfilacion.py       # Ficha individual de cuenta
│   ├── estrategias.py       # Gestión de estrategias BDM
│   └── asistente.py         # Chat IA (Ollama/OpenAI/Gemini)
├── app.py                   # Entry point
├── Dockerfile               # Imagen Docker (python:3.11-slim)
├── requirements.txt         # Dependencias Python
├── DEPLOYMENT.md            # Guía de despliegue detallada
└── MANUAL_ANALITICA.md      # Documentación del modelo analítico
```

## Documentación

- **[DEPLOYMENT.md](PC2026/DEPLOYMENT.md)** — Guía completa de despliegue (Docker, GCP, variables de entorno)
- **[MANUAL_ANALITICA.md](PC2026/MANUAL_ANALITICA.md)** — Documentación del modelo analítico: cómo se calculan scores, semáforo, normalización de datos, fórmulas de cada página

---

Desarrollado para el equipo de Desarrollo de Negocios — Gamma 2026.
