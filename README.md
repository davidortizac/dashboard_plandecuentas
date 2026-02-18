# 📊 Dashboard Comercial 2026

Este proyecto es un tablero de control interactivo diseñado para la gestión y priorización comercial, potenciado con Inteligencia Artificial local.

## 🚀 Características Principales

-   **Visualización de Datos**: Gráficos interactivos de clientes, oportunidades y métricas clave usando Streamlit y Plotly.
-   **Integración con Google Sheets**: Los datos se actualizan automáticamente desde una hoja de cálculo en la nube, con respaldo local en caso de fallos de conexión.
-   **Asistente IA (Chatbot)**: Integración con **Ollama** para chatear con tus datos localmente. Puedes preguntar sobre riesgos, oportunidades o resúmenes y la IA responderá con el contexto del dashboard.
-   **Contenerización**: Listo para desplegarse con Docker.

## 🛠️ Requisitos Previos

-   **Docker Desktop** (para ejecutar la aplicación aislada).
-   **Ollama** (para el chatbot de IA). Debes tenerlo instalado y corriendo (`ollama serve`).
-   Modelo de IA recomendado: `gemma:2b` (o el que prefieras configurar).

## 📦 Instalación y Uso

### Opción 1: Ejecución con Docker (Recomendada)

1.  **Construir la imagen**:
    ```bash
    cd PC2026
    docker build -t dashboard-2026 .
    ```

2.  **Ejecutar el contenedor**:
    Nota: Usamos `--add-host` para permitir que el contenedor se comunique con el Ollama de tu máquina anfitriona.
    ```bash
    docker run -d -p 8501:8501 --add-host=host.docker.internal:host-gateway --name dashboard-app dashboard-2026
    ```

3.  **Acceder**: Abre tu navegador en [http://localhost:8501](http://localhost:8501).

### Opción 2: Ejecución Local (Python)

1.  Instalar dependencias:
    ```bash
    pip install -r PC2026/requirements.txt
    ```

2.  Ejecutar la app:
    ```bash
    streamlit run PC2026/app.py
    ```

## 🤖 Configuración del Chatbot

En la barra lateral del dashboard, encontrarás la sección **"Asistente IA"**.
-   Asegúrate de que Ollama esté corriendo en tu PC.
-   Ingresa el nombre de tu modelo local (ej: `gemma:2b`, `llama3`, `mistral`) en el campo de configuración.
-   ¡Pregunta lo que quieras sobre tus datos!

## 📂 Estructura del Proyecto

-   `PC2026/app.py`: Código principal de la aplicación Streamlit.
-   `PC2026/Dockerfile`: Configuración para construir la imagen Docker.
-   `PC2026/requirements.txt`: Lista de librerías Python necesarias.
-   `PC2026/*.csv/xlsx`: Archivos de datos de respaldo (fallback).

---
Desarrollado para la gestión comercial 2026.
