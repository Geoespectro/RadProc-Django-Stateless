/* main.js — STATeless
   Funciones globales comunes a todo el sitio
   ------------------------------------------
   - Alternancia modo claro/oscuro persistente
   - Aplicación automática según preferencia guardada
   - Apertura de vista de Configuraciones sin exigir archivo
*/

/**
 * Alterna entre modo claro y oscuro y guarda preferencia en localStorage.
 */
function alternarModo() {
  const body = document.body;
  const esModoClaro = body.classList.contains('modo-claro');

  body.classList.toggle('modo-claro');
  body.classList.toggle('modo-oscuro');

  localStorage.setItem('modo', esModoClaro ? 'oscuro' : 'claro');
}

/**
 * Al cargar cualquier página, se aplica el modo guardado
 * y se reinicia la barra de progreso si existe.
 */
document.addEventListener('DOMContentLoaded', () => {
  const modo = localStorage.getItem('modo');
  const body = document.body;

  if (modo === 'oscuro') {
    body.classList.remove('modo-claro');
    body.classList.add('modo-oscuro');
  } else {
    body.classList.remove('modo-oscuro');
    body.classList.add('modo-claro');
  }

  const barra = document.getElementById('barra-progreso');
  if (barra) {
    barra.style.width = '0%';
    barra.innerText = '0%';
  }
});

/**
 * Abre Configuraciones en base al tipo seleccionado,
 * sin exigir archivo (flujo stateless).
 * Antes de navegar, guardamos el contenido del LOG para restaurarlo al volver.
 */
function abrirConfiguraciones() {
  const select = document.getElementById('tipo-medicion');
  const tipo = (select && select.value) || '';

  if (!tipo) {
    if (typeof mostrarToast === 'function') {
      mostrarToast("⚠️ Primero selecciona un tipo de medición (Agua o Suelo).");
    } else {
      alert("⚠️ Primero selecciona un tipo de medición (Agua o Suelo).");
    }
    return;
  }

  // Si ya hay ZIP seleccionado, avisamos que habrá que recargarlo al volver
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

  // Navegamos en la misma pestaña; dejamos que el backend devuelva el log nuevo
  window.location.href = `/configuraciones/?tipo=${encodeURIComponent(tipo)}`;
}
function abrirConfiguraciones() {
  const select = document.getElementById('tipo-medicion');
  const tipo = (select && select.value) || '';

  if (!tipo) {
    if (typeof mostrarToast === 'function') {
      mostrarToast("⚠️ Primero selecciona un tipo de medición (Agua o Suelo).");
    } else {
      alert("⚠️ Primero selecciona un tipo de medición (Agua o Suelo).");
    }
    return;
  }

  // Si ya hay ZIP seleccionado, avisamos que habrá que recargarlo al volver
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

  // Navegamos en la misma pestaña; dejamos que el backend devuelva el log nuevo
  window.location.href = `/configuraciones/?tipo=${encodeURIComponent(tipo)}`;
}


/**
 * Muestra un mensaje emergente tipo toast (fallback simple).
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

  setTimeout(() => {
    toast.classList.add("fade-out");
    setTimeout(() => toast.remove(), 1000);
  }, 3000);
}
