import os
import re
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Evita requerir GUI para graficar
import matplotlib.pyplot as plt

# =============================================================================
# Lectura robusta de archivos .txt de espectrorradiómetro
# =============================================================================
def read_file(file_path):
    """
    Lee un archivo espectral ASD (.txt), separa encabezado y datos,
    y retorna diccionario con metadatos, longitudes de onda y radiancias.
    """
    with open(file_path, 'r') as f:
        content = f.read()

    if '\n\n' not in content:
        print(f"ADVERTENCIA: El archivo '{file_path}' no tiene el separador esperado '\n\n'.")
        raise ValueError(f"Archivo mal formateado: {file_path}")

    header, content = content.split('\n\n', 1)
    metadata = {}
    for line in header.split('\n'):
        if 'instrument number was' in line:
            metadata['Instrument ID'] = line.split('was ')[1].strip()
        elif 'New ASD spectrum file: Program version' in line:
            metadata['Program version'] = line.split('= ')[1].strip()
        elif 'Spectrum saved' in line:
            metadata['Spectrum saved'] = line.split(': ')[1].strip()
        elif 'VNIR integration time' in line:
            metadata['VNIR integration time'] = int(line.split(': ')[1])
        elif 'VNIR channel 1 wavelength' in line:
            parts = line.split('= ', 1)[1].split()
            metadata['Wavelength step'] = int(parts[-1])
        elif 'There were' in line:
            metadata['Samples per data'] = int(line.split('There were')[1].split('samples')[0])
        elif 'xmin' in line:
            metadata['xmin'] = int(line.split('= ')[1].split()[0])
        elif 'xmax' in line:
            metadata['xmax'] = int(line.split('= ')[1].split()[0])
        elif 'ymin' in line:
            metadata['ymin'] = int(line.split('= ')[1].split()[0])
        elif 'ymax' in line:
            metadata['ymax'] = int(line.split('= ')[1].split()[0])
        elif 'SWIR1 gain was' in line:
            parts = line.split('was ')[1].split()
            if len(parts) >= 3:
                metadata['SWIR1 gain'] = int(parts[0])
                metadata['SWIR1 offset'] = int(parts[2])
        elif 'SWIR2 gain was' in line:
            parts = line.split('was ')[1].split()
            if len(parts) >= 3:
                metadata['SWIR2 gain'] = int(parts[0])
                metadata['SWIR2 offset'] = int(parts[2])
        elif 'Join between VNIR and SWIR1 was' in line:
            metadata['VNIR-SWIR1 join'] = line.split('was ')[1].split()[0] + ' nm'
        elif 'Join between SWIR1 and SWIR2 was' in line:
            metadata['SWIR1-SWIR2 join'] = line.split('was ')[1].split()[0] + ' nm'
        elif 'VNIR dark signal subtracted' in line:
            metadata['VNIR dark signal subtracted'] = True
        elif 'dark measurements taken' in line:
            parts = line.split('dark measurements taken ')[1].split()
            if parts[0].isdigit():
                metadata['Dark measurements'] = int(parts[0])
        elif 'DCC value was' in line:
            metadata['DCC value'] = int(line.split('was ')[1])
        elif 'There was no foreoptic attached' in line:
            metadata['Foreoptic'] = 'None'
        elif 'GPS-Latitude is' in line:
            metadata['GPS-Latitude'] = line.split('is ')[1]
        elif 'GPS-Longitude is' in line:
            metadata['GPS-Longitude'] = line.split('is ')[1]
        elif 'GPS-Altitude is' in line:
            metadata['GPS-Altitude'] = float(line.split('is ')[1].split(',')[0])
        elif 'GPS-UTC is' in line:
            metadata['GPS-UTC'] = line.split('is ')[1]

    wavelengths = []
    radiances = []
    for line in content.split('\n'):
        line = line.strip()
        if line and re.match(r'^\d+', line):
            wavelength, radiance = line.split()
            wavelengths.append(float(wavelength))
            radiances.append(float(radiance.replace(',', '.')))

    return {'metadata': metadata, 'wavelengths': wavelengths, 'radiances': radiances}

# =============================================================================
# Guardar metadatos en JSON
# =============================================================================
def save_metadata(metadata, output_path):
    """Guarda metadatos en un archivo JSON."""
    with open(output_path, 'w') as f:
        json.dump(metadata, f, indent=4)

# -----------------------------------------------------------------------------
# Cálculo de índices e importación de espectros
# -----------------------------------------------------------------------------
def TarAndSpe_ind(spectrum, meas_order):
    """
    Devuelve los índices de archivos que son de Spectralon y de muestra (target),
    además de la posición de las fechas.
    """
    meas_spec_ind, meas_tar_ind = [], []
    n = 0
    for i, tipo in enumerate(meas_order):
        if tipo == 'spectralon':
            meas_spec_ind.append(np.arange(n, n + spectrum))
            if i == 0:
                date_start = 'spec'
            elif i == len(meas_order) - 1:
                date_end = 'spec'
        elif tipo == 'target':
            if i == 0:
                date_start = 'mues'
            elif i == len(meas_order) - 1:
                date_end = 'mues'
            meas_tar_ind.append(np.arange(n, n + spectrum))
        n += spectrum
    return np.concatenate(meas_spec_ind), np.concatenate(meas_tar_ind), date_start, date_end


def OneMeasurementProcess(folder_path, file_list_med_spec, file_list_med_tar, date_start, date_end, wavelength_n):
    """
    Procesa una medición: carga los archivos, extrae matrices de radiancia y metadatos.
    """
    rad_spec = np.zeros((len(file_list_med_spec), wavelength_n))
    rad_mues = np.zeros((len(file_list_med_tar), wavelength_n))
    metadata = {}

    for i, file in enumerate(file_list_med_spec):
        data = read_file(os.path.join(folder_path, file))
        if i == 0 and date_start == 'spec':
            date_hour_start = data['metadata']['Spectrum saved']
        elif i == len(file_list_med_spec) - 1 and date_end == 'spec':
            date_hour_end = data['metadata']['Spectrum saved']
            metadata = data['metadata']
        rad_spec[i, :] = np.array(data['radiances'])

    for i, file in enumerate(file_list_med_tar):
        data = read_file(os.path.join(folder_path, file))
        if i == 0 and date_start == 'mues':
            date_hour_start = data['metadata']['Spectrum saved']
        elif i == len(file_list_med_tar) - 1 and date_end == 'mues':
            date_hour_end = data['metadata']['Spectrum saved']
            metadata = data['metadata']
        rad_mues[i, :] = np.array(data['radiances'])

    metadata['Archivos Muestra'] = file_list_med_tar
    metadata['Archivos Spectralon'] = file_list_med_spec
    return rad_spec, rad_mues, metadata, date_hour_start, date_hour_end


# -----------------------------------------------------------------------------
# Cálculo de reflectancia y errores
# -----------------------------------------------------------------------------
def RefflectanceAndStatistics(rad_spec, rad_mues, spectralon_reflectance, ref_error_method):
    """
    Calcula reflectancia media, desvío estándar y errores según método elegido.
    """
    rad_spec_mean = np.mean(rad_spec, axis=0)
    rad_spec_std = np.std(rad_spec, axis=0)
    rad_mues_mean = np.mean(rad_mues, axis=0)
    rad_mues_std = np.std(rad_mues, axis=0)
    ref = spectralon_reflectance * rad_mues_mean / rad_spec_mean

    if ref_error_method == 'mues':
        ref_error = np.sqrt((1 / rad_spec_mean)**2 * rad_mues_std**2)
    elif ref_error_method == 'both':
        ref_error = np.sqrt(
            (1 / rad_spec_mean)**2 * rad_mues_std**2 +
            (-rad_mues_mean / rad_spec_mean**2)**2 * rad_spec_std**2
        )
    else:
        ref_error = np.zeros_like(ref)

    return rad_mues_mean, rad_mues_std, ref, ref_error, rad_spec_mean, rad_spec_std


# -----------------------------------------------------------------------------
# Gráficos espectrales
# -----------------------------------------------------------------------------
def radiance_graph(wavelength, rad_mues_mean, rad_mues_std, ax_title):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(wavelength, rad_mues_mean, '-', label='Radiancia media')
    ax.fill_between(wavelength, rad_mues_mean - rad_mues_std, rad_mues_mean + rad_mues_std, alpha=0.2, label='Error')
    ax.set_xlabel("$\\lambda$ [nm]")
    ax.set_ylabel("L [$W/m^2/nm/sr$")
    ax.set_title(ax_title)
    ax.grid(True)
    ax.legend()
    return fig

def reflectance_graph(wavelength, ref, ref_error, ax_title):
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(wavelength, ref, '-', label='Reflectancia media')
    ax.fill_between(wavelength, ref - ref_error, ref + ref_error, alpha=0.2, label='Error')
    ax.set_xlabel("$\\lambda$ [nm]")
    ax.set_ylabel("Reflectancia")
    ax.set_title(ax_title)
    ax.grid(True)
    ax.legend()
    return fig

def radiance_graph_all(wavelength, rad_mues, rad_spec, rad_ref_title):
    fig, ax = plt.subplots(figsize=(10, 6))
    for i in range(rad_mues.shape[0]):
        ax.plot(wavelength, rad_mues[i, :], alpha=0.6)
    for i in range(rad_spec.shape[0]):
        ax.plot(wavelength, rad_spec[i, :], '--', alpha=0.6)
    ax.set_xlabel("$\\lambda$ [nm]")
    ax.set_ylabel("L [$W/m^2/nm/sr$")
    ax.set_title(f"{rad_ref_title} (All Radiances)")
    ax.grid(True)
    return fig


# -----------------------------------------------------------------------------
# Utilidades varias
# -----------------------------------------------------------------------------
def check_folders(folder_path_rad_med, folder_path_ref_med):
    for path in [folder_path_rad_med, folder_path_ref_med]:
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"Directorio '{path}' creado.")
        else:
            print(f"El directorio '{path}' ya existe.")

def read_spectralon_reflectance(file_path):
    datos = []
    with open(file_path, 'r') as file:
        file.readline()  # Encabezado
        for line in file:
            wl, val = line.split()
            wl = int(wl)
            if 350 <= wl <= 2500:
                datos.append(float(val))
    return datos

def get_script_dir():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.getcwd()

def load_config(file_path):
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: El archivo {file_path} no se encontró.")
        return None
    except json.JSONDecodeError:
        print(f"Error: El archivo {file_path} no es un JSON válido.")
        return None

