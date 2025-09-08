import sys
import os
import shutil

# ---------------------------------------------------------------------
# FUNCIONES DE UTILIDAD PARA RUTAS Y RECURSOS DEL PROYECTO
# Estas funciones están pensadas para funcionar tanto en desarrollo
# como cuando la app está empaquetada con PyInstaller o Nuitka.
# ---------------------------------------------------------------------

def get_project_root():
    """
    Devuelve la raíz del proyecto, que contiene las carpetas 'interfaz' y 'procesamiento'.
    En modo empaquetado (--onefile), devuelve la ubicación del ejecutable.
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def get_base_path():
    """
    Devuelve la ruta base donde se encuentra la carpeta 'interfaz'.
    Útil para acceder a recursos de la GUI.
    """
    return os.path.join(get_project_root(), 'interfaz')


def get_resource_path(relative_path):
    """
    Construye la ruta absoluta a un recurso dentro de 'interfaz' usando su path relativo.
    
    Ejemplo:
        get_resource_path("recursos/sonidos/fin.wav")
    """
    base = get_base_path()
    return os.path.join(base, relative_path)


def get_estilo_path(nombre_qss):
    """
    Devuelve la ruta completa a un archivo .qss de estilo dentro de interfaz/estilos.
    """
    return get_resource_path(os.path.join("estilos", nombre_qss))


def get_imagen_path(nombre_img):
    """
    Devuelve la ruta completa a una imagen dentro de interfaz/recursos/imagenes.
    """
    return get_resource_path(os.path.join("recursos", "imagenes", nombre_img))


def get_sonido_path(nombre_sonido):
    """
    Devuelve la ruta completa a un archivo de sonido dentro de interfaz/recursos/sonidos.
    """
    return get_resource_path(os.path.join("recursos", "sonidos", nombre_sonido))


def get_config_path(nombre_json):
    """
    Devuelve la ruta al archivo JSON de configuración ubicado en procesamiento/configs.

    Si el programa está empaquetado (--onefile) y se ejecuta desde /tmp,
    copia los archivos de configuración a una carpeta temporal para que sean editables.
    """
    import tempfile

    base = get_project_root()
    config_path = os.path.join(base, "procesamiento", "configs", nombre_json)

    # Modo empaquetado: redirige a carpeta temporal editable
    if getattr(sys, 'frozen', False) and base.startswith("/tmp/onefile_"):
        tmp_config_dir = os.path.join(tempfile.gettempdir(), "radproc_config")
        os.makedirs(tmp_config_dir, exist_ok=True)
        tmp_config_path = os.path.join(tmp_config_dir, nombre_json)

        if not os.path.exists(tmp_config_path):
            try:
                shutil.copy2(config_path, tmp_config_path)
            except Exception as e:
                print(f"Error copiando config a editable: {e}")
        return tmp_config_path

    return config_path


def get_python_executable():
    """
    Devuelve la ruta del ejecutable de Python disponible en el sistema.
    Prioriza python3 > python > el ejecutable actual.
    """
    return shutil.which("python3") or shutil.which("python") or sys.executable











