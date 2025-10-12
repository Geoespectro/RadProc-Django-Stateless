// index.js — consolidado y idempotente
// - Maneja selección de tipo, validaciones, submit via fetch + descarga, sonido fin
// - Maneja ZIP y Spectralon (sin duplicar listeners)
// - Log helpers (appendLog / clearLog / normalizeLogNewlines)
// - Limpieza de estado en "Limpiar"

document.addEventListener("DOMContentLoaded", function () {
  // ======= Referencias DOM =======
  const tipoSelect        = document.getElementById("tipo-medicion");
  const hiddenMedicion    = document.getElementById("tipo-medicion-hidden");
  const formDatos         = document.getElementById("form-datos");
  const btnProcesar       = document.getElementById("btn-procesar") || (formDatos ? formDatos.querySelector('button[type="submit"]') : null);
  const inputArchivo      = formDatos ? formDatos.querySelector('input[name="zipfile"]') : null;

  // UI auxiliares
  const nombreSpan        = document.getElementById("nombre-carpeta-datos");
  const logArea           = document.getElementById('log-area');

  // Spectralon
  const btnCambiarSpectralon = document.getElementById("btn-cambiar-spectralon");
  const inputSpectralon      = document.getElementById("input-spectralon");
  const nombreSpectralon     = document.getElementById("nombre-spectralon");

  // ======= Helpers UI =======
  function setProcesando(isOn) {
    if (!btnProcesar || !formDatos) return;
    if (isOn) {
      btnProcesar.disabled = true;
      btnProcesar.textContent = 'Procesando…';
      formDatos.classList.add('opacity-75');
    } else {
      btnProcesar.disabled = false;
      btnProcesar.textContent = 'Procesar y descargar';
      formDatos.classList.remove('opacity-75');
    }
  }

  function setNombreArchivoOk(nombre) {
    if (!nombreSpan) return;
    if (nombre) {
      nombreSpan.innerHTML = `<span class="text-success">✅ Archivo seleccionado: ${nombre}</span>`;
    } else {
      nombreSpan.innerHTML = `<span class="text-muted">Ningún archivo seleccionado</span>`;
    }
  }

  function setNombreArchivoRequerido(msg = "Debes volver a cargar el archivo ZIP antes de procesar.") {
    if (!nombreSpan) return;
    nombreSpan.innerHTML = `<span class="text-warning">⚠️ ${msg}</span>`;
  }

  function habilitarCargaSiHayTipo() {
    const hayTipo = !!(tipoSelect && tipoSelect.value);
    if (inputArchivo) inputArchivo.disabled = !hayTipo;
    if (btnProcesar) btnProcesar.disabled = !hayTipo;
  }

  function aplicarColorSelect() {
    if (!tipoSelect) return;
    tipoSelect.classList.remove("agua", "suelo");
    const v = (tipoSelect.value || "").toLowerCase();
    if (v === "agua" || v === "suelo") tipoSelect.classList.add(v);
  }

  // ======= Estado inicial =======
  if (hiddenMedicion && tipoSelect) hiddenMedicion.value = tipoSelect.value || "";
  aplicarColorSelect();
  habilitarCargaSiHayTipo();

  // Si volvimos de Config con un ZIP previamente elegido: limpiar estado y avisar
  if (sessionStorage.getItem("fue_config_con_zip") === "1") {
    sessionStorage.removeItem("fue_config_con_zip");
    sessionStorage.removeItem("archivo_seleccionado");
    sessionStorage.removeItem("zip_name");
    if (typeof mostrarToast === 'function') {
      mostrarToast("ℹ️ Modificaste Configuraciones. Por favor, vuelve a cargar el archivo ZIP antes de procesar.");
    } else {
      alert("ℹ️ Modificaste Configuraciones. Por favor, vuelve a cargar el archivo ZIP antes de procesar.");
    }
    setNombreArchivoRequerido();
  } else {
    setNombreArchivoOk("");
  }

  // ======= Cambios de tipo =======
  if (tipoSelect && !tipoSelect.dataset.bound) {
    tipoSelect.addEventListener("change", function () {
      const valor = this.value || "";
      if (hiddenMedicion) hiddenMedicion.value = valor;
      aplicarColorSelect();
      habilitarCargaSiHayTipo();

      if (sessionStorage.getItem("archivo_seleccionado") === "1") {
        if (typeof mostrarToast === 'function') {
          mostrarToast("ℹ️ Cambiaste el tipo de medición. Verifica que el ZIP corresponda al tipo seleccionado.");
        } else {
          alert("ℹ️ Cambiaste el tipo de medición. Verifica que el ZIP corresponda al tipo seleccionado.");
        }
      }
    });
    tipoSelect.dataset.bound = "1";
  }

  // ======= Interacción con input file (ZIP) =======
  if (inputArchivo && !inputArchivo.dataset.bound) {
    // Bloquear diálogo si no hay tipo
    inputArchivo.addEventListener("click", (e) => {
      const hayTipo = !!(tipoSelect && tipoSelect.value);
      if (!hayTipo) {
        e.preventDefault();
        e.stopPropagation();
        if (typeof mostrarToast === 'function') {
          mostrarToast("⚠️ Primero selecciona el tipo de medición (Agua o Suelo).");
        } else {
          alert("⚠️ Primero selecciona el tipo de medición (Agua o Suelo).");
        }
      }
    });

    // Guardar SOLO el nombre del archivo (no el contenido)
    inputArchivo.addEventListener("change", () => {
      const archivo = inputArchivo.files && inputArchivo.files[0];
      if (archivo) {
        sessionStorage.setItem("zip_name", archivo.name);
        sessionStorage.setItem("archivo_seleccionado", "1");
        setNombreArchivoOk(archivo.name);
      } else {
        sessionStorage.removeItem("zip_name");
        sessionStorage.removeItem("archivo_seleccionado");
        setNombreArchivoOk("");
      }
    });
    inputArchivo.dataset.bound = "1";
  }

  // ======= Spectralon (idempotente, sin doble apertura) =======
  if (btnCambiarSpectralon && !btnCambiarSpectralon.dataset.bound) {
    btnCambiarSpectralon.addEventListener("click", () => {
      if (inputSpectralon) {
        // Fuerza que 'change' dispare aunque el usuario elija el mismo archivo
        inputSpectralon.value = '';
        inputSpectralon.click();
      }
    });
    btnCambiarSpectralon.dataset.bound = "1";
  }

  if (inputSpectralon && !inputSpectralon.dataset.bound) {
    inputSpectralon.addEventListener("change", () => {
      const f = inputSpectralon.files && inputSpectralon.files[0];
      if (f && nombreSpectralon) {
        nombreSpectralon.textContent = `Spectralon seleccionado: ${f.name} (solo esta ejecución)`;
        nombreSpectralon.classList.remove('text-muted');
      } else if (nombreSpectralon) {
        const def = nombreSpectralon.getAttribute('data-default') || "SRT-99-120.txt (por defecto)";
        nombreSpectralon.textContent = def;
        nombreSpectralon.classList.add('text-muted');
      }
    });
    inputSpectralon.dataset.bound = "1";
  }

  // ======= Submit via fetch (descarga ZIP + sonido + logs) =======
  if (formDatos && !formDatos.dataset.bound) {
    formDatos.addEventListener("submit", async function (ev) {
      ev.preventDefault();

      const hayTipo = !!(tipoSelect && tipoSelect.value);
      const tieneArchivo = inputArchivo && inputArchivo.files && inputArchivo.files.length > 0;

      if (!hayTipo) {
        typeof mostrarToast === 'function'
          ? mostrarToast("⚠️ Selecciona un tipo de medición antes de procesar.")
          : alert("⚠️ Selecciona un tipo de medición antes de procesar.");
        return;
      }
      if (!tieneArchivo) {
        typeof mostrarToast === 'function'
          ? mostrarToast("⚠️ Debes seleccionar un archivo ZIP antes de procesar.")
          : alert("⚠️ Debes seleccionar un archivo ZIP antes de procesar.");
        setNombreArchivoRequerido("Debes seleccionar un archivo ZIP.");
        return;
      }

      const fd = new FormData(formDatos);
      setProcesando(true);
      appendLog('⏳ Iniciando procesamiento…');

      try {
        const resp = await fetch(formDatos.action, {
          method: 'POST',
          body: fd
          // CSRF no requerido: /procesar/ es csrf_exempt en el backend
        });

        if (!resp.ok) {
          const txt = await resp.text().catch(() => '');
          appendLog(`❌ Error del servidor (${resp.status}). ${txt || ''}`.trim());
          setProcesando(false);
          return;
        }

        const blob = await resp.blob();
        const dispo = resp.headers.get('Content-Disposition') || '';
        const m = dispo.match(/filename="([^"]+)"/i);
        const filename = m ? m[1] : 'resultados.zip';

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);

        appendLog('✅ Procesamiento completado. Descarga iniciada.');
        if (typeof playDoneSound === 'function') playDoneSound();
      } catch (err) {
        appendLog(`❌ Error de red o del cliente: ${err}`);
      } finally {
        setProcesando(false);
      }
    });
    formDatos.dataset.bound = "1";
  }

  // ======= Exportar log =======
  const btnExp = document.getElementById('btn-exportar-log');
  if (btnExp && logArea && !btnExp.dataset.bound) {
    btnExp.addEventListener('click', () => {
      const blob = new Blob([logArea.value || ''], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'radproc_log.txt';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    });
    btnExp.dataset.bound = "1";
  }

  // ======= Limpiar (reseteo cliente antes del flush de sesión) =======
  const formLimpiar = document.getElementById("form-limpiar") ||
                      document.querySelector('form[action$="limpiar_sesion/"]');
  if (formLimpiar && !formLimpiar.dataset.bound) {
    formLimpiar.addEventListener("submit", function () {
      try {
        sessionStorage.clear();
        if (tipoSelect) {
          tipoSelect.value = "";
          tipoSelect.classList.remove("agua", "suelo");
        }
        if (inputArchivo) inputArchivo.value = "";
        if (nombreSpan) {
          nombreSpan.innerHTML = `<span class="text-muted">Ningún archivo seleccionado</span>`;
        }
        if (logArea) logArea.value = "";
        if (inputSpectralon && nombreSpectralon) {
          inputSpectralon.value = "";
          const def = nombreSpectralon.getAttribute('data-default') || "SRT-99-120.txt (por defecto)";
          nombreSpectralon.textContent = def;
          nombreSpectralon.classList.add('text-muted');
        }
      } catch (e) {
        console.warn("No se pudo limpiar completamente el estado local:", e);
      }
      // El submit continúa y el backend hace request.session.flush()
    });
    formLimpiar.dataset.bound = "1";
  }
});

// ======= Helpers de LOG en pantalla =======
(function () {
  const getLogEl = () => document.getElementById('log-area');

  function appendLog(msg) {
    const el = getLogEl();
    if (!el) return;
    const ts = new Date().toLocaleString('es-AR', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
      hour12: false
    });
    const line = `[${ts}] ${msg}`;
    el.value = (el.value ? el.value + '\n' : '') + line;
    el.scrollTop = el.scrollHeight;
  }

  function normalizeLogNewlines() {
    const el = getLogEl();
    if (!el) return;
    el.value = el.value.replace(/\\n/g, '\n');
    el.scrollTop = el.scrollHeight;
  }

  function clearLog() {
    const el = getLogEl();
    if (el) el.value = '';
  }

  window.appendLog = appendLog;
  window.clearLog = clearLog;
  window.normalizeLogNewlines = normalizeLogNewlines;

  document.addEventListener('DOMContentLoaded', normalizeLogNewlines);
})();


