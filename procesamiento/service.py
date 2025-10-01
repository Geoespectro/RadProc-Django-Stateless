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


# =========================
# Registry perezoso (lazy)
# =========================
_PROCESSOR_MODULES: dict[str, str] = {
    "agua": "procesamiento.processors.agua",
    "suelo": "procesamiento.processors.suelo",
}

def get_registered_kinds() -> List[str]:
    return list(_PROCESSOR_MODULES.keys())

def _load_runner(kind: str) -> Callable[..., Dict[str, Any]]:
    try:
        module_path = _PROCESSOR_MODULES[kind]
    except KeyError:
        disponibles = ", ".join(sorted(get_registered_kinds()))
        raise ValueError(f"kind inválido: {kind!r}. Disponibles: {disponibles}.")
    mod = importlib.import_module(module_path)
    if not hasattr(mod, "run"):
        raise RuntimeError(f"El módulo {module_path} no expone `run`.")
    return getattr(mod, "run")


# =========================
# Configuración de límites
# =========================
def _mb_to_bytes(mb: int) -> int:
    return int(mb) * 1024 * 1024

MAX_ZIP_BYTES = _mb_to_bytes(int(os.getenv("MAX_ZIP_MB", "200")))
MAX_ZIP_FILES = int(os.getenv("MAX_ZIP_FILES", "20000"))
MAX_NAME_LEN = int(os.getenv("MAX_ZIP_NAME_LEN", "255"))
MAX_SINGLE_UNCOMP_BYTES = _mb_to_bytes(int(os.getenv("MAX_SINGLE_MB", "512")))
MAX_TOTAL_UNCOMP_BYTES  = _mb_to_bytes(int(os.getenv("MAX_TOTAL_MB", "2048")))
TMP_DIR = os.getenv("TMP_DIR", "/tmp")


# =========================
# Rutas de paquete
# =========================
def _procesamiento_dir() -> str:
    return os.path.dirname(__file__)

def _configs_dir() -> str:
    return os.path.join(_procesamiento_dir(), "configs")

def _load_defaults(kind: str) -> Dict[str, Any]:
    cfg_path = os.path.join(_configs_dir(), f"{kind}.json")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return json.load(f)


# =========================
# Utilidades
# =========================
@contextmanager
def _chdir(path: str):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)

def _is_symlink(zipinfo: zipfile.ZipInfo) -> bool:
    return ((zipinfo.external_attr >> 16) & 0o170000) == 0o120000  # S_IFLNK

def _safe_join(base: str, *paths: str) -> str:
    dest = os.path.normpath(os.path.join(base, *paths))
    base_abs = os.path.abspath(base)
    dest_abs = os.path.abspath(dest)
    if not (dest_abs == base_abs or dest_abs.startswith(base_abs + os.sep)):
        raise ValueError("Ruta insegura detectada al extraer ZIP (posible Zip-Slip).")
    return dest

def _zip_extract_all(zip_bytes: bytes, dest_dir: str) -> None:
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
            # mover respetando estructura relativa a tmp_root
            rel = os.path.relpath(full, tmp_root)
            dest = os.path.join(stray_base, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                shutil.move(full, dest)
            except Exception:
                # si falla mover, intentamos copiar
                try:
                    shutil.copy2(full, dest)
                    os.remove(full)
                except Exception:
                    continue
            dests.append(dest)
    return dests


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
    defaults = _load_defaults(kind)
    cfg: Dict[str, Any] = {**defaults, **(params or {})}

    with TemporaryDirectory(dir=TMP_DIR) as tmp:
        in_dir = os.path.join(tmp, "in")
        out_dir = os.path.join(tmp, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        _zip_extract_all(zip_bytes, in_dir)

        if spectralon_txt_bytes:
            spec_dir = os.path.join(in_dir, "configs", "Spectralon")
            os.makedirs(spec_dir, exist_ok=True)
            spec_path = os.path.join(spec_dir, "SRT-99-120.txt")
            with open(spec_path, "wb") as f:
                f.write(spectralon_txt_bytes)
            cfg["spectralon_file"] = spec_path

        if spectralon_params_override:
            cfg.setdefault("spectralon_params", {}).update(spectralon_params_override)

        # Fijar env y pasar rutas en config ANTES de importar el runner
        old_out = os.environ.get("OUTPUT_DIR")
        old_in  = os.environ.get("INPUT_DIR")
        os.environ["OUTPUT_DIR"] = out_dir
        os.environ["INPUT_DIR"]  = in_dir
        cfg["output_dir"] = out_dir
        cfg["input_dir"]  = in_dir

        try:
            runner = _load_runner(kind)   # importa ahora, con env ya seteado
            # Cambiar CWD para que rutas relativas del runner caigan en out_dir
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

        # Si el runner no reporta 'produced', inferirlo de out_dir
        produced_abs: List[str] = []
        if meta and meta.get("produced"):
            produced_abs = list(meta.get("produced") or [])
        else:
            produced_abs = _list_files(out_dir)

        # Si sigue vacío, buscar “descolgados” en tmp y moverlos a out/_strays
        if not produced_abs:
            moved = _move_strays(tmp_root=tmp, in_dir=in_dir, out_dir=out_dir)
            produced_abs = _list_files(out_dir) if moved else []

        # Enriquecer metadata
        meta2 = dict(meta or {})
        produced_rel: List[str] = []
        for p in produced_abs:
            try:
                rel = os.path.relpath(p, out_dir)
                if rel.startswith(".."):
                    rel = p
            except Exception:
                rel = p
            produced_rel.append(rel)
        meta2["produced"] = produced_rel

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

        meta2["kind"] = kind
        meta2["run_id"] = datetime.now(timezone(timedelta(hours=-3))).isoformat()
        meta2["processor_version"] = "radproc-web 1.0.0"
        meta2.setdefault("notes", "Procesamiento stateless")
        meta2["params_effective"] = cfg

        spec_src = "uploaded" if spectralon_txt_bytes else "default"
        spec_name = os.path.basename(cfg.get("spectralon_file", "SRT-99-120.txt"))
        spec_sha = hashlib.sha256(spectralon_txt_bytes).hexdigest() if spectralon_txt_bytes else ""
        meta2["inputs"] = {
            "zip_name": meta2.get("inputs", {}).get("zip_name", "upload.zip"),
            "zip_size_bytes": len(zip_bytes),
            "spectralon": {"source": spec_src, "name": spec_name, "sha256": spec_sha},
        }

        meta_bytes = json.dumps(meta2, ensure_ascii=False, indent=2).encode("utf-8")
        out_zip = _zip_dir_to_bytes(out_dir, extra_files=[("metadata.json", meta_bytes)])
        return out_zip


def process_folder_to_zip(
    input_dir: str,
    kind: Literal["agua", "suelo"],
    params: Optional[Dict[str, Any]] = None,
    spectralon_txt_path: Optional[str] = None,
    spectralon_params_override: Optional[Dict[str, Any]] = None,
) -> bytes:
    if not os.path.isdir(input_dir):
        raise FileNotFoundError(f"input_dir no existe o no es carpeta: {input_dir}")

    defaults = _load_defaults(kind)
    cfg: Dict[str, Any] = {**defaults, **(params or {})}

    with TemporaryDirectory(dir=TMP_DIR) as tmp:
        in_dir = os.path.join(tmp, "in")
        out_dir = os.path.join(tmp, "out")
        os.makedirs(in_dir, exist_ok=True)
        os.makedirs(out_dir, exist_ok=True)

        # Copia superficial
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

        old_out = os.environ.get("OUTPUT_DIR")
        old_in  = os.environ.get("INPUT_DIR")
        os.environ["OUTPUT_DIR"] = out_dir
        os.environ["INPUT_DIR"]  = in_dir
        cfg["output_dir"] = out_dir
        cfg["input_dir"]  = in_dir

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

        produced_abs: List[str] = []
        if meta and meta.get("produced"):
            produced_abs = list(meta.get("produced") or [])
        else:
            produced_abs = _list_files(out_dir)

        if not produced_abs:
            moved = _move_strays(tmp_root=tmp, in_dir=in_dir, out_dir=out_dir)
            produced_abs = _list_files(out_dir) if moved else []

        meta2 = dict(meta or {})
        produced_rel: List[str] = []
        for p in produced_abs:
            try:
                rel = os.path.relpath(p, out_dir)
                if rel.startswith(".."):
                    rel = p
            except Exception:
                rel = p
            produced_rel.append(rel)
        meta2["produced"] = produced_rel

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

        meta2["kind"] = kind
        meta2["run_id"] = datetime.now(timezone(timedelta(hours=-3))).isoformat()
        meta2["processor_version"] = "radproc-web 1.0.0"
        meta2.setdefault("notes", "Procesamiento stateless")
        meta2["params_effective"] = cfg

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




