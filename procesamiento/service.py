# procesamiento/service.py
from __future__ import annotations

"""
Servicio de orquestación STATeless para RadProc.

Características:
- Trabaja SIEMPRE en un directorio temporal efímero (no persiste nada).
- Extrae ZIPs de entrada con verificaciones de seguridad (anti Zip-Slip,
  symlinks, límites de tamaño por archivo y total).
- Invoca los runners de procesamiento (agua/suelo) y retorna un ZIP en memoria
  con los resultados + metadata.json.
- Permite opcionalmente adjuntar un archivo Spectralon TXT y/o overrides de
  parámetros de Spectralon SOLO para la ejecución actual.

Variables de entorno (todas opcionales):
  TMP_DIR="/tmp"                  # Raíz para TemporaryDirectory
  MAX_ZIP_MB="200"                # Tamaño máximo del ZIP de entrada (MB)
  MAX_ZIP_FILES="20000"           # Máx. cantidad de entradas en el ZIP
  MAX_ZIP_NAME_LEN="255"          # Máx. longitud de nombre de archivo
  MAX_SINGLE_MB="512"             # Máx. tamaño descomprimido por archivo (MB)
  MAX_TOTAL_MB="2048"             # Máx. tamaño descomprimido total (MB)
"""

import os
import json
from io import BytesIO
from typing import Dict, Any, Literal, Optional, List, Tuple
from tempfile import TemporaryDirectory
import zipfile

# Runners stateless
from procesamiento.processors.agua import run as run_agua
from procesamiento.processors.suelo import run as run_suelo


# =========================
# Configuración de límites
# =========================
def _mb_to_bytes(mb: int) -> int:
    return int(mb) * 1024 * 1024

MAX_ZIP_BYTES = _mb_to_bytes(int(os.getenv("MAX_ZIP_MB", "200")))                 # ZIP de entrada (comprimido)
MAX_ZIP_FILES = int(os.getenv("MAX_ZIP_FILES", "20000"))                          # Entradas máximas
MAX_NAME_LEN = int(os.getenv("MAX_ZIP_NAME_LEN", "255"))                          # Longitud de nombre
MAX_SINGLE_UNCOMP_BYTES = _mb_to_bytes(int(os.getenv("MAX_SINGLE_MB", "512")))    # Archivo descomprimido
MAX_TOTAL_UNCOMP_BYTES  = _mb_to_bytes(int(os.getenv("MAX_TOTAL_MB", "2048")))    # Total descomprimido

TMP_DIR = os.getenv("TMP_DIR", "/tmp")  # Ideal para montar emptyDir en K8s


# =========================
# Rutas de paquete
# =========================
def _procesamiento_dir() -> str:
    """Ruta absoluta a la carpeta 'procesamiento'."""
    return os.path.dirname(__file__)

def _configs_dir() -> str:
    """Ruta a procesamiento/configs."""
    return os.path.join(_procesamiento_dir(), "configs")

def _load_defaults(kind: Literal["agua", "suelo"]) -> Dict[str, Any]:
    """Carga el JSON de configuración por defecto (solo lectura, dentro de la imagen)."""
    cfg_path = os.path.join(_configs_dir(), f"{kind}.json")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


# =========================
# ZIP seguro (anti Zip-Slip, límites)
# =========================
def _is_symlink(zipinfo: zipfile.ZipInfo) -> bool:
    # Detecta symlinks en ZIP (modo Unix: bits de tipo archivo en external_attr)
    # 0o120000 => S_IFLNK
    return ((zipinfo.external_attr >> 16) & 0o170000) == 0o120000

def _safe_join(base: str, *paths: str) -> str:
    # Ensambla y normaliza, garantizando que el resultado quede dentro de 'base'
    dest = os.path.normpath(os.path.join(base, *paths))
    base_abs = os.path.abspath(base)
    dest_abs = os.path.abspath(dest)
    if not (dest_abs == base_abs or dest_abs.startswith(base_abs + os.sep)):
        raise ValueError("Ruta insegura detectada al extraer ZIP (posible Zip-Slip).")
    return dest

def _zip_extract_all(zip_bytes: bytes, dest_dir: str) -> None:
    """
    Extrae un ZIP (desde memoria) a 'dest_dir' con validaciones de seguridad:
    - Tamaño máximo del ZIP comprimido
    - Límite de cantidad de archivos
    - Bloqueo de rutas absolutas o traversal ('..')
    - Bloqueo de symlinks
    - Límite de tamaño descomprimido por archivo y total
    """
    if len(zip_bytes) > MAX_ZIP_BYTES:
        raise ValueError(f"ZIP demasiado grande: {len(zip_bytes)} bytes (límite {MAX_ZIP_BYTES} bytes).")

    total_uncompressed = 0
    files_count = 0

    with zipfile.ZipFile(BytesIO(zip_bytes), "r") as zf:
        infolist = zf.infolist()

        if len(infolist) > MAX_ZIP_FILES:
            raise ValueError(f"ZIP con demasiados archivos: {len(infolist)} (límite {MAX_ZIP_FILES}).")

        for info in infolist:
            filename = info.filename

            # Saltar directorios
            if filename.endswith("/") or filename.endswith("\\"):
                continue

            # Validar nombre
            if os.path.isabs(filename):
                raise ValueError(f"Ruta absoluta no permitida en ZIP: {filename}")
            norm = os.path.normpath(filename)
            if ".." in norm.split(os.sep):
                raise ValueError(f"Ruta con '..' no permitida en ZIP: {filename}")
            if len(os.path.basename(norm)) > MAX_NAME_LEN:
                raise ValueError(f"Nombre de archivo demasiado largo en ZIP: {filename}")

            # Bloquear symlinks
            if _is_symlink(info):
                raise ValueError(f"Symlink no permitido en ZIP: {filename}")

            # Límites de tamaño descomprimido
            uncomp = info.file_size
            if uncomp > MAX_SINGLE_UNCOMP_BYTES:
                raise ValueError(f"Archivo descomprimido excede el límite: {filename} ({uncomp} bytes).")
            total_uncompressed += uncomp
            if total_uncompressed > MAX_TOTAL_UNCOMP_BYTES:
                raise ValueError("Tamaño total descomprimido del ZIP excede el límite.")

            # Extraer de forma controlada (copia por chunks)
            dest_path = _safe_join(dest_dir, norm)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with zf.open(info, "r") as src, open(dest_path, "wb") as dst:
                for chunk in iter(lambda: src.read(1024 * 1024), b""):
                    dst.write(chunk)

            files_count += 1


def _zip_dir_to_bytes(src_dir: str, extra_files: Optional[List[Tuple[str, bytes]]] = None) -> bytes:
    """
    Comprime recursivamente 'src_dir' en un ZIP en memoria.
    Permite agregar archivos 'extra_files' como (path_relativo, contenido_bytes).
    """
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Contenido generado por el proceso
        for root, _, files in os.walk(src_dir):
            for name in files:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, src_dir)
                zf.write(full, rel)
        # Extras (p. ej. metadata.json agregada por este servicio)
        if extra_files:
            for rel, data in extra_files:
                zf.writestr(rel, data)
    buf.seek(0)
    return buf.read()


# =========================
# API de orquestación
# =========================
def process_zip(
    zip_bytes: bytes,
    kind: Literal["agua", "suelo"],
    params: Optional[Dict[str, Any]] = None,
    spectralon_txt_bytes: Optional[bytes] = None,
    spectralon_params_override: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Orquesta el procesamiento STATeless:
      1) Crea un directorio temporal efímero
      2) Extrae el ZIP de entrada (validado)
      3) Carga defaults y aplica 'params'
      4) (Opcional) Escribe Spectralon TXT temporal y/o aplica overrides
      5) Ejecuta el runner (agua/suelo)
      6) Devuelve un ZIP en memoria con los resultados + metadata.json
    """
    if kind not in ("agua", "suelo"):
        raise ValueError("kind debe ser 'agua' o 'suelo'.")

    defaults = _load_defaults(kind)
    cfg: Dict[str, Any] = {**defaults, **(params or {})}

    with TemporaryDirectory(dir=TMP_DIR) as tmp:
        in_dir = os.path.join(tmp, "in")
        out_dir = os.path.join(tmp, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        # 1-2) Extraer ZIP a in_dir (validado)
        _zip_extract_all(zip_bytes, in_dir)

        # 3-4) Spectralon SOLO para esta ejecución
        if spectralon_txt_bytes:
            spec_dir = os.path.join(in_dir, "configs", "Spectralon")
            os.makedirs(spec_dir, exist_ok=True)
            # Usamos el nombre esperado por el pipeline por defecto:
            spec_path = os.path.join(spec_dir, "SRT-99-120.txt")
            with open(spec_path, "wb") as f:
                f.write(spectralon_txt_bytes)
            # Señal al runner (si lo soporta)
            cfg["spectralon_file"] = spec_path

        if spectralon_params_override:
            cfg.setdefault("spectralon_params", {}).update(spectralon_params_override)

        # 5) Ejecutar runner
        if kind == "agua":
            meta = run_agua(input_dir=in_dir, output_dir=out_dir, config=cfg)
        else:
            meta = run_suelo(input_dir=in_dir, output_dir=out_dir, config=cfg)

        # 6) Empaquetar resultados + metadata.json
        meta_bytes = json.dumps(meta or {}, ensure_ascii=False, indent=2).encode("utf-8")
        out_zip = _zip_dir_to_bytes(out_dir, extra_files=[("metadata.json", meta_bytes)])
        return out_zip


# ---------------------- Helpers para desarrollo local (opcional) ----------------------
def process_folder_to_zip(
    input_dir: str,
    kind: Literal["agua", "suelo"],
    params: Optional[Dict[str, Any]] = None,
    spectralon_txt_path: Optional[str] = None,
    spectralon_params_override: Optional[Dict[str, Any]] = None,
) -> bytes:
    """
    Procesa una carpeta ya descomprimida (input_dir) y devuelve un ZIP
    de resultados en memoria. Útil para pruebas locales.
    """
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"input_dir no existe o no es carpeta: {input_dir}")

    defaults = _load_defaults(kind)
    cfg: Dict[str, Any] = {**defaults, **(params or {})}

    with TemporaryDirectory(dir=TMP_DIR) as tmp:
        # Copiamos input_dir bajo tmp/in para emular layout
        in_dir = os.path.join(tmp, "in")
        out_dir = os.path.join(tmp, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        # Copia superficial (nombres y tamaños razonables para pruebas)
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

        # Spectralon local opcional
        if spectralon_txt_path and os.path.isfile(spectralon_txt_path):
            spec_dir = os.path.join(in_dir, "configs", "Spectralon")
            os.makedirs(spec_dir, exist_ok=True)
            spec_path = os.path.join(spec_dir, "SRT-99-120.txt")
            with open(spectralon_txt_path, "rb") as s, open(spec_path, "wb") as d:
                for chunk in iter(lambda: s.read(1024 * 1024), b""):
                    d.write(chunk)
            cfg["spectralon_file"] = spec_path

        if spectralon_params_override:
            cfg.setdefault("spectralon_params", {}).update(spectralon_params_override)

        if kind == "agua":
            meta = run_agua(input_dir=in_dir, output_dir=out_dir, config=cfg)
        else:
            meta = run_suelo(input_dir=in_dir, output_dir=out_dir, config=cfg)

        meta_bytes = json.dumps(meta or {}, ensure_ascii=False, indent=2).encode("utf-8")
        return _zip_dir_to_bytes(out_dir, extra_files=[("metadata.json", meta_bytes)])
