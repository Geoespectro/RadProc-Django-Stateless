# =====================================================
# RADPROC CORE - Procesamiento espectral (agua/suelo)
# =====================================================
FROM python:3.10-slim

WORKDIR /app

# Evitar buffering en logs
ENV PYTHONUNBUFFERED=1
ENV TZ=America/Argentina/Buenos_Aires

# Copiar procesamiento y dependencias
COPY procesamiento/ ./procesamiento/
COPY docker/core/requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar entrypoint
COPY docker/core/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
