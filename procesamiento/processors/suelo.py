# procesamiento/processors/suelo.py
from __future__ import annotations

import os
import re
import json
from typing import Dict, Any, List, Tuple
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from procesamiento.aux import aux_func as auxfunc

def _write_processing_info(out_folder: str, spec_path: str, config: dict,
                           spectrum: int, meas_order: list,
                           ref_error_method: str, rad_plot: int, ref_plot: int) -> None:
    import hashlib, json, os
    sha = ""
    try:
        with open(spec_path, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
    except Exception:
        pass
    info = {
        "spectralon_file": spec_path,
        "spectralon_sha256": sha,
        "params_effective": {
            "spectrum": spectrum,
            "meas_order": meas_order,
            "ref_error_method": ref_error_method,
            "rad_plot": rad_plot,
            "ref_plot": ref_plot
        }
    }
    p = os.path.join(out_folder, "processing_info.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)



def _spectralon_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(__file__))  # .../procesamiento
    return os.path.join(base_dir, "configs", "Spectralon", "SRT-99-120.txt")


def _find_measurement_dir(root: str) -> List[str]:
    found: List[str] = []
    for current, dirs, files in os.walk(root):
        if os.path.basename(current) == "Texto Rad CorrPar":
            parent = os.path.basename(os.path.dirname(current))
            grand = os.path.basename(os.path.dirname(os.path.dirname(current)))
            if parent == "Radiometria" and grand:
                found.append(current)
    return found


def _sorted_txt_files(meas_dir: str) -> List[str]:
    def extraer_num_final(nombre: str) -> int:
        match = re.search(r"(\d+)(?=\.asd|\.txt)", nombre)
        return int(match.group(1)) if match else 0

    return sorted(
        [
            f for f in os.listdir(meas_dir)
            if f.lower().endswith(".txt") and os.path.isfile(os.path.join(meas_dir, f))
        ],
        key=extraer_num_final
    )


def run(input_dir: str, output_dir: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa mediciones de SUELO en modo stateless.
    """
    # ---------- Configuración ----------
    folder_list: List[str] = config.get("folder_list", []) or []
    ref_error_method = config.get("ref_error_method", "mues")
    rad_all_plot = int(config.get("rad_all_plot", 0))
    rad_plot = int(config.get("rad_plot", 1))
    ref_plot = int(config.get("ref_plot", 1))
    spectrum = int(config.get("spectrum", 10))
    meas_order: List[str] = config.get("meas_order", [])
    target_list: List[str] = config.get("target_list", [])

    # ---------- Spectralon ----------
    # Prioriza el espectralon provisto por config; si no, usa el default del paquete.
    spec_path = config.get("spectralon_file") or _spectralon_path()
    if not os.path.exists(spec_path):
        raise FileNotFoundError(f"No se encontró archivo de calibración: {spec_path}")
    spectralon_reflectance = np.array(auxfunc.read_spectralon_reflectance(spec_path))

    # ---------- Variables base ----------
    wavelength = np.arange(350, 2501)
    wavelength_n = len(wavelength)
    meas_spec_ind, meas_tar_ind, date_start, date_end = auxfunc.TarAndSpe_ind(spectrum, meas_order)
    n_one_meas = spectrum * len(meas_order)

    # ---------- Descubrir campañas / mediciones ----------
    measurement_dirs: List[Tuple[str, str]] = []
    if folder_list:
        for folder in folder_list:
            candidate = os.path.join(input_dir, folder, "Radiometria", "Texto Rad CorrPar")
            if os.path.exists(candidate):
                measurement_dirs.append((folder, candidate))
        if not measurement_dirs:
            for folder in folder_list:
                base = os.path.join(input_dir, folder)
                found = _find_measurement_dir(base)
                for m in found:
                    measurement_dirs.append((folder, m))
    else:
        for m in _find_measurement_dir(input_dir):
            folder_name = os.path.basename(os.path.dirname(os.path.dirname(m)))
            measurement_dirs.append((folder_name, m))

    os.makedirs(output_dir, exist_ok=True)

    # ---------- Proceso ----------
    produced: List[str] = []

    for folder, meas_dir in measurement_dirs:
        file_list = _sorted_txt_files(meas_dir)
        if not file_list:
            continue

        n_meas = len(file_list) // n_one_meas if n_one_meas > 0 else 0
        if n_meas <= 0:
            continue

        for nn in range(n_meas):
            files = file_list[nn * n_one_meas: (nn + 1) * n_one_meas]
            spec_files = [files[i] for i in meas_spec_ind]
            tar_files = [files[i] for i in meas_tar_ind]

            rad_spec, rad_mues, metadata, date_start_str, date_end_str = auxfunc.OneMeasurementProcess(
                meas_dir, spec_files, tar_files, date_start, date_end, wavelength_n
            )

            rad_mues_mean, rad_mues_std, ref, ref_error, rad_spec_mean, rad_spec_std = auxfunc.RefflectanceAndStatistics(
                rad_spec, rad_mues, spectralon_reflectance, ref_error_method
            )

            out_folder = os.path.join(output_dir, folder)
            rad_dir = os.path.join(out_folder, "Radiometria", "Texto Radiancia Promedio")
            ref_dir = os.path.join(out_folder, "Radiometria", "Texto reflectancia promedio")
            auxfunc.check_folders(rad_dir, ref_dir)

            tag = target_list[nn] if nn < len(target_list) else f"MED_{nn+1:03d}"
            root_rad = os.path.join(rad_dir, tag)
            root_ref = os.path.join(ref_dir, tag)

            np.savetxt(root_rad + "_rad.txt", rad_mues_mean)
            np.savetxt(root_rad + "_rad-error.txt", rad_mues_std)
            np.savetxt(root_ref + "_ref.txt", ref)
            np.savetxt(root_ref + "_ref-error.txt", ref_error)
            auxfunc.save_metadata(metadata, root_rad + "_rad_metadata.json")
            auxfunc.save_metadata(metadata, root_ref + "_ref_metadata.json")

            if rad_plot == 1:
                fig = auxfunc.radiance_graph(wavelength, rad_mues_mean, rad_mues_std, tag)
                fig.savefig(root_rad + "_rad.png")
                plt.close(fig)

            if ref_plot == 1:
                fig = auxfunc.reflectance_graph(wavelength, ref, ref_error, tag)
                fig.savefig(root_ref + "_ref.png")
                plt.close(fig)

            produced.extend([
                root_rad + "_rad.txt",
                root_rad + "_rad-error.txt",
                root_ref + "_ref.txt",
                root_ref + "_ref-error.txt",
                root_rad + "_rad_metadata.json",
                root_ref + "_ref_metadata.json",
            ])
            if rad_plot == 1:
                produced.append(root_rad + "_rad.png")
            if ref_plot == 1:
                produced.append(root_ref + "_ref.png")

    return {
        "ok": True,
        "produced": produced,
        "campaigns": list({c for c, _ in measurement_dirs}),
        "notes": "Procesamiento de suelo en modo stateless"
    }


if __name__ == "__main__":
    in_dir = os.environ.get("INPUT_DIR")
    out_dir = os.environ.get("OUTPUT_DIR")
    cfg_path = os.environ.get("CONFIG_JSON")
    if not (in_dir and out_dir and cfg_path and os.path.exists(cfg_path)):
        raise SystemExit("Definí INPUT_DIR, OUTPUT_DIR y CONFIG_JSON para ejecutar localmente.")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    result = run(in_dir, out_dir, cfg)
    print(json.dumps(result, ensure_ascii=False, indent=2))

