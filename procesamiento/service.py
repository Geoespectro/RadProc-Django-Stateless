# =============================================================================
# procesamiento/service.py
# -----------------------------------------------------------------------------
# Módulo principal de orquestación del procesamiento radiométrico.
# Se encarga de:
#   - Validar y descomprimir el paquete ZIP recibido.
#   - Invocar los procesadores específicos (agua / suelo).
#   - Gestionar el archivo de referencia Spectralon.
#   - Generar y devolver el ZIP de salida con metadata consolidada.
#
# Estructura general:
#   1) Registro de procesadores disponibles
#   2) Configuración de límites y rutas
#   3) Funciones utilitarias (ZIP, rutas, etc.)
#   4) Excepciones de dominio
#   5) API principal (process_zip / process_folder_to_zip / run_processing_from_json_file)
# =============================================================================

from __future__ import annotations
import os
import json
import shutil
from io import BytesIO
from typing import Dict, Any, Literal, Optional, List, Tuple, Callable
from tempfile import TemporaryDirectory
import zipfile
from datetime import datetime, timezone, timedelta
import hashlib
import importlib
from contextlib import contextmanager
import re
from procesamiento.validators.config_validator import validar_configuracion


# =============================================================================
# 1️⃣ REGISTRO DE PROCESADORES DISPONIBLES
# -----------------------------------------------------------------------------
# Define qué tipos de procesamiento están habilitados y sus rutas de módulo.
# Cada módulo debe exponer una función `run(input_dir, output_dir, config)`.
# =============================================================================
_PROCESSOR_MODULES: dict[str, str] = {
    "agua": "procesamiento.processors.agua",
    "suelo": "procesamiento.processors.suelo",
}

def get_registered_kinds() -> List[str]:
    return list(_PROCESSOR_MODULES.keys())

def _load_runner(kind: str) -> Callable[..., Dict[str, Any]]:
    """Carga dinámicamente el módulo del procesador solicitado."""
    try:
        module_path = _PROCESSOR_MODULES[kind]
    except KeyError:
        disponibles = ", ".join(sorted(get_registered_kinds()))
        raise ValueError(f"kind inválido: {kind!r}. Disponibles: {disponibles}.")
    mod = importlib.import_module(module_path)
    if not hasattr(mod, "run"):
        raise RuntimeError(f"El módulo {module_path} no expone `run`.")
    return getattr(mod, "run")


# =============================================================================
# 2️⃣ CONFIGURACIÓN GLOBAL DE LÍMITES Y RUTAS
# -----------------------------------------------------------------------------
# Establece límites de tamaño y cantidad de archivos, así como rutas temporales.
# =============================================================================
def _mb_to_bytes(mb: int) -> int:
    return int(mb) * 1024 * 1024

MAX_ZIP_BYTES = _mb_to_bytes(int(os.getenv("MAX_ZIP_MB", "200")))
MAX_ZIP_FILES = int(os.getenv("MAX_ZIP_FILES", "20000"))
MAX_NAME_LEN = int(os.getenv("MAX_ZIP_NAME_LEN", "255"))
MAX_SINGLE_UNCOMP_BYTES = _mb_to_bytes(int(os.getenv("MAX_SINGLE_MB", "512")))
MAX_TOTAL_UNCOMP_BYTES  = _mb_to_bytes(int(os.getenv("MAX_TOTAL_MB", "2048")))
TMP_DIR = os.getenv("TMP_DIR", "/tmp")


# =============================================================================
# 3️⃣ FUNCIONES DE RUTA Y CONFIGURACIÓN BASE
# -----------------------------------------------------------------------------
# Carga configuraciones predeterminadas según el tipo de procesamiento.
# =============================================================================
def _procesamiento_dir() -> str:
    return os.path.dirname(__file__)

def _configs_dir() -> str:
    return os.path.join(_procesamiento_dir(), "configs")

def _load_defaults(kind: str) -> Dict[str, Any]:
    """Carga el archivo JSON de configuración predeterminada."""
    cfg_path = os.path.join(_configs_dir(), f"{kind}.json")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# 4️⃣ FUNCIONES UTILITARIAS GENERALES
# -----------------------------------------------------------------------------
# Incluye manejo de contexto, lectura/escritura ZIP segura y control de rutas.
# =============================================================================
@contextmanager
def _chdir(path: str):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)

def _is_symlink(zipinfo: zipfile.ZipInfo) -> bool:
    """Detecta si un archivo dentro del ZIP es un enlace simbólico."""
    return ((zipinfo.external_attr >> 16) & 0o170000) == 0o120000

def _safe_join(base: str, *paths: str) -> str:
    """Evita vulnerabilidades tipo Zip-Slip al validar rutas de extracción."""
    dest = os.path.normpath(os.path.join(base, *paths))
    base_abs = os.path.abspath(base)
    dest_abs = os.path.abspath(dest)
    if not (dest_abs == base_abs or dest_abs.startswith(base_abs + os.sep)):
        raise ValueError("Ruta insegura detectada al extraer ZIP (posible Zip-Slip).")
    return dest

def _zip_extract_all(zip_bytes: bytes, dest_dir: str) -> None:
    """Extrae un ZIP validando límites de tamaño, cantidad y nombres de archivos."""
    if len(zip_bytes) > MAX_ZIP_BYTES:
        raise ValueError(f"ZIP demasiado grande: {len(zip_bytes)} bytes (límite {MAX_ZIP_BYTES} bytes).")

    total_uncompressed = 0
    with zipfile.ZipFile(BytesIO(zip_bytes), "r") as zf:
        infolist = zf.infolist()
        if len(infolist) > MAX_ZIP_FILES:
            raise ValueError(f"ZIP con demasiados archivos: {len(infolist)} (límite {MAX_ZIP_FILES}).")

        for info in infolist:
            filename = info.filename
            if filename.endswith("/") or filename.endswith("\\"):
                continue

            if os.path.isabs(filename):
                raise ValueError(f"Ruta absoluta no permitida en ZIP: {filename}")
            norm = os.path.normpath(filename)
            if ".." in norm.split(os.sep):
                raise ValueError(f"Ruta con '..' no permitida en ZIP: {filename}")
            if len(os.path.basename(norm)) > MAX_NAME_LEN:
                raise ValueError(f"Nombre de archivo demasiado largo en ZIP: {filename}")
            if _is_symlink(info):
                raise ValueError(f"Symlink no permitido en ZIP: {filename}")

            uncomp = info.file_size
            if uncomp > MAX_SINGLE_UNCOMP_BYTES:
                raise ValueError(f"Archivo descomprimido excede el límite: {filename} ({uncomp} bytes).")
            total_uncompressed += uncomp
            if total_uncompressed > MAX_TOTAL_UNCOMP_BYTES:
                raise ValueError("Tamaño total descomprimido del ZIP excede el límite.")

            dest_path = _safe_join(dest_dir, norm)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with zf.open(info, "r") as src, open(dest_path, "wb") as dst:
                for chunk in iter(lambda: src.read(1024 * 1024), b""):
                    dst.write(chunk)

def _zip_dir_to_bytes(src_dir: str, extra_files: Optional[List[Tuple[str, bytes]]] = None) -> bytes:
    """Comprime un directorio completo en memoria, agregando archivos extra si se indican."""
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src_dir):
            for name in files:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, src_dir)
                zf.write(full, rel)
        if extra_files:
            for rel, data in extra_files:
                zf.writestr(rel, data)
    buf.seek(0)
    return buf.read()

def _list_files(base: str) -> List[str]:
    """Lista recursivamente todos los archivos de un directorio base."""
    out: List[str] = []
    for root, _, files in os.walk(base):
        for name in files:
            out.append(os.path.join(root, name))
    return out

def _move_strays(tmp_root: str, in_dir: str, out_dir: str) -> List[str]:
    """
    Mueve a out_dir/_strays cualquier archivo creado dentro de tmp_root
    que no esté bajo in_dir ni bajo out_dir. Devuelve las rutas destino.
    """
    dests: List[str] = []
    stray_base = os.path.join(out_dir, "_strays")
    for root, _, files in os.walk(tmp_root):
        for name in files:
            full = os.path.join(root, name)
            if full.startswith(in_dir + os.sep) or full.startswith(out_dir + os.sep):
                continue
            rel = os.path.relpath(full, tmp_root)
            dest = os.path.join(stray_base, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                shutil.move(full, dest)
            except Exception:
                try:
                    shutil.copy2(full, dest)
                    os.remove(full)
                except Exception:
                    continue
            dests.append(dest)
    return dests

def _normalize_spectralon_filename(name: Optional[str]) -> str:
    """Normaliza el nombre del archivo TXT de Spectralon para evitar problemas de ruta."""
    base = os.path.basename(name or "uploaded_spectralon.txt")
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base)
    if not base.lower().endswith(".txt"):
        base += ".txt"
    if len(base) > MAX_NAME_LEN:
        base = base[-MAX_NAME_LEN:]
    return base


# =============================================================================
# 5️⃣ EXCEPCIONES DEL DOMINIO
# -----------------------------------------------------------------------------
# Define excepciones específicas de este módulo para capturar y reportar
# errores controlados (por ejemplo, validación de configuración).
# =============================================================================
class ConfigValidationError(Exception):
    """Error de validación entre set de datos y configuración."""
    def __init__(self, user_message: str, details: dict | None = None):
        super().__init__(user_message)
        self.user_message = user_message
        self.details = details or {}


# =============================================================================
# 6️⃣ API PRINCIPAL DE ORQUESTACIÓN
# -----------------------------------------------------------------------------
# Funciones de alto nivel que ejecutan el flujo completo de procesamiento.
# - process_zip: recibe un ZIP y devuelve un ZIP procesado.
# - process_folder_to_zip: procesa una carpeta local.
# - run_processing_from_json_file: ejecuta pruebas directas con JSON.
# =============================================================================
def process_zip(
    zip_bytes: bytes,
    kind: Literal["agua", "suelo"],
    params: Optional[Dict[str, Any]] = None,
    spectralon_txt_bytes: Optional[bytes] = None,
    spectralon_params_override: Optional[Dict[str, Any]] = None,
    spectralon_filename: Optional[str] = None,
) -> bytes:
    """
    Procesa un paquete ZIP con datos radiométricos.
    Incluye validación previa de configuración antes del procesamiento.
    """

    defaults = _load_defaults(kind)
    cfg: Dict[str, Any] = {**defaults, **(params or {})}

    with TemporaryDirectory(dir=TMP_DIR) as tmp:
        in_dir = os.path.join(tmp, "in")
        out_dir = os.path.join(tmp, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        # Guardar y extraer temporalmente el ZIP
        tmp_zip_path = os.path.join(tmp, "upload.zip")
        with open(tmp_zip_path, "wb") as f:
            f.write(zip_bytes)
        with zipfile.ZipFile(tmp_zip_path, "r") as z:
            z.extractall(in_dir)

        # --- VALIDACIÓN PREVIA ---
        validacion = validar_configuracion(in_dir, cfg)
        if not validacion["valido"]:
            raise ConfigValidationError(
                user_message=f"Configuración inválida: {validacion['motivo']}",
                details={
                    "kind": kind,
                    "spectrum": cfg.get("spectrum"),
                    "meas_order": cfg.get("meas_order"),
                    "target_list": cfg.get("target_list"),
                },
            )

        # Reextracción segura (mantiene la lógica original)
        _zip_extract_all(zip_bytes, in_dir)

        # --- Cargar Spectralon si vino adjunto ---
        if spectralon_txt_bytes:
            spec_dir = os.path.join(in_dir, "configs", "Spectralon")
            os.makedirs(spec_dir, exist_ok=True)
            spec_name = _normalize_spectralon_filename(spectralon_filename)
            spec_path = os.path.join(spec_dir, spec_name)
            with open(spec_path, "wb") as f:
                f.write(spectralon_txt_bytes)
            cfg["spectralon_file"] = spec_path

        # ✅ Fusión defensiva de parámetros Spectralon
        if spectralon_params_override:
            base_params = cfg.get("spectralon_params")
            if not isinstance(base_params, dict):
                base_params = {}
            base_params.update(spectralon_params_override)
            cfg["spectralon_params"] = base_params

        # Variables de entorno y rutas
        old_out, old_in = os.environ.get("OUTPUT_DIR"), os.environ.get("INPUT_DIR")
        os.environ["OUTPUT_DIR"], os.environ["INPUT_DIR"] = out_dir, in_dir
        cfg["output_dir"], cfg["input_dir"] = out_dir, in_dir

        try:
            runner = _load_runner(kind)
            with _chdir(out_dir):
                meta = runner(input_dir=in_dir, output_dir=out_dir, config=cfg)
        finally:
            if old_out is None:
                os.environ.pop("OUTPUT_DIR", None)
            else:
                os.environ["OUTPUT_DIR"] = old_out
            if old_in is None:
                os.environ.pop("INPUT_DIR", None)
            else:
                os.environ["INPUT_DIR"] = old_in

        # --- Consolidar salida ---
        produced_abs = list(meta.get("produced") or []) if meta and meta.get("produced") else _list_files(out_dir)
        if not produced_abs:
            moved = _move_strays(tmp_root=tmp, in_dir=in_dir, out_dir=out_dir)
            produced_abs = _list_files(out_dir) if moved else []

        meta2 = dict(meta or {})
        produced_rel = []
        for p in produced_abs:
            try:
                rel = os.path.relpath(p, out_dir)
                if rel.startswith(".."):
                    rel = p
            except Exception:
                rel = p
            produced_rel.append(rel)
        meta2["produced"] = produced_rel

        # Campaña detectada (si existe)
        campaign = ""
        if produced_rel:
            parts = produced_rel[0].split(os.sep)
            if parts:
                campaign = parts[0]
        if campaign:
            meta2.setdefault("campaigns", [])
            if campaign not in meta2["campaigns"]:
                meta2["campaigns"].append(campaign)
            meta2["campaign"] = campaign

        # Metadata final
        meta2["kind"] = kind
        meta2["run_id"] = datetime.now(timezone(timedelta(hours=-3))).isoformat()
        meta2["processor_version"] = "radproc-web 1.0.0"
        meta2.setdefault("notes", "Procesamiento stateless")
        meta2["params_effective"] = cfg

        # Información de entrada
        spec_src = "uploaded" if spectralon_txt_bytes else "default"
        spec_name = os.path.basename(cfg.get("spectralon_file", "SRT-99-120.txt"))
        spec_sha = hashlib.sha256(spectralon_txt_bytes).hexdigest() if spectralon_txt_bytes else ""
        meta2["inputs"] = {
            "zip_name": meta2.get("inputs", {}).get("zip_name", "upload.zip"),
            "zip_size_bytes": len(zip_bytes),
            "spectralon": {"source": spec_src, "name": spec_name, "sha256": spec_sha},
        }

        meta_bytes = json.dumps(meta2, ensure_ascii=False, indent=2).encode("utf-8")
        return _zip_dir_to_bytes(out_dir, extra_files=[("metadata.json", meta_bytes)])


def process_folder_to_zip(
    input_dir: str,
    kind: Literal["agua", "suelo"],
    params: Optional[Dict[str, Any]] = None,
    spectralon_txt_path: Optional[str] = None,
    spectralon_params_override: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Procesa una carpeta local como si fuera un ZIP subido.
    Mantiene la misma lógica de validación y salida que process_zip().
    """
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"input_dir no existe o no es carpeta: {input_dir}")

    defaults = _load_defaults(kind)
    cfg: Dict[str, Any] = {**defaults, **(params or {})}

    with TemporaryDirectory(dir=TMP_DIR) as tmp:
        in_dir = os.path.join(tmp, "in")
        out_dir = os.path.join(tmp, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        # Copia superficial de archivos
        for root, dirs, files in os.walk(input_dir):
            rel_root = os.path.relpath(root, input_dir)
            dest_root = os.path.join(in_dir, rel_root if rel_root != "." else "")
            os.makedirs(dest_root, exist_ok=True)
            for name in files:
                src = os.path.join(root, name)
                dst = os.path.join(dest_root, name)
                with open(src, "rb") as s, open(dst, "wb") as d:
                    for chunk in iter(lambda: s.read(1024 * 1024), b""):
                        d.write(chunk)

        # Spectralon opcional
        if spectralon_txt_path and os.path.isfile(spectralon_txt_path):
            spec_dir = os.path.join(in_dir, "configs", "Spectralon")
            os.makedirs(spec_dir, exist_ok=True)
            spec_path = os.path.join(spec_dir, "SRT-99-120.txt")
            with open(spectralon_txt_path, "rb") as s, open(spec_path, "wb") as d:
                for chunk in iter(lambda: s.read(1024 * 1024), b""):
                    d.write(chunk)
            cfg["spectralon_file"] = spec_path

        # ✅ Fusión defensiva de parámetros Spectralon
        if spectralon_params_override:
            base_params = cfg.get("spectralon_params")
            if not isinstance(base_params, dict):
                base_params = {}
            base_params.update(spectralon_params_override)
            cfg["spectralon_params"] = base_params

        # Variables de entorno y rutas
        old_out, old_in = os.environ.get("OUTPUT_DIR"), os.environ.get("INPUT_DIR")
        os.environ["OUTPUT_DIR"], os.environ["INPUT_DIR"] = out_dir, in_dir
        cfg["output_dir"], cfg["input_dir"] = out_dir, in_dir

        try:
            runner = _load_runner(kind)
            with _chdir(out_dir):
                meta = runner(input_dir=in_dir, output_dir=out_dir, config=cfg)
        finally:
            if old_out is None:
                os.environ.pop("OUTPUT_DIR", None)
            else:
                os.environ["OUTPUT_DIR"] = old_out
            if old_in is None:
                os.environ.pop("INPUT_DIR", None)
            else:
                os.environ["INPUT_DIR"] = old_in

        # --- Consolidar resultados ---
        produced_abs = list(meta.get("produced") or []) if meta and meta.get("produced") else _list_files(out_dir)
        if not produced_abs:
            moved = _move_strays(tmp_root=tmp, in_dir=in_dir, out_dir=out_dir)
            produced_abs = _list_files(out_dir) if moved else []

        meta2 = dict(meta or {})
        produced_rel = []
        for p in produced_abs:
            try:
                rel = os.path.relpath(p, out_dir)
                if rel.startswith(".."):
                    rel = p
            except Exception:
                rel = p
            produced_rel.append(rel)
        meta2["produced"] = produced_rel

        # Campaña detectada (si existe)
        campaign = ""
        if produced_rel:
            parts = produced_rel[0].split(os.sep)
            if parts:
                campaign = parts[0]
        if campaign:
            meta2.setdefault("campaigns", [])
            if campaign not in meta2["campaigns"]:
                meta2["campaigns"].append(campaign)
            meta2["campaign"] = campaign

        # Metadata final
        meta2["kind"] = kind
        meta2["run_id"] = datetime.now(timezone(timedelta(hours=-3))).isoformat()
        meta2["processor_version"] = "radproc-web 1.0.0"
        meta2.setdefault("notes", "Procesamiento stateless")
        meta2["params_effective"] = cfg

        # Información de entrada
        spec_src = "uploaded" if spectralon_txt_path else "default"
        spec_name = os.path.basename(cfg.get("spectralon_file", "SRT-99-120.txt"))
        spec_sha = ""
        try:
            if spectralon_txt_path and os.path.isfile(spectralon_txt_path):
                with open(spectralon_txt_path, "rb") as _f:
                    spec_sha = hashlib.sha256(_f.read()).hexdigest()
        except Exception:
            spec_sha = ""
        meta2["inputs"] = {
            "zip_name": meta2.get("inputs", {}).get("zip_name", "folder-import"),
            "zip_size_bytes": 0,
            "spectralon": {"source": spec_src, "name": spec_name, "sha256": spec_sha},
        }

        meta_bytes = json.dumps(meta2, ensure_ascii=False, indent=2).encode("utf-8")
        return _zip_dir_to_bytes(out_dir, extra_files=[("metadata.json", meta_bytes)])


# =============================================================================
# 7️⃣ UTILIDAD PARA PRUEBAS DIRECTAS CON ARCHIVOS JSON
# -----------------------------------------------------------------------------
# Permite ejecutar el procesamiento sin necesidad de interfaz ni ZIPs.
# Útil para pruebas unitarias y automatizadas.
# =============================================================================
def run_processing_from_json_file(kind: Literal["agua", "suelo"], config_path: str) -> Dict[str, Any]:
    """
    Ejecuta el procesamiento usando un archivo JSON de configuración.
    Útil para pruebas locales o pipelines de integración continua.
    """
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"No se encontró el archivo de configuración: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    runner = _load_runner(kind)
    tmp_in = config_data.get("input_dir") or "/tmp/input"
    tmp_out = config_data.get("output_dir") or "/tmp/output"
    os.makedirs(tmp_in, exist_ok=True)
    os.makedirs(tmp_out, exist_ok=True)

    return runner(input_dir=tmp_in, output_dir=tmp_out, config=config_data)


# =============================================================================
# FIN DEL MÓDULO
# -----------------------------------------------------------------------------
# Este módulo constituye el núcleo del procesamiento en RadProc Web.
# Cualquier modificación debe preservar:
#   - La validación previa de configuración.
#   - El control de rutas seguras.
#   - El registro de metadata de salida.
# =============================================================================




