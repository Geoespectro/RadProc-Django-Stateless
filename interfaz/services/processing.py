# interfaz/services/processing.py

from __future__ import annotations

import os
import json
from io import BytesIO
from typing import Dict, Any, Optional, Tuple

from django.http import HttpResponse

from procesamiento.service import process_zip


# =========================
# Helpers internos
# =========================
def _bytes_from_upload(up) -> bytes:
    """Lee un UploadedFile en chunks y retorna bytes."""
    return b"".join(chunk for chunk in up.chunks())

def _parse_json_obj(raw: str) -> Dict[str, Any]:
    """Parsea JSON a dict. Si está vacío, devuelve {}. Si no es dict, devuelve {}."""
    if not raw:
        return {}
    data = json.loads(raw)
    return data if isinstance(data, dict) else {}

def _get_session_overrides(request, tipo: str) -> Dict[str, Any]:
    """Obtiene overrides temporales guardados en sesión para un tipo dado."""
    all_over = request.session.get("config_overrides", {})
    if isinstance(all_over, dict) and isinstance(all_over.get(tipo), dict):
        return dict(all_over[tipo])  # copia defensiva
    return {}

def _pop_spectralon_tmp_bytes(request) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Si existe 'spectralon_tmp_path' en sesión, lee sus bytes y lo elimina.
    Devuelve (bytes, nombre_archivo) o (None, None) si no existe/falla la lectura.
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

    # obtener nombre antes de borrar
    tmp_name: Optional[str] = os.path.basename(tmp_path)

    # Intentar borrar y limpiar sesión siempre
    try:
        os.remove(tmp_path)
    except Exception:
        pass
    request.session.pop("spectralon_tmp_path", None)
    return content, tmp_name


# =========================
# Servicio principal
# =========================
def process_request_to_zip_response(request) -> HttpResponse:
    """
    Procesa una solicitud POST con:
      - 'tipo_medicion' en {'agua','suelo'}
      - 'zipfile' (archivo ZIP)
      - Opcionales:
          * 'params' o 'params_json' (JSON con overrides generales)
          * 'spectralon_txt' (archivo .txt para esta ejecución)
          * 'spectralon_params' (JSON: overrides específicos de spectralon)
    Respeta overrides en sesión: request.session['config_overrides'][tipo] = {...}
    Usa y limpia 'spectralon_tmp_path' en sesión si existe.

    Devuelve un HttpResponse con el ZIP de resultados o un error (400/405/500).
    """
    # Método
    if request.method != "POST":
        return HttpResponse("Método no permitido", status=405)

    # Tipo de medición
    tipo = (request.POST.get("tipo_medicion") or "").strip().lower()
    if tipo not in ("agua", "suelo"):
        return HttpResponse("Tipo de medición inválido. Use 'agua' o 'suelo'.", status=400)

    # ZIP de entrada
    up = request.FILES.get("zipfile")
    if not up:
        return HttpResponse("Debes adjuntar un archivo ZIP en el campo 'zipfile'.", status=400)

    # Params generales (overrides)
    params_raw = request.POST.get("params") or request.POST.get("params_json") or ""
    try:
        params = _parse_json_obj(params_raw)
    except json.JSONDecodeError:
        return HttpResponse("params inválido (debe ser JSON).", status=400)

    # Fusionar overrides guardados en sesión (ligeros)
    session_over = _get_session_overrides(request, tipo)
    for k, v in session_over.items():
        params.setdefault(k, v)

    # Spectralon TXT (archivo subido o temporal de sesión)
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
        # si no subieron, intentar usar el temporal de sesión y limpiarlo
        spectralon_txt_bytes, spectralon_filename = _pop_spectralon_tmp_bytes(request)

    # Overrides de parámetros de Spectralon (JSON)
    spectralon_params_override: Optional[Dict[str, Any]] = None
    spec_params_raw = request.POST.get("spectralon_params") or ""
    if spec_params_raw:
        try:
            spectralon_params_override = _parse_json_obj(spec_params_raw)
        except json.JSONDecodeError:
            return HttpResponse("spectralon_params inválido (JSON).", status=400)

    # Ejecutar procesamiento con el core (stateless)
    zip_bytes_in = _bytes_from_upload(up)
    try:
        out_zip = process_zip(
            zip_bytes=zip_bytes_in,
            kind=tipo,
            params=params,
            spectralon_txt_bytes=spectralon_txt_bytes,
            spectralon_params_override=spectralon_params_override,
            spectralon_filename=spectralon_filename,  # <-- clave para registrar el nombre real
        )
        # Efectos de sesión (compatibles con la vista actual)
        request.session["zip_nombre"] = getattr(up, "name", "datos.zip")
        request.session["zip_tipo"] = tipo
        request.session["log_resultado"] = "✅ Procesamiento completado. Se descargó el ZIP."

        # Respuesta ZIP (igual que la vista actual)
        resp = HttpResponse(out_zip, content_type="application/zip")
        resp["Content-Disposition"] = f'attachment; filename="resultados_{tipo}.zip"'
        return resp

    except Exception as e:
        # Mantener misma semántica de logging en sesión + HTTP 500
        request.session["log_resultado"] = f"❌ Error en procesamiento: {e}"
        return HttpResponse(f"Error en procesamiento: {e}", status=500)
