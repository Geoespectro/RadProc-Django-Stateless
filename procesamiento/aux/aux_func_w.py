import os
import re
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Permite generar gráficos sin entorno gráfico
import matplotlib.pyplot as plt

# =============================================================================
# Lectura robusta de archivos .txt de espectrorradiómetro
# =============================================================================
def read_file(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    if '\n\n' not in content:
        raise ValueError(f"Archivo mal formateado (falta separador '\\n\\n'): {file_path}")
    header, content = content.split('\n\n', 1)

    metadata = {}
    for line in header.split('\n'):
        if 'instrument number was' in line:
            metadata['Instrument ID'] = line.split('was ')[1].strip()
        elif 'Spectrum saved' in line:
            metadata['Spectrum saved'] = line.split(': ')[1].strip()

    wavelengths = []
    radiances = []
    for line in content.split('\n'):
        line = line.strip()
        if line and re.match(r'^\d+', line):
            wl, rad = line.split()
            wavelengths.append(float(wl))
            radiances.append(float(rad.replace(',', '.')))

    return {'metadata': metadata, 'wavelengths': wavelengths, 'radiances': radiances}

# =============================================================================
# Guardar metadatos en JSON (UTF-8)
# =============================================================================
def save_metadata(metadata, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

# =============================================================================
# Cálculo de reflectancia para agua
# =============================================================================
def calculate_refagua(rad_m_mean, rad_cielo_mean, rad_spec_mean, spectralon_reflectance):
    # Fórmula solicitada: Refagua = spectralon * ((rad_m - 0.00256 * rad_cielo) / rad_spec)
    return spectralon_reflectance * ((rad_m_mean - 0.00256 * rad_cielo_mean) / rad_spec_mean)

# =============================================================================
# Carga de configuración desde JSON
# =============================================================================
def load_config(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: El archivo {file_path} no se encontró.")
        return None
    except json.JSONDecodeError:
        print(f"Error: El archivo {file_path} no es un JSON válido.")
        return None

# =============================================================================
# Definición de índices de spectralon y muestra según el orden de medición
# =============================================================================
def TarAndSpe_ind(spectrum, meas_order):
    """
    Retorna:
      - índices (np.array) para archivos de spectralon y de muestra
      - banderas para fechas (date_start / date_end): 'spec', 'mues' o 'unknown_*'
    """
    if not meas_order or spectrum <= 0:
        raise ValueError("Config inválida: 'meas_order' vacío o 'spectrum' <= 0.")

    meas_spec_ind = []
    meas_tar_ind = []
    n = 0
    date_start = None
    date_end = None

    for i, element in enumerate(meas_order):
        if element == 'spectralon':
            meas_spec_ind.append(np.arange(n, n + spectrum))
            if i == 0:
                date_start = 'spec'
            elif i == len(meas_order) - 1:
                date_end = 'spec'
        elif element == 'target':
            meas_tar_ind.append(np.arange(n, n + spectrum))
            if i == 0:
                date_start = 'mues'
            elif i == len(meas_order) - 1:
                date_end = 'mues'
        # 'cielo' u otros elementos se ignoran para el índice
        n += spectrum

    if not meas_spec_ind or not meas_tar_ind:
        raise ValueError("No se detectaron índices de spectralon o target con el 'meas_order' provisto.")

    if date_start is None:
        date_start = 'unknown_start'
    if date_end is None:
        date_end = 'unknown_end'

    meas_spec_ind = np.concatenate(meas_spec_ind)
    meas_tar_ind = np.concatenate(meas_tar_ind)
    return meas_spec_ind, meas_tar_ind, date_start, date_end

# =============================================================================
# Procesamiento de una medición
# =============================================================================
def OneMeasurementProcess(folder_path, file_list_med_spec, file_list_med_tar, date_start, date_end, wavelength_n):
    """
    Lee los archivos listados para spectralon y muestra, arma matrices de radiancia
    y retorna (rad_spec, rad_mues, metadata, date_hour_start, date_hour_end).
    """
    rad_spec = np.zeros((len(file_list_med_spec), wavelength_n), dtype='float64')
    rad_mues = np.zeros((len(file_list_med_tar), wavelength_n), dtype='float64')
    metadata = {}
    date_hour_start = "unknown_start"
    date_hour_end = "unknown_end"

    for i, file in enumerate(file_list_med_spec):
        data = read_file(os.path.join(folder_path, file))
        if i == 0 and date_start == 'spec':
            date_hour_start = data['metadata'].get('Spectrum saved', date_hour_start)
        elif i == len(file_list_med_spec) - 1 and date_end == 'spec':
            date_hour_end = data['metadata'].get('Spectrum saved', date_hour_end)
            metadata.update(data['metadata'])
        rad_spec[i, :] = np.asarray(data['radiances'], dtype='float64')

    for i, file in enumerate(file_list_med_tar):
        data = read_file(os.path.join(folder_path, file))
        if i == 0 and date_start == 'mues':
            date_hour_start = data['metadata'].get('Spectrum saved', date_hour_start)
        elif i == len(file_list_med_tar) - 1 and date_end == 'mues':
            date_hour_end = data['metadata'].get('Spectrum saved', date_hour_end)
            metadata.update(data['metadata'])
        rad_mues[i, :] = np.asarray(data['radiances'], dtype='float64')

    metadata['Archivos Muestra'] = file_list_med_tar
    metadata['Archivos Spectralon'] = file_list_med_spec
    return rad_spec, rad_mues, metadata, date_hour_start, date_hour_end

# =============================================================================
# Gráficos
# =============================================================================
def radiance_graph(wavelength, rad_mues_mean, rad_mues_std, ax_title):
    fig, ax = plt.subplots(figsize=(10, 6))
    error_upper = rad_mues_mean + rad_mues_std
    error_lower = rad_mues_mean - rad_mues_std
    ax.plot(wavelength, rad_mues_mean, '-', label='Radiancia media')
    ax.fill_between(wavelength, error_lower, error_upper, alpha=0.2, label='Error')
    ax.set_xlabel("$\\lambda$ [nm]")
    ax.set_ylabel("L [$W/m^2/nm/sr$]")  # etiqueta cerrada correctamente
    ax.set_title(ax_title)
    ax.legend()
    ax.grid(True)
    return fig

def reflectance_graph(wavelength, ref, ref_error, ax_title):
    fig, ax = plt.subplots(figsize=(10, 6))
    error_upper_ref = ref + ref_error
    error_lower_ref = ref - ref_error
    ax.plot(wavelength, ref, '-', label='Reflectancia media')
    ax.fill_between(wavelength, error_lower_ref, error_upper_ref, alpha=0.2, label='Error')
    ax.set_xlabel("$\\lambda$ [nm]")
    ax.set_ylabel("Ref")
    ax.set_title(ax_title)
    ax.legend()
    ax.grid(True)
    return fig

# =============================================================================
# Creación de carpetas (solo dentro de output_dir)
# =============================================================================
def check_folders(folder_path_rad_med, folder_path_ref_med):
    if not os.path.exists(folder_path_rad_med):
        os.makedirs(folder_path_rad_med, exist_ok=True)
    if not os.path.exists(folder_path_ref_med):
        os.makedirs(folder_path_ref_med, exist_ok=True)

# =============================================================================
# Lectura de reflectancia del Spectralon
# =============================================================================
def read_spectralon_reflectance(file_path):
    reflectance_data = []
    with open(file_path, 'r') as file:
        header = file.readline().strip()
        for line in file:
            wavelength, reflectance = line.split()
            wavelength = int(wavelength)
            reflectance = float(reflectance)
            if 350 <= wavelength <= 2500:
                reflectance_data.append(reflectance)
    return reflectance_data


