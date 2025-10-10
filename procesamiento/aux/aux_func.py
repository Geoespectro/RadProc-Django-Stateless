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
def read_file(file_path):
    """
    Lee un archivo espectral ASD (.txt), separa encabezado y datos con tolerancia,
    y retorna dict con metadatos, longitudes de onda y radiancias.
    - Tolera ausencia de '\n\n' localizando la primera línea de datos.
    - Tolera columnas extra en las filas numéricas (toma la 2ª como valor).
    - Mantiene búsqueda de metadatos por substring (orden indiferente).
    """
    with open(file_path, 'r') as f:
        content = f.read()

    lines = content.splitlines()
    # 1) Detectar índice donde empiezan los datos (primera línea que arranca con dígitos)
    data_start = None
    for i, ln in enumerate(lines):
        if ln.strip() and re.match(r'^\d+', ln.strip()):
            data_start = i
            break
    if data_start is None:
        raise ValueError(f"No se detectaron filas de datos numéricos en: {file_path}")

    # 2) Header = todo antes de la primera línea numérica (tenga o no '\n\n')
    header_lines = lines[:data_start]
    data_lines = lines[data_start:]

    # 3) Metadatos (mismo criterio que tenías)
    header = "\n".join(header_lines)
    metadata = {}
    for line in header.split('\n'):
        if 'instrument number was' in line:
            metadata['Instrument ID'] = line.split('was ')[1].strip()
        elif 'New ASD spectrum file: Program version' in line:
            metadata['Program version'] = line.split('= ')[1].strip() if '= ' in line else line.split()[-1]
        elif 'Spectrum saved' in line:
            metadata['Spectrum saved'] = line.split(': ', 1)[1].strip() if ': ' in line else line.split(':',1)[1].strip()
        elif 'VNIR integration time' in line:
            try:
                metadata['VNIR integration time'] = int(line.split(': ', 1)[1])
            except Exception:
                pass
        elif 'VNIR channel 1 wavelength' in line:
            try:
                parts = line.split('= ', 1)[1].split()
                metadata['Wavelength step'] = int(parts[-1])
            except Exception:
                pass
        elif 'There were' in line and 'samples' in line:
            try:
                metadata['Samples per data'] = int(line.split('There were')[1].split('samples')[0])
            except Exception:
                pass
        elif 'xmin' in line:
            try: metadata['xmin'] = int(line.split('= ',1)[1].split()[0])
            except Exception: pass
        elif 'xmax' in line:
            try: metadata['xmax'] = int(line.split('= ',1)[1].split()[0])
            except Exception: pass
        elif 'ymin' in line:
            try: metadata['ymin'] = int(line.split('= ',1)[1].split()[0])
            except Exception: pass
        elif 'ymax' in line:
            try: metadata['ymax'] = int(line.split('= ',1)[1].split()[0])
            except Exception: pass
        elif 'SWIR1 gain was' in line:
            parts = line.split('was ')[1].split()
            if len(parts) >= 3:
                try:
                    metadata['SWIR1 gain'] = int(parts[0]); metadata['SWIR1 offset'] = int(parts[2])
                except Exception: pass
        elif 'SWIR2 gain was' in line:
            parts = line.split('was ')[1].split()
            if len(parts) >= 3:
                try:
                    metadata['SWIR2 gain'] = int(parts[0]); metadata['SWIR2 offset'] = int(parts[2])
                except Exception: pass
        elif 'Join between VNIR and SWIR1 was' in line:
            try: metadata['VNIR-SWIR1 join'] = line.split('was ')[1].split()[0] + ' nm'
            except Exception: pass
        elif 'Join between SWIR1 and SWIR2 was' in line:
            try: metadata['SWIR1-SWIR2 join'] = line.split('was ')[1].split()[0] + ' nm'
            except Exception: pass
        elif 'VNIR dark signal subtracted' in line:
            metadata['VNIR dark signal subtracted'] = True
        elif 'dark measurements taken' in line:
            try:
                parts = line.split('dark measurements taken ')[1].split()
                if parts[0].isdigit():
                    metadata['Dark measurements'] = int(parts[0])
            except Exception:
                pass
        elif 'DCC value was' in line:
            try: metadata['DCC value'] = int(line.split('was ')[1])
            except Exception: pass
        elif 'There was no foreoptic attached' in line:
            metadata['Foreoptic'] = 'None'
        elif 'GPS-Latitude is' in line:
            metadata['GPS-Latitude'] = line.split('is ',1)[1]
        elif 'GPS-Longitude is' in line:
            metadata['GPS-Longitude'] = line.split('is ',1)[1]
        elif 'GPS-Altitude is' in line:
            try: metadata['GPS-Altitude'] = float(line.split('is ',1)[1].split(',')[0])
            except Exception: pass
        elif 'GPS-UTC is' in line:
            metadata['GPS-UTC'] = line.split('is ',1)[1]

    # 4) Datos numéricos (tolerantes)
    wavelengths = []
    radiances = []
    for line in data_lines:
        s = line.strip()
        if not s or not re.match(r'^\d+', s):
            continue
        parts = s.split()
        try:
            wl = float(parts[0])
            # Tomar la 2ª columna como valor; reemplazar coma por punto
            rad_token = parts[1].replace(',', '.')
            val = float(rad_token)
        except Exception:
            continue  # línea rara → ignorar
        wavelengths.append(wl)
        radiances.append(val)

    if not wavelengths:
        raise ValueError(f"No se extrajeron datos numéricos en: {file_path}")

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

