# procesamiento/service.py
from __future__ import annotations

import os
import json
from io import BytesIO
from typing import Dict, Any, Literal, Optional, List, Tuple
from tempfile import TemporaryDirectory
import zipfile

# Importar los runners stateless que ya reemplazaste
from procesamiento.processors.agua import run as run_agua
from procesamiento.processors.suelo import run as run_suelo


def _procesamiento_dir() -> str:
    """
    Devuelve la ruta absoluta a la carpeta 'procesamiento'.
    Este archivo debe estar en procesamiento/service.py.
    """
    return os.path.dirname(__file__)


def _configs_dir() -> str:
    """Ruta a procesamiento/configs"""
    return os.path.join(_procesamiento_dir(), "configs")


def _load_defaults(kind: Literal["agua", "suelo"]) -> Dict[str, Any]:
    """
    Carga el JSON de configuración por defecto (solo lectura, dentro de la imagen).
    """
    cfg_path = os.path.join(_configs_dir(), f"{kind}.json")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _zip_extract_all(zip_bytes: bytes, dest_dir: str) -> None:
    """
    Extrae ZIP (en memoria) al directorio 'dest_dir'.
    """
    with zipfile.ZipFile(BytesIO(zip_bytes), "r") as zf:
        zf.extractall(dest_dir)


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


def process_zip(
    zip_bytes: bytes,
    kind: Literal["agua", "suelo"],
    params: Optional[Dict[str, Any]] = None
) -> bytes:
    """
    Orquesta el procesamiento en modo stateless:
      1) Crea un directorio temporal
      2) Extrae el ZIP de entrada
      3) Carga defaults de config y los mergea con 'params'
      4) Ejecuta el runner (agua/suelo)
      5) Devuelve un ZIP en memoria con los resultados + metadata.json

    No persiste nada fuera del directorio temporal.
    """
    if kind not in ("agua", "suelo"):
        raise ValueError("kind debe ser 'agua' o 'suelo'.")

    defaults = _load_defaults(kind)
    cfg: Dict[str, Any] = {**defaults, **(params or {})}

    with TemporaryDirectory() as tmp:
        in_dir = os.path.join(tmp, "in")
        out_dir = os.path.join(tmp, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        # 1-2) Extraer ZIP a in_dir
        _zip_extract_all(zip_bytes, in_dir)

        # 3-4) Ejecutar proceso
        if kind == "agua":
            meta = run_agua(input_dir=in_dir, output_dir=out_dir, config=cfg)
        else:
            meta = run_suelo(input_dir=in_dir, output_dir=out_dir, config=cfg)

        # 5) Empaquetar resultados + metadata.json
        meta_bytes = json.dumps(meta or {}, ensure_ascii=False, indent=2).encode("utf-8")
        out_zip = _zip_dir_to_bytes(out_dir, extra_files=[("metadata.json", meta_bytes)])
        return out_zip


# ---------------------- Opcional: helpers para desarrollo local ----------------------

def process_folder_to_zip(
    input_dir: str,
    kind: Literal["agua", "suelo"],
    params: Optional[Dict[str, Any]] = None
) -> bytes:
    """
    Versión de ayuda para desarrollo local: procesa una carpeta ya descomprimida (input_dir)
    y devuelve un ZIP de resultados en memoria.
    """
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"input_dir no existe o no es carpeta: {input_dir}")

    defaults = _load_defaults(kind)
    cfg: Dict[str, Any] = {**defaults, **(params or {})}

    with TemporaryDirectory() as tmp:
        out_dir = os.path.join(tmp, "out")
        os.makedirs(out_dir, exist_ok=True)

        if kind == "agua":
            meta = run_agua(input_dir=input_dir, output_dir=out_dir, config=cfg)
        else:
            meta = run_suelo(input_dir=input_dir, output_dir=out_dir, config=cfg)

        meta_bytes = json.dumps(meta or {}, ensure_ascii=False, indent=2).encode("utf-8")
        return _zip_dir_to_bytes(out_dir, extra_files=[("metadata.json", meta_bytes)])
