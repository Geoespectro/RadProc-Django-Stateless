# =============================================================================
# procesamiento/app.py
# -----------------------------------------------------------------------------
# Módulo de despliegue ligero basado en FastAPI para ejecutar RadProc como
# servicio independiente (stateless function).
#
# Estructura general:
#   1) Imports y configuración base de FastAPI
#   2) Definición de rutas (GET /, POST /run)
#   3) Ejecución de procesamiento mediante process_zip()
# =============================================================================

import io
import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, PlainTextResponse
from procesamiento.service import process_zip


# =============================================================================
# 1️⃣ CONFIGURACIÓN INICIAL DE LA APLICACIÓN FASTAPI
# -----------------------------------------------------------------------------
# Se define una app FastAPI mínima que ejecuta el procesamiento de "suelo"
# con parámetros fijos cargados desde los archivos del core.
# =============================================================================
app = FastAPI(title="RadProc Function (stateless)")

# Rutas y parámetros fijos del servicio
SPECTRALON_PATH = "procesamiento/configs/Spectralon/SRT-99-120.txt"
PARAMS_PATH = "procesamiento/configs/suelo.json"


# =============================================================================
# 2️⃣ ENDPOINT PRINCIPAL (GET /)
# -----------------------------------------------------------------------------
# Endpoint de verificación rápida del estado del servicio.
# Devuelve un texto simple indicando que el servicio está operativo.
# =============================================================================
@app.get("/", response_class=PlainTextResponse)
def root():
    return "RadProc function OK (suelo). Use POST /run with form-data: zip=@file.zip"


# =============================================================================
# 3️⃣ ENDPOINT DE PROCESAMIENTO (POST /run)
# -----------------------------------------------------------------------------
# Recibe un archivo ZIP (form-data) y ejecuta el procesamiento de suelo
# con el archivo Spectralon y la configuración predeterminada incluidos
# dentro del contenedor.
#
# Devuelve el resultado como un archivo ZIP en un StreamingResponse.
# =============================================================================
@app.post("/run")
async def run(zip: UploadFile = File(...)):
    try:
        # Validar tipo MIME (solo aviso, no bloqueante)
        if zip.content_type not in ["application/zip", "application/octet-stream"]:
            pass  # aviso no bloqueante

        # Leer bytes del archivo ZIP recibido
        in_bytes = await zip.read()

        # Cargar Spectralon y configuración por defecto desde el entorno
        spectralon_bytes = open(SPECTRALON_PATH, "rb").read()
        params = json.load(open(PARAMS_PATH, "r", encoding="utf-8"))

        # Ejecutar procesamiento
        out_bytes = process_zip(
            zip_bytes=in_bytes,
            kind="suelo",
            params=params,
            spectralon_txt_bytes=spectralon_bytes,
            spectralon_params_override=None,
        )

        # Responder ZIP como stream
        return StreamingResponse(
            io.BytesIO(out_bytes),
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="salida_suelo.zip"'},
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"processing error: {e}")


# =============================================================================
# FIN DEL MÓDULO
# -----------------------------------------------------------------------------
# Este archivo permite ejecutar el procesador de "suelo" como microservicio
# FastAPI autónomo. Ideal para pruebas, contenedores Docker o integraciones
# serverless (AWS Lambda, Google Cloud Run, etc.).
# =============================================================================

