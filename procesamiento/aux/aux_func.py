# procesamiento/aux/aux_func.py
from __future__ import annotations

import os
import re
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Evita requerir GUI para graficar
import matplotlib.pyplot as plt
from typing import List, Tuple, Dict, Any


# =============================================================================
# Lectura robusta de archivos .txt de espectrorradiómetro
# =============================================================================
def read_file(file_path: str) -> Dict[str, Any]:
    """
    Lee un archivo espectral ASD (.txt), separa encabezado y datos,
    y retorna dict con: {'metadata', 'wavelengths', 'radiances'}.
    - Tolerante a UTF-8, CRLF y decimales con coma.
    """
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read().replace('\r\n', '\n')

    # Separar encabezado y datos (dos saltos de línea, tolerando espacios)
    parts = re.split(r"\n\s*\n", content, maxsplit=1)
    if len(parts) < 2:
        # No encontramos separador claro; abortamos con error explícito
        raise ValueError(f"Archivo mal formateado (sin separador de encabezado): {file_path}")
    header, content = parts

    metadata: Dict[str, Any] = {}
    for line in header.split('\n'):
        line = line.strip()
        if not line:
            continue

        try:
            if 'instrument number was' in line:
                metadata['Instrument ID'] = line.split('was ', 1)[1].strip()
            elif 'New ASD spectrum file: Program version' in line:
                # "New ASD spectrum file: Program version = X.Y"
                metadata['Program version'] = line.split('= ', 1)[1].strip()
            elif 'Spectrum saved' in line:
                metadata['Spectrum saved'] = line.split(': ', 1)[1].strip()
            elif 'VNIR integration time' in line:
                metadata['VNIR integration time'] = int(line.split(': ', 1)[1].strip())
            elif 'VNIR channel 1 wavelength' in line:
                parts2 = line.split('= ', 1)[1].split()
                # último valor suele ser el "step"
                metadata['Wavelength step'] = float(parts2[-1].replace(',', '.'))
            elif 'There were' in line and 'samples' in line:
                # "There were N samples ..."
                mid = line.split('There were', 1)[1]
                num = mid.split('samples', 1)[0].strip()
                if num.isdigit():
                    metadata['Samples per data'] = int(num)
            elif 'xmin' in line:
                metadata['xmin'] = float(line.split('= ', 1)[1].split()[0].replace(',', '.'))
            elif 'xmax' in line:
                metadata['xmax'] = float(line.split('= ', 1)[1].split()[0].replace(',', '.'))
            elif 'ymin' in line:
                metadata['ymin'] = float(line.split('= ', 1)[1].split()[0].replace(',', '.'))
            elif 'ymax' in line:
                metadata['ymax'] = float(line.split('= ', 1)[1].split()[0].replace(',', '.'))
            elif 'SWIR1 gain was' in line:
                parts2 = line.split('was ', 1)[1].split()
                if len(parts2) >= 3:
                    metadata['SWIR1 gain'] = float(parts2[0].replace(',', '.'))
                    metadata['SWIR1 offset'] = float(parts2[2].replace(',', '.'))
            elif 'SWIR2 gain was' in line:
                parts2 = line.split('was ', 1)[1].split()
                if len(parts2) >= 3:
                    metadata['SWIR2 gain'] = float(parts2[0].replace(',', '.'))
                    metadata['SWIR2 offset'] = float(parts2[2].replace(',', '.'))
            elif 'Join between VNIR and SWIR1 was' in line:
                metadata['VNIR-SWIR1 join'] = line.split('was ', 1)[1].split()[0] + ' nm'
            elif 'Join between SWIR1 and SWIR2 was' in line:
                metadata['SWIR1-SWIR2 join'] = line.split('was ', 1)[1].split()[0] + ' nm'
            elif 'VNIR dark signal subtracted' in line:
                metadata['VNIR dark signal subtracted'] = True
            elif 'dark measurements taken' in line:
                # "... dark measurements taken N ..."
                tail = line.split('dark measurements taken ', 1)[1].split()
                if tail and tail[0].isdigit():
                    metadata['Dark measurements'] = int(tail[0])
            elif 'DCC value was' in line:
                metadata['DCC value'] = float(line.split('was ', 1)[1].strip().replace(',', '.'))
            elif 'There was no foreoptic attached' in line:
                metadata['Foreoptic'] = 'None'
            elif 'GPS-Latitude is' in line:
                metadata['GPS-Latitude'] = line.split('is ', 1)[1].strip()
            elif 'GPS-Longitude is' in line:
                metadata['GPS-Longitude'] = line.split('is ', 1)[1].strip()
            elif 'GPS-Altitude is' in line:
                metadata['GPS-Altitude'] = float(line.split('is ', 1)[1].split(',')[0].replace(',', '.'))
            elif 'GPS-UTC is' in line:
                metadata['GPS-UTC'] = line.split('is ', 1)[1].strip()
        except Exception:
            # En caso de línea rara, seguimos sin romper el parseo completo
            continue

    wavelengths: List[float] = []
    radiances: List[float] = []
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
        # línea de datos: "wavelength radiance"
        if re.match(r'^\d', line):
            parts2 = line.split()
            if len(parts2) >= 2:
                wl = parts2[0]
                rad = parts2[1]
                try:
                    wavelengths.append(float(wl.replace(',', '.')))
                    radiances.append(float(rad.replace(',', '.')))
                except ValueError:
                    # si hay valores corruptos, los saltamos
                    continue

    return {'metadata': metadata, 'wavelengths': wavelengths, 'radiances': radiances}


# =============================================================================
# Guardar metadatos en JSON
# =============================================================================
def save_metadata(metadata: Dict[str, Any], output_path: str) -> None:
    """Guarda metadatos en un archivo JSON UTF-8."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)


# -----------------------------------------------------------------------------
# Cálculo de índices e importación de espectros
# -----------------------------------------------------------------------------
def TarAndSpe_ind(spectrum: int, meas_order: List[str]) -> Tuple[np.ndarray, np.ndarray, str, str]:
    """
    Devuelve (indices_spectralon, indices_target, date_start, date_end).
    Valida que existan bloques 'spectralon' y 'target'.
    """
    meas_spec_ind, meas_tar_ind = [], []
    n = 0
    date_start, date_end = 'unknown_start', 'unknown_end'

    for i, tipo in enumerate(meas_order or []):
        if tipo == 'spectralon':
            meas_spec_ind.append(np.arange(n, n + spectrum))
            if i == 0:
                date_start = 'spec'
            if i == len(meas_order) - 1:
                date_end = 'spec'
        elif tipo == 'target':
            meas_tar_ind.append(np.arange(n, n + spectrum))
            if i == 0:
                date_start = 'mues'
            if i == len(meas_order) - 1:
                date_end = 'mues'
        n += spectrum

    if not meas_spec_ind or not meas_tar_ind:
        raise ValueError("Config inválida: faltan 'spectralon' o 'target' en 'meas_order'.")

    return np.concatenate(meas_spec_ind), np.concatenate(meas_tar_ind), date_start, date_end


def OneMeasurementProcess(folder_path: str,
                          file_list_med_spec: List[str],
                          file_list_med_tar: List[str],
                          date_start: str,
                          date_end: str,
                          wavelength_n: int) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any], str, str]:
    """
    Procesa una medición: carga archivos, arma matrices de radiancia y compila metadatos.
    Devuelve: (rad_spec, rad_mues, metadata, date_hour_start, date_hour_end)
    """
    rad_spec = np.zeros((len(file_list_med_spec), wavelength_n))
    rad_mues = np.zeros((len(file_list_med_tar), wavelength_n))
    metadata: Dict[str, Any] = {}
    date_hour_start = "unknown"
    date_hour_end = "unknown"

    for i, file in enumerate(file_list_med_spec):
        data = read_file(os.path.join(folder_path, file))
        if i == 0 and date_start == 'spec':
            date_hour_start = data['metadata'].get('Spectrum saved', date_hour_start)
        if i == len(file_list_med_spec) - 1 and date_end == 'spec':
            date_hour_end = data['metadata'].get('Spectrum saved', date_hour_end)
            metadata = data['metadata']
        rad_spec[i, :] = np.array(data['radiances'])[:wavelength_n]

    for i, file in enumerate(file_list_med_tar):
        data = read_file(os.path.join(folder_path, file))
        if i == 0 and date_start == 'mues':
            date_hour_start = data['metadata'].get('Spectrum saved', date_hour_start)
        if i == len(file_list_med_tar) - 1 and date_end == 'mues':
            date_hour_end = data['metadata'].get('Spectrum saved', date_hour_end)
            metadata = data['metadata']
        rad_mues[i, :] = np.array(data['radiances'])[:wavelength_n]

    metadata['Archivos Muestra'] = file_list_med_tar
    metadata['Archivos Spectralon'] = file_list_med_spec
    return rad_spec, rad_mues, metadata, date_hour_start, date_hour_end


# -----------------------------------------------------------------------------
# Cálculo de reflectancia y errores
# -----------------------------------------------------------------------------
def RefflectanceAndStatistics(rad_spec: np.ndarray,
                              rad_mues: np.ndarray,
                              spectralon_reflectance: np.ndarray,
                              ref_error_method: str):
    """
    Calcula reflectancia media, desvío estándar y errores según método elegido.
    """
    rad_spec_mean = np.mean(rad_spec, axis=0)
    rad_spec_std = np.std(rad_spec, axis=0)
    rad_mues_mean = np.mean(rad_mues, axis=0)
    rad_mues_std = np.std(rad_mues, axis=0)

    ref = spectralon_reflectance * rad_mues_mean / np.maximum(rad_spec_mean, 1e-12)

    if ref_error_method == 'mues':
        ref_error = np.sqrt((1 / np.maximum(rad_spec_mean, 1e-12))**2 * rad_mues_std**2)
    elif ref_error_method == 'both':
        ref_error = np.sqrt(
            (1 / np.maximum(rad_spec_mean, 1e-12))**2 * rad_mues_std**2 +
            (-rad_mues_mean / np.maximum(rad_spec_mean, 1e-12)**2)**2 * rad_spec_std**2
        )
    else:
        ref_error = np.zeros_like(ref)

    return rad_mues_mean, rad_mues_std, ref, ref_error, rad_spec_mean, rad_spec_std


# -----------------------------------------------------------------------------
# Gráficos espectrales
# -----------------------------------------------------------------------------
def radiance_graph(wavelength: np.ndarray,
                   rad_mues_mean: np.ndarray,
                   rad_mues_std: np.ndarray,
                   ax_title: str):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(wavelength, rad_mues_mean, '-', label='Radiancia media')
    ax.fill_between(wavelength, rad_mues_mean - rad_mues_std, rad_mues_mean + rad_mues_std,
                    alpha=0.2, label='Error')
    ax.set_xlabel("$\\lambda$ [nm]")
    ax.set_ylabel("L [$W/m^2/nm/sr$]")
    ax.set_title(ax_title)
    ax.grid(True)
    ax.legend()
    return fig


def reflectance_graph(wavelength: np.ndarray,
                      ref: np.ndarray,
                      ref_error: np.ndarray,
                      ax_title: str):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(wavelength, ref, '-', label='Reflectancia media')
    ax.fill_between(wavelength, ref - ref_error, ref + ref_error, alpha=0.2, label='Error')
    ax.set_xlabel("$\\lambda$ [nm]")
    ax.set_ylabel("Reflectancia")
    ax.set_title(ax_title)
    ax.grid(True)
    ax.legend()
    return fig


def radiance_graph_all(wavelength: np.ndarray,
                       rad_mues: np.ndarray,
                       rad_spec: np.ndarray,
                       rad_ref_title: str):
    fig, ax = plt.subplots(figsize=(10, 6))
    for i in range(rad_mues.shape[0]):
        ax.plot(wavelength, rad_mues[i, :], alpha=0.6)
    for i in range(rad_spec.shape[0]):
        ax.plot(wavelength, rad_spec[i, :], '--', alpha=0.6)
    ax.set_xlabel("$\\lambda$ [nm]")
    ax.set_ylabel("L [$W/m^2/nm/sr$]")
    ax.set_title(f"{rad_ref_title} (All Radiances)")
    ax.grid(True)
    return fig


# -----------------------------------------------------------------------------
# Utilidades varias
# -----------------------------------------------------------------------------
def check_folders(folder_path_rad_med: str, folder_path_ref_med: str) -> None:
    os.makedirs(folder_path_rad_med, exist_ok=True)
    os.makedirs(folder_path_ref_med, exist_ok=True)


def read_spectralon_reflectance(file_path: str) -> List[float]:
    datos: List[float] = []
    with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
        # Saltar encabezado si existe
        first = file.readline()
        for line in file:
            parts = line.strip().split()
            if len(parts) < 2:
                continue
            try:
                wl = int(float(parts[0].replace(',', '.')))
                val = float(parts[1].replace(',', '.'))
            except ValueError:
                continue
            if 350 <= wl <= 2500:
                datos.append(val)
    return datos


def get_script_dir() -> str:
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()


def load_config(file_path: str):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: El archivo {file_path} no se encontró.")
        return None
    except json.JSONDecodeError:
        print(f"Error: El archivo {file_path} no es un JSON válido.")
        return None

