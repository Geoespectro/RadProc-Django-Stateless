# =============================================================================
# procesamiento/validators/config_validator.py
# -----------------------------------------------------------------------------
# Funciones de validación de coherencia entre el set de datos descomprimido
# y la configuración seleccionada por el usuario (spectrum, meas_order, target_list).
#
# Este módulo se ejecuta antes del procesamiento principal, garantizando que:
#   - No se procese un set de datos incompatible con los parámetros definidos.
#   - Se devuelvan mensajes claros y estructurados en caso de error (422).
#   - Se distingan errores críticos (bloqueantes) de avisos leves (no bloqueantes).
#
# =============================================================================

import os
from typing import Dict, Any, List


# =============================================================================
# FUNCIÓN PRINCIPAL: validar_configuracion()
# -----------------------------------------------------------------------------
# Verifica si la configuración del usuario es coherente con la estructura real
# del set de datos descomprimido.
#
# Entradas:
#   - input_dir : str → Ruta a la carpeta descomprimida con archivos de medición.
#   - config    : dict → Configuración actual (incluye spectrum, meas_order, target_list).
#
# Salida:
#   - dict con las claves:
#       valido : bool  → True si puede procesarse; False si debe bloquearse.
#       motivo : str   → Mensaje explicativo (errores o avisos concatenados).
# =============================================================================
def validar_configuracion(input_dir: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Valida coherencia estructural y semántica entre el conjunto de datos y
    los parámetros definidos por el usuario.

    Esta función se divide en tres niveles:
        1) Estructura base (existencia de datos y parámetros esenciales).
        2) Consistencia aritmética (cantidad esperada de archivos por medición).
        3) Coherencia nominal (nombres de targets presentes o no en los datos).
    """

    # -------------------------------------------------------------------------
    # Inicialización de estructuras de control
    # -------------------------------------------------------------------------
    errores: List[str] = []   # Errores críticos → bloquean la ejecución
    avisos: List[str] = []    # Avisos no críticos → informativos

    # -------------------------------------------------------------------------
    # 1️⃣ Validación básica de ruta y estructura de archivos
    # -------------------------------------------------------------------------
    if not os.path.isdir(input_dir):
        return {"valido": False, "motivo": f"La ruta de entrada no existe: {input_dir}"}

    txt_files: List[str] = []
    for root, _, files in os.walk(input_dir):
        for name in files:
            if name.lower().endswith(".txt"):
                txt_files.append(os.path.join(root, name))

    if not txt_files:
        errores.append("El conjunto de datos no contiene archivos .txt de medición.")

    # -------------------------------------------------------------------------
    # 2️⃣ Validación de parámetros esenciales de configuración
    # -------------------------------------------------------------------------
    spectrum = int(config.get("spectrum", 0))
    meas_order = config.get("meas_order", [])
    target_list = config.get("target_list", [])

    if not spectrum:
        errores.append("Falta el parámetro 'spectrum' o es cero.")
    if not meas_order:
        errores.append("Falta el parámetro 'meas_order' o está vacío.")

    # Si hay errores estructurales graves, no tiene sentido continuar
    if errores:
        return {"valido": False, "motivo": " | ".join(errores)}

    # -------------------------------------------------------------------------
    # 3️⃣ Cálculo y verificación del número esperado de archivos
    # -------------------------------------------------------------------------
    n_one_meas = spectrum * len(meas_order)
    total_files = len(txt_files)

    if total_files % n_one_meas != 0:
        errores.append(
            f"Incompatibilidad entre set de datos y configuración.\n"
            f"- Total de archivos: {total_files}\n"
            f"- Esperados por medición: {n_one_meas} "
            f"(spectrum={spectrum} × meas_order={len(meas_order)})"
        )

    # -------------------------------------------------------------------------
    # 4️⃣ Validación opcional de coincidencia de nombres (solo aviso)
    # -------------------------------------------------------------------------
    nombres_archivos = [os.path.basename(f).lower() for f in txt_files]
    patrones_targets = [t.lower().replace(" ", "_") for t in target_list]

    if target_list:
        coincidencias = sum(
            any(pt in n for pt in patrones_targets)
            for n in nombres_archivos
        )
        if coincidencias == 0:
            avisos.append(
                "Los nombres definidos en 'target_list' no coinciden con los archivos del conjunto."
            )

    # -------------------------------------------------------------------------
    # 5️⃣ Resultado final: prioriza errores críticos sobre avisos
    # -------------------------------------------------------------------------
    if errores:
        # Bloqueo: se devuelve False (detiene ejecución)
        return {"valido": False, "motivo": " | ".join(errores)}
    elif avisos:
        # Aviso: no detiene ejecución, pero se informa
        return {"valido": True, "motivo": "Aviso: " + " | ".join(avisos)}
    else:
        # Todo correcto
        return {"valido": True, "motivo": None}


# =============================================================================
# FIN DEL MÓDULO
# -----------------------------------------------------------------------------
# Este módulo actúa como capa de seguridad previa al procesamiento principal.
# Su objetivo es garantizar integridad estructural antes de ejecutar los scripts
# de cálculo (agua.py / suelo.py). Cualquier ampliación futura debe mantener
# el esquema de validación progresiva:
#   1) Estructura → 2) Coherencia → 3) Correspondencia nominal.
# =============================================================================




