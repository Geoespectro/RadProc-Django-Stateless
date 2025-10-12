# procesamiento/base.py

from typing import Protocol, Dict, Any

class Processor(Protocol):
    """
    Contrato para todos los procesadores de RadProc.
    Cada procesador debe implementar un callable con la siguiente firma:

    Args:
        input_dir (str): Ruta al directorio temporal con los datos de entrada.
        output_dir (str): Ruta al directorio temporal donde se guardarán los resultados.
        config (Dict[str, Any]): Diccionario de configuración específico para la ejecución.

    Returns:
        Dict[str, Any]: Metadatos resultantes del procesamiento (por ejemplo, estadísticas o info de salida).
    """

    def __call__(self, *, input_dir: str, output_dir: str, config: Dict[str, Any]) -> Dict[str, Any]:
        ...
