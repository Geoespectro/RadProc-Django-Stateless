# Imagen base liviana con Python
FROM python:3.10-slim

# Carpeta de trabajo
WORKDIR /app

# Copiamos requerimientos e instalamos dependencias
COPY docker/core/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código fuente del core
COPY procesamiento/ ./procesamiento/

# Exponemos el puerto del servicio API
EXPOSE 8080

# Comando final: levantar el servidor FastAPI
CMD ["uvicorn", "procesamiento.app:app", "--host", "0.0.0.0", "--port", "8080"]

