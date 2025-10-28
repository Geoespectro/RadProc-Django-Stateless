# =============================================================================
# interfaz/services/processing.py
# -----------------------------------------------------------------------------
# Módulo de integración entre la interfaz web (Django) y el núcleo de
# procesamiento (procesamiento/service.py).
#
# Se encarga de:
#   - Leer los datos y configuraciones enviados desde la interfaz (POST).
#   - Aplicar validaciones previas y combinaciones con overrides de sesión.
#   - Invocar el procesamiento del core (agua/suelo) y devolver el ZIP resultante.
#
# Estructura general:
#   1) Imports y dependencias
#   2) Funciones helper internas
#   3) Servicio principal: process_request_to_zip_response()
# =============================================================================

from __future__ import annotations

import os
import json
from io import BytesIO
from typing import Dict, Any, Optional, Tuple

from django.http import HttpResponse
from procesamiento.service import process_zip, ConfigValidationError


# =============================================================================
# 1️⃣ FUNCIONES AUXILIARES INTERNAS
# -----------------------------------------------------------------------------
# Pequeñas utilidades para lectura de archivos, parsing de JSON y manejo
# de variables de sesión en Django. No tienen efectos secundarios globales.
# =============================================================================
def _bytes_from_upload(up) -> bytes:
    """Lee un UploadedFile en chunks y devuelve sus bytes."""
    return b"".join(chunk for chunk in up.chunks())


def _parse_json_obj(raw: str) -> Dict[str, Any]:
    """
    Convierte una cadena JSON a dict.
    - Si está vacía, devuelve {}.
    - Si no es un dict válido, devuelve {}.
    """
    if not raw:
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}


def _get_session_overrides(request, tipo: str) -> Dict[str, Any]:
    """Obtiene overrides temporales almacenados en sesión para un tipo dado."""
    all_over = request.session.get("config_overrides", {})
    if isinstance(all_over, dict) and isinstance(all_over.get(tipo), dict):
        return dict(all_over[tipo])  # copia defensiva
    return {}


def _pop_spectralon_tmp_bytes(request) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Si existe un 'spectralon_tmp_path' en sesión, lee sus bytes y elimina el archivo.
    Devuelve (bytes, nombre_archivo) o (None, None) si no existe o falla la lectura.
    """
    tmp_path = request.session.get("spectralon_tmp_path")
    if not tmp_path or not os.path.isfile(tmp_path):
        return None, None

    content: Optional[bytes] = None
    try:
        with open(tmp_path, "rb") as f:
            content = f.read()
    except Exception:
        content = None

    tmp_name: Optional[str] = os.path.basename(tmp_path)

    # Limpieza de archivo y sesión
    try:
        os.remove(tmp_path)
    except Exception:
        pass
    request.session.pop("spectralon_tmp_path", None)
    return content, tmp_name


# =============================================================================
# 2️⃣ SERVICIO PRINCIPAL DE PROCESAMIENTO
# -----------------------------------------------------------------------------
# Procesa una solicitud POST con los siguientes campos:
#   - tipo_medicion : {'agua','suelo'}
#   - zipfile       : archivo ZIP con los datos
#   - params / params_json (opcional) : configuración JSON
#   - spectralon_txt (opcional)       : archivo .txt temporal de Spectralon
#   - spectralon_params (opcional)    : configuración JSON de Spectralon
#
# Devuelve un HttpResponse con:
#   - ZIP procesado (status=200)
#   - o errores HTTP 400 / 405 / 422 / 500 según el caso.
# =============================================================================
def process_request_to_zip_response(request) -> HttpResponse:
    """Recibe una solicitud POST desde la interfaz y ejecuta el procesamiento completo."""
    # -------------------------------------------------------------------------
    # Validaciones de método y parámetros básicos
    # -------------------------------------------------------------------------
    if request.method != "POST":
        return HttpResponse("Método no permitido", status=405)

    tipo = (request.POST.get("tipo_medicion") or "").strip().lower()
    if tipo not in ("agua", "suelo"):
        return HttpResponse("Tipo de medición inválido. Use 'agua' o 'suelo'.", status=400)

    up = request.FILES.get("zipfile")
    if not up:
        return HttpResponse("Debes adjuntar un archivo ZIP en el campo 'zipfile'.", status=400)

    if not getattr(up, "name", "").lower().endswith(".zip"):
        return HttpResponse("El archivo debe ser un ZIP válido.", status=400)

    # -------------------------------------------------------------------------
    # Lectura de parámetros (JSON) y combinación con overrides de sesión
    # -------------------------------------------------------------------------
    params_raw = request.POST.get("params") or request.POST.get("params_json") or ""

    try:
        params = _parse_json_obj(params_raw)
    except json.JSONDecodeError:
        return HttpResponse("params inválido (debe ser JSON).", status=400)

    session_over = _get_session_overrides(request, tipo)
    for k, v in session_over.items():
        params.setdefault(k, v)

    # -------------------------------------------------------------------------
    # Lectura de archivo Spectralon (subido o temporal)
    # -------------------------------------------------------------------------
    spectralon_txt_bytes: Optional[bytes] = None
    spectralon_filename: Optional[str] = None

    spec_file = request.FILES.get("spectralon_txt")
    if spec_file:
        max_mb = int(os.getenv("MAX_SPEC_MB", "2"))
        if spec_file.size > max_mb * 1024 * 1024:
            return HttpResponse(f"El archivo Spectralon supera {max_mb} MB.", status=400)
        spectralon_txt_bytes = _bytes_from_upload(spec_file)
        spectralon_filename = getattr(spec_file, "name", None)
    else:
        # Si no se subió, intentar usar el archivo temporal almacenado en sesión
        spectralon_txt_bytes, spectralon_filename = _pop_spectralon_tmp_bytes(request)

    # -------------------------------------------------------------------------
    # Overrides de parámetros específicos de Spectralon
    # -------------------------------------------------------------------------
    spectralon_params_override: Optional[Dict[str, Any]] = None
    spec_params_raw = request.POST.get("spectralon_params") or ""
    if spec_params_raw:
        try:
            spectralon_params_override = _parse_json_obj(spec_params_raw)
        except json.JSONDecodeError:
            return HttpResponse("spectralon_params inválido (JSON).", status=400)

    # -------------------------------------------------------------------------
    # Ejecución del procesamiento (core stateless)
    # Incluye manejo explícito de excepciones de validación y errores genéricos.
    # -------------------------------------------------------------------------
    zip_bytes_in = _bytes_from_upload(up)
    try:
        out_zip = process_zip(
            zip_bytes=zip_bytes_in,
            kind=tipo,
            params=params,
            spectralon_txt_bytes=spectralon_txt_bytes,
            spectralon_params_override=spectralon_params_override,
            spectralon_filename=spectralon_filename,
        )

        # --- Registro en sesión (éxito) ---
        request.session["zip_nombre"] = getattr(up, "name", "datos.zip")
        request.session["zip_tipo"] = tipo
        request.session["log_resultado"] = "✅ Procesamiento completado. Descarga iniciada."

        # --- Respuesta ZIP ---
        resp = HttpResponse(out_zip, content_type="application/zip")
        resp["Content-Disposition"] = f'attachment; filename="resultados_{tipo}.zip"'
        return resp

    except ConfigValidationError as e:
        # ⛔ Error de validación controlado → se devuelve 422
        mensaje = (e.user_message or "Configuración inválida").strip()
        request.session["log_resultado"] = f"❌ Solicitud no procesable (422). {mensaje}"

        resp = HttpResponse(mensaje, content_type="text/plain", status=422)
        resp["X-Radproc-Message"] = mensaje.splitlines()[0][:200]
        return resp

    except Exception as e:
        # ⚠️ Cualquier otro error se maneja como 500 (interno)
        request.session["log_resultado"] = f"❌ Error en procesamiento: {e}"
        return HttpResponse("Error interno del servidor.", status=500, content_type="text/plain")


# =============================================================================
# FIN DEL MÓDULO
# -----------------------------------------------------------------------------
# Este módulo actúa como puente entre la capa web y el núcleo de cálculo.
# Garantiza que las solicitudes se validen correctamente y que las respuestas
# se devuelvan de manera controlada (HTTP 200, 400, 422 o 500 según el caso).
# =============================================================================

