// ============================================================================
// main.js — Funciones globales del sitio RadProc WEB
// ---------------------------------------------------------------------------
// Contiene:
//  - Alternancia entre modo claro / oscuro (con persistencia en localStorage)
//  - Aplicación del modo guardado al iniciar cada página
//  - Apertura de la vista "Configuraciones" con lógica stateless
//  - Sistema básico de avisos tipo toast (fallback)
// ============================================================================

/**
 * Alterna entre modo claro y oscuro y guarda la preferencia.
 */
function alternarModo() {
  const body = document.body;
  const esModoClaro = body.classList.contains("modo-claro");

  body.classList.toggle("modo-claro");
  body.classList.toggle("modo-oscuro");

  localStorage.setItem("modo", esModoClaro ? "oscuro" : "claro");
}

/**
 * Aplica el modo guardado al cargar cualquier página.
 * También reinicia la barra de progreso si existe.
 */
document.addEventListener("DOMContentLoaded", () => {
  const modo = localStorage.getItem("modo");
  const body = document.body;

  if (modo === "oscuro") {
    body.classList.remove("modo-claro");
    body.classList.add("modo-oscuro");
  } else {
    body.classList.remove("modo-oscuro");
    body.classList.add("modo-claro");
  }

  const barra = document.getElementById("barra-progreso");
  if (barra) {
    barra.style.width = "0%";
    barra.innerText = "0%";
  }
});

/**
 * Abre la vista de Configuraciones según el tipo de medición actual.
 * Si ya hay un ZIP cargado, avisa al usuario que deberá recargarlo al volver.
 */
function abrirConfiguraciones() {
  const select = document.getElementById("tipo-medicion");
  const tipo = (select && select.value) || "";

  if (!tipo) {
    if (typeof mostrarToast === "function") {
      mostrarToast("⚠️ Primero selecciona un tipo de medición (Agua o Suelo).");
    } else {
      alert("⚠️ Primero selecciona un tipo de medición (Agua o Suelo).");
    }
    return;
  }

  const yaHayZip = sessionStorage.getItem("archivo_seleccionado") === "1";
  if (yaHayZip) {
    const continuar = confirm(
      "Vas a abrir Configuraciones habiendo seleccionado un ZIP.\n" +
        "Cuando regreses, por políticas del navegador tendrás que volver a cargar el ZIP antes de procesar.\n\n" +
        "¿Deseas continuar?"
    );
    if (!continuar) return;
    sessionStorage.setItem("fue_config_con_zip", "1");
  } else {
    sessionStorage.removeItem("fue_config_con_zip");
  }

  // Navegamos a la vista de configuraciones
  window.location.href = `/configuraciones/?tipo=${encodeURIComponent(tipo)}`;
}

/**
 * Muestra un mensaje emergente tipo toast (fallback si no hay librería externa).
 */
function mostrarToast(mensaje) {
  const container = document.getElementById("toast-container");

  if (!container) {
    alert(mensaje);
    return;
  }

  const toast = document.createElement("div");
  toast.className = "toast-aviso";
  toast.innerText = mensaje;

  container.appendChild(toast);

  // Desaparece luego de 3 segundos
  setTimeout(() => {
    toast.classList.add("fade-out");
    setTimeout(() => toast.remove(), 1000);
  }, 3000);
}
