# =============================================================================
# procesamiento/base.py
# -----------------------------------------------------------------------------
# Define el contrato base (interfaz) para todos los procesadores del sistema.
# Cada procesador (por ejemplo, agua.py o suelo.py) debe implementar esta
# estructura de llamada para mantener compatibilidad con el núcleo (service.py).
#
# Estructura general:
#   1) Imports y dependencias
#   2) Definición del protocolo Processor
# =============================================================================

from typing import Protocol, Dict, Any


# =============================================================================
# 1️⃣ PROTOCOLO BASE DE PROCESADORES
# -----------------------------------------------------------------------------
# El protocolo Processor establece la firma esperada de todos los módulos de
# procesamiento. Asegura que cada procesador implemente un método __call__
# con parámetros y retorno compatibles con el core.
# =============================================================================
class Processor(Protocol):
    """
    Contrato formal para todos los procesadores de RadProc.
    Cada procesador debe implementar un callable con la siguiente firma:

    Args:
        input_dir (str): Ruta al directorio temporal con los datos de entrada.
        output_dir (str): Ruta al directorio temporal donde se guardarán los resultados.
        config (Dict[str, Any]): Diccionario de configuración específico para la ejecución.

    Returns:
        Dict[str, Any]: Metadatos resultantes del procesamiento (por ejemplo,
        estadísticas o información adicional sobre los archivos generados).
    """

    def __call__(self, *, input_dir: str, output_dir: str, config: Dict[str, Any]) -> Dict[str, Any]:
        ...


# =============================================================================
# FIN DEL MÓDULO
# -----------------------------------------------------------------------------
# Este archivo actúa como contrato abstracto para los procesadores.
# Cualquier módulo que implemente la lógica de cálculo debe seguir este
# protocolo para integrarse correctamente con procesamiento/service.py.
# =============================================================================

