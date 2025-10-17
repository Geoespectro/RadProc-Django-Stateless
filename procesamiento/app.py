# app.py
import io, json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, PlainTextResponse
from procesamiento.service import process_zip

app = FastAPI(title="RadProc Function (stateless)")

# Rutas (hardcode de suelo + spectralon interno)
SPECTRALON_PATH = "procesamiento/configs/Spectralon/SRT-99-120.txt"
PARAMS_PATH = "procesamiento/configs/suelo.json"

@app.get("/", response_class=PlainTextResponse)
def root():
    return "RadProc function OK (suelo). Use POST /run with form-data: zip=@file.zip"

@app.post("/run")
async def run(zip: UploadFile = File(...)):
    try:
        if zip.content_type not in ["application/zip", "application/octet-stream"]:
            # no exigimos, pero avisamos
            pass

        # leer bytes del ZIP
        in_bytes = await zip.read()

        # cargar spectr + params desde imagen
        spectralon_bytes = open(SPECTRALON_PATH, "rb").read()
        params = json.load(open(PARAMS_PATH, "r", encoding="utf-8"))

        out_bytes = process_zip(
            zip_bytes=in_bytes,
            kind="suelo",
            params=params,
            spectralon_txt_bytes=spectralon_bytes,
            spectralon_params_override=None,
        )

        return StreamingResponse(
            io.BytesIO(out_bytes),
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="salida_suelo.zip"'},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"processing error: {e}")
