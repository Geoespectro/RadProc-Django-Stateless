# interfaz/views.py — STATeless 

import os
import json
from io import BytesIO
from tempfile import NamedTemporaryFile
from pathlib import Path

from django.shortcuts import render, HttpResponseRedirect
from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

# Delegamos el procesamiento en el servicio (nuevo)
from interfaz.services.processing import process_request_to_zip_response

# === Utilidades locales ======================================================

BASE_DIR = Path(getattr(settings, "BASE_DIR", Path(__file__).resolve().parents[2]))
PROC_DIR = BASE_DIR / "procesamiento"
CONFIGS_DIR = PROC_DIR / "configs"
SPECTRALON_DEFAULT = CONFIGS_DIR / "Spectralon" / "SRT-99-120.txt"

def _load_defaults(tipo: str) -> dict:
    """Carga agua.json o suelo.json desde procesamiento/configs"""
    nombre = f"{tipo}.json"
    cfg_path = (CONFIGS_DIR / nombre)
    if not cfg_path.exists():
        return {}
    with cfg_path.open("r", encoding="utf-8") as f:
        return json.load(f)

def _parse_list_maybe(s: str):
    """Intenta parsear una lista desde string (JSON o coma-sep)."""
    if not s:
        return []
    s = s.strip()
    try:
        # si es JSON válido
        v = json.loads(s)
        return v if isinstance(v, list) else [str(v)]
    except Exception:
        # fallback: coma separada
        return [x.strip() for x in s.split(",") if x.strip()]

def _tmp_dir() -> str:
    return os.getenv("TMP_DIR", "/tmp")

def _session_pop(request, key, default=None):
    val = request.session.get(key, default)
    try:
        request.session.pop(key, None)
    except Exception:
        pass
    return val

# === Vistas ==================================================================

def vista_principal(request):
    """Home con selector, carga de ZIP y (opcional) Spectralon temporal."""
    tipo = request.GET.get("tipo") or request.session.get("zip_tipo") or ""
    # nombre de spectralon para la UI
    nombre_spectralon = "SRT-99-120.txt (por defecto)"
    tmp_path = request.session.get("spectralon_tmp_path")
    if tmp_path and os.path.isfile(tmp_path):
        nombre_spectralon = "Spectralon temporal preparado"

    ctx = {
        "tipo_seleccionado": tipo,
        "nombre_zip": request.session.get("zip_nombre"),
        "log": request.session.get("log_resultado", ""),
        "nombre_spectralon": nombre_spectralon,
    }
    return render(request, "main/index.html", ctx)

@csrf_exempt
def procesar(request):
    """
    Endpoint principal:
    - Requiere 'zipfile' y 'tipo_medicion' ('agua' o 'suelo').
    - Opcional: 'spectralon_txt' (archivo .txt) y 'spectralon_params' (JSON).
    - Opcional: 'params' (JSON) con overrides generales (spectrum, meas_order, ...).
    - Compatibilidad: si existe 'spectralon_tmp_path' en sesión, lo usa y luego lo borra.
    """
    # Ahora delega todo en el servicio, sin cambiar la funcionalidad existente.
    return process_request_to_zip_response(request)


def _build_config_context(tipo: str) -> dict:
    """Arma contexto para configuraciones.html con defaults + overrides en sesión."""
    defaults = _load_defaults(tipo) if tipo in ("agua", "suelo") else {}
    overrides = {}
    if isinstance(request_overrides := defaults, dict):  # placeholder
        pass
    # combinar overrides de sesión si existen
    # (guardamos uno por tipo para no mezclar)
    merged = defaults.copy()
    # leer posibles overrides por tipo
    # guardados como: request.session["config_overrides"][tipo] = { ... }
    return {
        "spectrum": merged.get("spectrum", ""),
        "meas_order": json.dumps(merged.get("meas_order", []), ensure_ascii=False),
        "target_list": json.dumps(merged.get("target_list", []), ensure_ascii=False),
    }


def vista_configuraciones(request):
    """
    Pantalla de configuraciones:
      - Agua / Suelo: muestra tabla con overrides TEMPORALES en sesión.
      - Spectralon: redirige al editor de TXT (no JSON) en /editar_spectralon/.
    """
    tipo = (request.GET.get("tipo") or "").strip().lower()
    if tipo not in ("agua", "suelo", "spectralon"):
        tipo = "agua"

    # Si eligieron Spectralon, vamos al editor de TXT (cambios temporales)
    if tipo == "spectralon":
        return HttpResponseRedirect("/editar_spectralon/")

    # Deshabilitar la opción opuesta para evitar errores de selección
    opciones_tipo = [
        {"valor": "agua",      "etiqueta": "Agua",      "disabled": (tipo == "suelo")},
        {"valor": "suelo",     "etiqueta": "Suelo",     "disabled": (tipo == "agua")},
        {"valor": "spectralon","etiqueta": "Spectralon (parámetros)", "disabled": False},
    ]

    # Cargar defaults y fusionar overrides temporales desde sesión
    defaults = _load_defaults(tipo)
    all_over = request.session.get("config_overrides", {})
    merged = defaults.copy()
    if isinstance(all_over, dict) and isinstance(all_over.get(tipo), dict):
        merged.update(all_over[tipo])

    ctx = {
        "mensaje": request.session.get("log_resultado", ""),
        "opciones_tipo": opciones_tipo,
        "tipo_seleccionado": tipo,
        "config": {
            "spectrum": merged.get("spectrum", ""),
            "meas_order": merged.get("meas_order", []),
            "target_list": merged.get("target_list", []),
        },
    }
    return render(request, "main/configuraciones.html", ctx)


def guardar_config(request):
    """Guarda overrides ligeros en sesión para AGUA/SUELO (solo próxima ejecución)."""
    if request.method != "POST":
        return HttpResponseRedirect("/configuraciones/?tipo=agua")

    tipo = (request.POST.get("tipo") or "").strip().lower()
    if tipo not in ("agua", "suelo"):
        request.session["log_resultado"] = "⚠️ Tipo inválido."
        return HttpResponseRedirect(f"/configuraciones/?tipo=agua")

    # Parseo seguro
    spectrum_raw = request.POST.get("spectrum") or ""
    meas_order_raw = request.POST.get("meas_order") or ""
    target_list_raw = request.POST.get("target_list") or ""

    try:
        spectrum = int(spectrum_raw) if str(spectrum_raw).strip() != "" else None
    except Exception:
        spectrum = None

    try:
        meas_order = json.loads(meas_order_raw) if meas_order_raw.strip().startswith("[") else _parse_list_maybe(meas_order_raw)
    except Exception:
        meas_order = []

    try:
        target_list = json.loads(target_list_raw) if target_list_raw.strip().startswith("[") else _parse_list_maybe(target_list_raw)
    except Exception:
        target_list = []

    over = request.session.get("config_overrides", {})
    if not isinstance(over, dict):
        over = {}
    over[tipo] = {}
    if spectrum is not None:
        over[tipo]["spectrum"] = spectrum
    if meas_order:
        over[tipo]["meas_order"] = meas_order
    if target_list:
        over[tipo]["target_list"] = target_list

    request.session["config_overrides"] = over
    request.session["log_resultado"] = f"✅ Configuración de {tipo} aplicada temporalmente (próxima ejecución)."
    return HttpResponseRedirect(f"/configuraciones/?tipo={tipo}")


def manual_usuario(request):
    # Podés reemplazar por un render a un template de manual si lo tienes
    return HttpResponse("Manual de usuario no disponible aún.", content_type="text/plain")


def descargar_resultados(request):
    # Endpoint deprecado: ahora el ZIP se entrega en la respuesta de /procesar
    return HttpResponse("Descarga directa deshabilitada: el ZIP se entrega al procesar.", status=410)


def _leer_spectralon_para_editar(request) -> tuple[str, str]:
    """
    Devuelve (contenido, etiqueta_nombre) para precargar el editor:
    - Si hay un spectralon temporal subido/guardado, lo muestra.
    - En caso contrario, carga el por defecto.
    """
    tmp_path = request.session.get("spectralon_tmp_path")
    if tmp_path and os.path.isfile(tmp_path):
        try:
            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                return (f.read(), "Temporal (subido)")
        except Exception:
            pass
    # Por defecto
    try:
        with open(SPECTRALON_DEFAULT, "r", encoding="utf-8", errors="ignore") as f:
            return (f.read(), SPECTRALON_DEFAULT.name)
    except Exception:
        return ("", "(no disponible)")


def editar_spectralon(request):
    """Editor de compatibilidad: NO persiste; guarda en /tmp y referencia en sesión."""
    contenido, nombre = _leer_spectralon_para_editar(request)
    # Determinar tipo_actual (para botón cancelar)
    tipo_actual = (request.GET.get("tipo") or request.session.get("zip_tipo") or "agua").lower()
    return render(request, "main/editar_spectralon.html", {
        "contenido_txt": contenido,
        "tipo_actual": tipo_actual,
        "nombre_actual": nombre,
    })


@csrf_exempt
def guardar_spectralon(request):
    """
    Guarda el contenido editado de Spectralon en un archivo temporal en /tmp
    y almacena su ruta en sesión para la PRÓXIMA ejecución.
    Redirige a Configuraciones preservando el tipo (agua/suelo).
    """
    if request.method != "POST":
        return HttpResponseRedirect("/editar_spectralon/")

    contenido = request.POST.get("contenido_txt", "")
    if not contenido:
        request.session["log_resultado"] = "⚠️ El contenido está vacío; se seguirá usando el Spectralon por defecto."
        return HttpResponseRedirect("/editar_spectralon/")

    # 🔧 Tomar el tipo en este orden: ?tipo -> hidden POST -> sesión -> 'agua'
    tipo_actual = (
        request.GET.get("tipo")
        or request.POST.get("tipo_actual")
        or request.session.get("zip_tipo")
        or "agua"
    ).lower()

    # Escribir a archivo temporal en /tmp
    with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=_tmp_dir(), suffix=".txt") as tmp:
        tmp.write(contenido)
        tmp_path = tmp.name

    # Guardar referencia de ruta en sesión (ligera)
    request.session["spectralon_tmp_path"] = tmp_path
    request.session["log_resultado"] = "✅ Spectralon editado cargado temporalmente. Se aplicará en la próxima ejecución."

    return HttpResponseRedirect(f"/configuraciones/?tipo={tipo_actual}")


@csrf_exempt
def cambiar_spectralon(request):
    """
    Recibe un archivo .txt y lo guarda TEMPORALMENTE en /tmp para la PRÓXIMA ejecución.
    (Compatibilidad con el botón 'Cambiar...' de la página principal)
    """
    if request.method != "POST":
        return HttpResponseRedirect("/")

    up = request.FILES.get("nuevo_spectralon")
    if not up:
        request.session["log_resultado"] = "⚠️ No se adjuntó ningún archivo Spectralon."
        return HttpResponseRedirect("/")

    max_mb = int(os.getenv("MAX_SPEC_MB", "2"))
    if up.size > max_mb * 1024 * 1024:
        request.session["log_resultado"] = f"⚠️ El archivo Spectralon supera {max_mb} MB. Intente con uno más pequeño."
        return HttpResponseRedirect("/")

    with NamedTemporaryFile("wb", delete=False, dir=_tmp_dir(), suffix=".txt") as tmp:
        for chunk in up.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    request.session["spectralon_tmp_path"] = tmp_path
    request.session["log_resultado"] = "✅ Spectralon cargado temporalmente. Se aplicará en la próxima ejecución."
    return HttpResponseRedirect("/")


@csrf_exempt
def limpiar_sesion(request):
    """Elimina estado de sesión (sin tocar disco del proyecto)."""
    if request.method == "POST":
        keys = [
            "log_resultado", "zip_nombre", "zip_tipo",
            "config_overrides",
            "spectralon_tmp_path",
        ]
        for k in keys:
            request.session.pop(k, None)
        request.session.flush()
        return HttpResponseRedirect("/")
    return HttpResponseRedirect("/")




    




