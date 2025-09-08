# interfaz/views.py — STATeless (listo para reemplazar)

import os
import json
import zipfile
import shutil
from pathlib import Path
from datetime import datetime

from django.shortcuts import render, HttpResponseRedirect
from django.http import HttpResponse, FileResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

# Orquestador stateless
from procesamiento.service import process_zip


# ===========================
# Helpers internos
# ===========================
def _configs_dir() -> Path:
    return Path(settings.BASE_DIR) / "procesamiento" / "configs"

def _load_defaults(tipo: str) -> dict:
    """
    Carga los defaults de procesamiento desde procesamiento/configs/<tipo>.json
    (solo lectura, parte de la imagen). Si no existe, retorna dict vacío.
    """
    cfg_path = _configs_dir() / f"{tipo}.json"
    if cfg_path.exists():
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _resolve_config_for_view(request, tipo: str) -> dict:
    """
    Arma el dict 'config' que espera el template:
    - Usa overrides guardados en sesión si existen para ese tipo
    - Si no, usa defaults del JSON correspondiente
    - Devuelve valores 'stringificables' para los <input> (lists como JSON)
    """
    overrides = request.session.get("config_overrides")
    if isinstance(overrides, dict) and overrides.get("tipo") == tipo:
        spectrum = overrides.get("spectrum", "")
        meas_order = overrides.get("meas_order", [])
        target_list = overrides.get("target_list", [])
    else:
        defaults = _load_defaults(tipo)
        spectrum = defaults.get("spectrum", "")
        meas_order = defaults.get("meas_order", [])
        target_list = defaults.get("target_list", [])

    return {
        "spectrum": spectrum,
        "meas_order": json.dumps(meas_order, ensure_ascii=False),
        "target_list": json.dumps(target_list, ensure_ascii=False),
    }


# ===========================
# Página principal
# ===========================
def vista_principal(request):
    nombre_zip = request.session.get('zip_nombre', '')
    tipo = request.session.get('zip_tipo', '')
    log = request.session.pop('log_resultado', '')
    spectralon_actual = request.session.get("spectralon_actual", "SRT-99-120.txt")
    log_eventos = request.session.get("log_eventos", [])

    return render(request, 'main/index.html', {
        'nombre_zip': nombre_zip,
        'tipo_seleccionado': tipo,
        'log': log,
        'nombre_spectralon': spectralon_actual,
        'eventos': log_eventos,
    })


# ===========================
# Manual de usuario
# ===========================
def manual_usuario(request):
    return render(request, 'docs/manual_usuario.html')


# ===========================
# Procesar (STATeless: un paso)
# ===========================
@csrf_exempt
def procesar(request):
    if request.method != 'POST':
        return HttpResponse("Método no permitido", status=405)

    tipo = (request.POST.get('tipo_medicion') or '').lower()
    if tipo not in ('agua', 'suelo'):
        return HttpResponse("Tipo de medición inválido. Use 'agua' o 'suelo'.", status=400)

    f = request.FILES.get('zipfile')
    if not f:
        return HttpResponse("Debes adjuntar un archivo ZIP en el campo 'zipfile'.", status=400)

    params_raw = request.POST.get('params_json') or request.POST.get('params') or ""
    try:
        params = json.loads(params_raw) if params_raw else {}
        if not isinstance(params, dict):
            raise ValueError("params debe ser un objeto JSON")
    except Exception:
        return HttpResponse("params inválido (debe ser JSON).", status=400)

    # Leer ZIP en memoria (sin escribir a disco)
    zip_bytes = b''.join(chunk for chunk in f.chunks())

    # Ejecutar orquestador
    try:
        out_zip = process_zip(zip_bytes, tipo, params)
    except Exception as e:
        return HttpResponse(f"Error en procesamiento: {e}", status=500)

    # Descarga directa
    resp = HttpResponse(out_zip, content_type="application/zip")
    resp['Content-Disposition'] = f'attachment; filename="resultados_{tipo}.zip"'
    return resp


# ===========================
# Configuraciones (acceso libre; se abre según ?tipo=)
# ===========================
@csrf_exempt
def vista_configuraciones(request):
    """
    Reglas:
    - 'base_tipo' es el tipo elegido en la pantalla principal (agua|suelo) y
      se usa para bloquear la edición del otro tipo dentro de Configuraciones.
    - Si el usuario mira 'spectralon', no se cambia 'base_tipo' y no se bloquea Spectralon.
    - Al entrar/salir de Config, el tipo elegido en la principal se conserva en sesión
      para que la pantalla principal lo muestre seleccionado al volver.
    """

    # Tipo pedido explícitamente en la URL de Config (agua|suelo|spectralon)
    view_tipo = (request.GET.get("tipo") or "").lower()

    # Tipo base (el elegido en la pantalla principal). Si llega por GET (agua|suelo),
    # lo fijamos en sesión para que al volver a la principal quede seleccionado.
    if view_tipo in ("agua", "suelo"):
        base_tipo = view_tipo
        request.session["zip_tipo"] = base_tipo  # conserva selección al volver
    else:
        # No nos sobreescribimos con 'spectralon'; tomamos lo último válido
        base_tipo = (request.session.get("zip_tipo") or "").lower()
        if base_tipo not in ("agua", "suelo"):
            # Si no hay contexto previo, por defecto usamos 'suelo' solo internamente
            base_tipo = "suelo"

    # Campos editables: solo para agua/suelo (Spectralon tiene su editor aparte)
    editable_fields = _resolve_config_for_view(request, view_tipo) if view_tipo in ("agua", "suelo") else {}

    # Construcción del selector con bloqueo coherente:
    # - El tipo base queda habilitado (editable) si lo estamos visualizando;
    #   el tipo contrario queda bloqueado para evitar mezclar configuraciones.
    # - Spectralon siempre habilitado.
    if base_tipo == "agua":
        opciones_tipo = [
            {"valor": "agua", "etiqueta": "Agua", "disabled": False},   # permitido
            {"valor": "suelo", "etiqueta": "Suelo", "disabled": True},  # bloqueado
            {"valor": "spectralon", "etiqueta": "Spectralon", "disabled": False},
        ]
    else:  # base_tipo == "suelo"
        opciones_tipo = [
            {"valor": "agua", "etiqueta": "Agua", "disabled": True},    # bloqueado
            {"valor": "suelo", "etiqueta": "Suelo", "disabled": False}, # permitido
            {"valor": "spectralon", "etiqueta": "Spectralon", "disabled": False},
        ]

    # 'tipo_seleccionado' es lo que se está viendo ahora en Config:
    # puede ser 'agua'/'suelo' o 'spectralon' (para que el select muestre esa pestaña activa).
    tipo_seleccionado = view_tipo if view_tipo in ("agua", "suelo", "spectralon") else base_tipo

    mensaje = request.session.pop("mensaje_config", None)

    return render(request, "main/configuraciones.html", {
        "tipo": tipo_seleccionado,         # lo que se está viendo (incluye 'spectralon')
        "config": editable_fields,         # solo tiene datos si se ve agua/suelo
        "tipo_seleccionado": tipo_seleccionado,
        "opciones_tipo": opciones_tipo,    # bloqueos en función de base_tipo
        "mensaje": mensaje
    })



# ===========================
# Guardar configuración (STATeless: en sesión)
# ===========================
@csrf_exempt
def guardar_config(request):
    if request.method == 'POST':
        tipo = (request.POST.get("tipo") or "agua").lower()
        if tipo not in ("agua", "suelo"):
            request.session['log_resultado'] = "⚠️ Tipo inválido para configuración."
            return HttpResponseRedirect("/configuraciones/?tipo=suelo")

        try:
            spectrum = int(request.POST.get("spectrum", 15))
        except ValueError:
            spectrum = 15

        try:
            meas_order = json.loads(request.POST.get("meas_order", "[]"))
        except json.JSONDecodeError:
            meas_order = []

        try:
            target_list = json.loads(request.POST.get("target_list", "[]"))
        except json.JSONDecodeError:
            target_list = []

        # Guardamos overrides en sesión (no persistimos en disco)
        request.session["config_overrides"] = {
            "tipo": tipo,
            "spectrum": spectrum,
            "meas_order": meas_order,
            "target_list": target_list
        }
        request.session["config_cargada"] = True
        request.session["configuracion_habilitada"] = True  # mantiene compatibilidad de UI
        request.session['log_resultado'] = f"✅ Configuración temporal guardada para {tipo.upper()}"

        return HttpResponseRedirect(f"/configuraciones/?tipo={tipo}")

    return HttpResponseRedirect("/")


# ===========================
# Subir ZIP (compatibilidad): ahora procesa y descarga
# ===========================
@csrf_exempt
def subir_zip(request):
    if request.method == 'POST' and request.FILES.get('zipfile'):
        zip_file = request.FILES['zipfile']
        tipo_medicion = (request.POST.get('tipo_medicion') or '').lower()
        if tipo_medicion not in ['agua', 'suelo']:
            return HttpResponse("Tipo de medición inválido.", status=400)

        # Mezclar overrides de sesión si coinciden con el tipo
        overrides = request.session.get("config_overrides", {})
        if isinstance(overrides, dict) and overrides.get("tipo") == tipo_medicion:
            params = {
                "spectrum": overrides.get("spectrum"),
                "meas_order": overrides.get("meas_order"),
                "target_list": overrides.get("target_list"),
            }
        else:
            params_raw = request.POST.get('params_json') or request.POST.get('params') or ""
            try:
                params = json.loads(params_raw) if params_raw else {}
                if not isinstance(params, dict):
                    params = {}
            except Exception:
                params = {}

        # Procesar inmediatamente (STATeless)
        zip_bytes = b''.join(chunk for chunk in zip_file.chunks())
        try:
            out_zip = process_zip(zip_bytes, tipo_medicion, params)
        except Exception as e:
            return HttpResponse(f"Error en procesamiento: {e}", status=500)

        resp = HttpResponse(out_zip, content_type="application/zip")
        resp['Content-Disposition'] = f'attachment; filename="resultados_{tipo_medicion}.zip"'
        return resp

    return HttpResponseRedirect('/')


# ===========================
# Compatibilidad: informar nuevo flujo
# ===========================
@csrf_exempt
def procesar_datos(request):
    if request.method == 'POST':
        request.session['log_resultado'] = "ℹ️ El procesamiento ahora es directo desde 'Procesar y descargar'."
        return HttpResponseRedirect('/')
    return HttpResponse("Método no permitido", status=405)


def descargar_resultados(request):
    return HttpResponse("Este flujo ahora devuelve la descarga directa tras procesar. No hay resultados persistidos.")


# ===========================
# Sesión / Spectralon (modo sesión)
# ===========================
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseRedirect
from django.conf import settings
import os, shutil

@csrf_exempt
def limpiar_sesion(request):
    if request.method == 'POST':
        # 1) Limpiar carpetas temporales según el tipo que se venía usando
        tipo = (request.session.get("zip_tipo") or "").lower()
        carpeta = None
        if tipo == "agua":
            carpeta = os.path.join(settings.BASE_DIR, "procesamiento", "input_w")
        elif tipo == "suelo":
            carpeta = os.path.join(settings.BASE_DIR, "procesamiento", "input")

        if carpeta and os.path.exists(carpeta):
            shutil.rmtree(carpeta, ignore_errors=True)
            os.makedirs(carpeta, exist_ok=True)

        # 2) Borrar claves de estado de la sesión (incluye el mensaje del log)
        for k in [
            "log_resultado", "zip_nombre", "zip_tipo",
            "config_cargada", "datos_cargados", "configuracion_habilitada",
            "acceso_spectralon", "spectralon_actual"
        ]:
            request.session.pop(k, None)

        # 3) Vaciar por completo la sesión (backstop)
        request.session.flush()

        # 4) Volver a la principal
        return HttpResponseRedirect('/')

    # GET u otros métodos → redirigir sin cambios
    return HttpResponseRedirect('/')



def editar_spectralon(request):
    if not request.session.get("acceso_spectralon"):
        return HttpResponseRedirect("/clave_spectralon/")

    contenido = request.session.get("spectralon_txt", "Cargar o editar Spectralon aquí (sesión).")
    tipo_actual = request.session.get("zip_tipo", "spectralon")
    return render(request, "main/editar_spectralon.html", {
        "contenido_txt": contenido,
        "tipo_actual": tipo_actual,
    })


@csrf_exempt
def guardar_spectralon(request):
    if request.method == "POST":
        nuevo_contenido = request.POST.get("contenido_txt", "")
        request.session["spectralon_txt"] = nuevo_contenido
        request.session["log_resultado"] = "✅ Spectralon cargado en sesión para esta ejecución."
        tipo_original = request.session.get("zip_tipo", "spectralon")
        return HttpResponseRedirect(f"/configuraciones/?tipo={tipo_original}")
    return HttpResponseRedirect("/")


@csrf_exempt
def cambiar_spectralon(request):
    if request.method == "POST" and request.FILES.get("nuevo_spectralon"):
        archivo = request.FILES["nuevo_spectralon"]
        if not archivo.name.endswith(".txt"):
            request.session["log_resultado"] = "⚠️ El archivo debe tener extensión .txt"
            return HttpResponseRedirect("/")
        contenido = archivo.read().decode("utf-8", errors="ignore")
        request.session["spectralon_txt"] = contenido
        request.session["spectralon_actual"] = archivo.name
        request.session["log_resultado"] = f"✅ Spectralon cargado en sesión: {archivo.name}"
        return HttpResponseRedirect("/")
    return HttpResponseRedirect("/")


def clave_spectralon(request):
    tipo_actual = request.session.get("zip_tipo", "spectralon")
    if request.method == "POST":
        clave = request.POST.get("clave", "")
        if clave == "1234":
            request.session["acceso_spectralon"] = True
            return HttpResponseRedirect("/editar_spectralon/")
        else:
            return render(request, "main/clave_spectralon.html", {
                "error": "❌ Clave incorrecta.",
                "tipo_actual": tipo_actual
            })
    return render(request, "main/clave_spectralon.html", {
        "tipo_actual": tipo_actual
    })



