// ============================================================================
// main.js — Funciones globales del sitio RadProc WEB
// ---------------------------------------------------------------------------
// Contiene:
//   - Alternancia entre modo claro / oscuro (con persistencia en localStorage)
//   - Aplicación automática del modo guardado al iniciar
//   - Apertura de la vista “Configuraciones” con verificación de tipo de medición
//   - Sistema básico de avisos tipo toast (fallback sin librerías externas)
// ============================================================================


/* ============================================================================
   1) MODO CLARO / OSCURO — Alternancia manual y persistencia
============================================================================ */

/**
 * Alterna entre modo claro y oscuro y guarda la preferencia en localStorage.
 */
function alternarModo() {
  const body = document.body;
  const esModoClaro = body.classList.contains("modo-claro");

  body.classList.toggle("modo-claro");
  body.classList.toggle("modo-oscuro");

  // Guarda la preferencia actual
  localStorage.setItem("modo", esModoClaro ? "oscuro" : "claro");
}


/* ============================================================================
   2) APLICACIÓN AUTOMÁTICA DEL MODO GUARDADO AL INICIAR
============================================================================ */

document.addEventListener("DOMContentLoaded", () => {
  const modo = localStorage.getItem("modo");
  const body = document.body;

  // Aplica la clase correspondiente al modo guardado
  if (modo === "oscuro") {
    body.classList.remove("modo-claro");
    body.classList.add("modo-oscuro");
  } else {
    body.classList.remove("modo-oscuro");
    body.classList.add("modo-claro");
  }

  // Reinicia barra de progreso si existe (usada en procesamientos futuros)
  const barra = document.getElementById("barra-progreso");
  if (barra) {
    barra.style.width = "0%";
    barra.innerText = "0%";
  }
});


/* ============================================================================
   3) NAVEGACIÓN — Apertura de la vista “Configuraciones”
============================================================================ */

/**
 * Abre la vista de Configuraciones según el tipo de medición seleccionado.
 * Si no hay tipo elegido, muestra advertencia. Si ya hay un ZIP cargado,
 * solicita confirmación al usuario (por requerimiento de recarga).
 */
function abrirConfiguraciones() {
  // Si ya estamos dentro de la vista de configuraciones, no hacer nada
  if (window.location.pathname.includes("/configuraciones")) {
    console.log("Ya estás en Configuraciones, no se muestra mensaje.");
    return;
  }

  const select = document.getElementById("tipo-medicion");
  const tipo = (select && select.value) || "";

  // Sin tipo seleccionado → aviso y salida
  if (!tipo) {
    if (typeof mostrarToast === "function") {
      mostrarToast("⚠️ Primero selecciona un tipo de medición (Agua o Suelo).");
    } else {
      alert("⚠️ Primero selecciona un tipo de medición (Agua o Suelo).");
    }
    return;
  }

  // Si hay ZIP cargado, advertimos antes de navegar
  const yaHayZip = sessionStorage.getItem("archivo_seleccionado") === "1";
  if (yaHayZip) {
    const continuar = confirm(
      "Vas a abrir Configuraciones habiendo seleccionado un ZIP.\n" +
      "Cuando regreses, por políticas del navegador deberás volver a cargar el ZIP antes de procesar.\n\n" +
      "¿Deseas continuar?"
    );

    if (!continuar) return;
    sessionStorage.setItem("fue_config_con_zip", "1");
  } else {
    sessionStorage.removeItem("fue_config_con_zip");
  }

  // Redirige a la vista de configuraciones con el tipo actual
  window.location.href = `/configuraciones/?tipo=${encodeURIComponent(tipo)}`;
}


/* ============================================================================
   4) SISTEMA DE AVISOS — Toast simple nativo
============================================================================ */

/**
 * Muestra un mensaje emergente tipo toast.
 * Si no hay contenedor de toasts, usa alert() como fallback.
 * @param {string} mensaje - Texto a mostrar
 */
function mostrarToast(mensaje) {
  const container = document.getElementById("toast-container");

  // Si no hay contenedor, usar alert nativo
  if (!container) {
    alert(mensaje);
    return;
  }

  // Crear elemento toast
  const toast = document.createElement("div");
  toast.className = "toast-aviso";
  toast.innerText = mensaje;
  container.appendChild(toast);

  // Desaparece suavemente luego de 3 segundos
  setTimeout(() => {
    toast.classList.add("fade-out");
    setTimeout(() => toast.remove(), 1000);
  }, 3000);
}
