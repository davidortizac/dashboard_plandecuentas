FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# usuario no-root
RUN addgroup --system app \
    && adduser --system --ingroup app --home /home/app --shell /bin/sh app \
    && mkdir -p /home/app/.streamlit /home/app/.cache \
    && chown -R app:app /home/app

ENV HOME=/home/app

# instalar dependencias (capa separada para mejor caché)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# copiar proyecto (credentials.json debe montarse en runtime)
COPY . /app
RUN chown -R app:app /app

USER app

EXPOSE 8501

# healthcheck: verifica que Streamlit responde
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

CMD ["streamlit", "run", "/app/app.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
