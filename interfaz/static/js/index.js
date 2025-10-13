// ============================================================================
// index.js — Lógica principal de la página "Inicio"
// ---------------------------------------------------------------------------
// Controla:
//  - Selección de tipo de medición (agua/suelo)
//  - Carga y validación de ZIP
//  - Integración opcional de archivo Spectralon
//  - Envío y descarga de resultados (fetch)
//  - Limpieza del estado local (sesión)
// ============================================================================

document.addEventListener("DOMContentLoaded", function () {
  // === Referencias DOM ===
  const tipoSelect = document.getElementById("tipo-medicion");
  const hiddenMedicion = document.getElementById("tipo-medicion-hidden");
  const formDatos = document.getElementById("form-datos");
  const btnProcesar = document.getElementById("btn-procesar");
  const inputArchivo = formDatos?.querySelector('input[name="zipfile"]');
  const nombreSpan = document.getElementById("nombre-carpeta-datos");
  const logArea = document.getElementById("log-area");

  // === Spectralon ===
  const btnCambiarSpectralon = document.getElementById("btn-cambiar-spectralon");
  const inputSpectralon = document.getElementById("input-spectralon");
  const nombreSpectralon = document.getElementById("nombre-spectralon");

  // ==========================================================================
  // 🔧 Helpers UI (funciones pequeñas reutilizables)
  // ==========================================================================

  /** Muestra/oculta estado de procesamiento visual */
  function setProcesando(isOn) {
    if (!btnProcesar || !formDatos) return;
    btnProcesar.disabled = isOn;
    btnProcesar.textContent = isOn ? "Procesando…" : "Procesar y descargar";
    formDatos.classList.toggle("opacity-75", isOn);
  }

  /** Actualiza mensaje del nombre del archivo ZIP */
  function setNombreArchivoOk(nombre) {
    if (!nombreSpan) return;
    nombreSpan.innerHTML = nombre
      ? `<span class="text-success">✅ Archivo seleccionado: ${nombre}</span>`
      : `<span class="text-muted">Ningún archivo seleccionado</span>`;
  }

  /** Muestra aviso de recarga requerida */
  function setNombreArchivoRequerido(msg = "Debes volver a cargar el archivo ZIP antes de procesar.") {
    if (nombreSpan) nombreSpan.innerHTML = `<span class="text-warning">⚠️ ${msg}</span>`;
  }

  /** Habilita la carga solo si hay tipo seleccionado */
  function habilitarCargaSiHayTipo() {
    const hayTipo = !!(tipoSelect && tipoSelect.value);
    inputArchivo && (inputArchivo.disabled = !hayTipo);
    btnProcesar && (btnProcesar.disabled = !hayTipo);
  }

  /** Aplica color de fondo al select según tipo */
  function aplicarColorSelect() {
    if (!tipoSelect) return;
    tipoSelect.classList.remove("agua", "suelo");
    const v = (tipoSelect.value || "").toLowerCase();
    if (v === "agua" || v === "suelo") tipoSelect.classList.add(v);
  }

  // ==========================================================================
  // 🔄 Estado inicial
  // ==========================================================================

  if (hiddenMedicion && tipoSelect) hiddenMedicion.value = tipoSelect.value || "";
  aplicarColorSelect();
  habilitarCargaSiHayTipo();

  if (sessionStorage.getItem("fue_config_con_zip") === "1") {
    // Volvimos desde Configuraciones con ZIP previo
    sessionStorage.removeItem("fue_config_con_zip");
    sessionStorage.removeItem("archivo_seleccionado");
    sessionStorage.removeItem("zip_name");
    mostrarToast?.("ℹ️ Modificaste Configuraciones. Por favor, vuelve a cargar el archivo ZIP antes de procesar.") ??
      alert("ℹ️ Modificaste Configuraciones. Por favor, vuelve a cargar el archivo ZIP antes de procesar.");
    setNombreArchivoRequerido();
  } else {
    setNombreArchivoOk("");
  }

  // ==========================================================================
  // 🧭 Select tipo de medición
  // ==========================================================================

  if (tipoSelect && !tipoSelect.dataset.bound) {
    tipoSelect.addEventListener("change", function () {
      const valor = this.value || "";
      hiddenMedicion && (hiddenMedicion.value = valor);
      aplicarColorSelect();
      habilitarCargaSiHayTipo();

      if (sessionStorage.getItem("archivo_seleccionado") === "1") {
        mostrarToast?.("ℹ️ Cambiaste el tipo de medición. Verifica que el ZIP corresponda al tipo seleccionado.") ??
          alert("ℹ️ Cambiaste el tipo de medición. Verifica que el ZIP corresponda al tipo seleccionado.");
      }
    });
    tipoSelect.dataset.bound = "1";
  }

  // ==========================================================================
  // 📁 Carga del ZIP principal
  // ==========================================================================

  if (inputArchivo && !inputArchivo.dataset.bound) {
    inputArchivo.addEventListener("click", (e) => {
      const hayTipo = !!(tipoSelect && tipoSelect.value);
      if (!hayTipo) {
        e.preventDefault();
        e.stopPropagation();
        mostrarToast?.("⚠️ Primero selecciona el tipo de medición (Agua o Suelo).") ??
          alert("⚠️ Primero selecciona el tipo de medición (Agua o Suelo).");
      }
    });

    inputArchivo.addEventListener("change", () => {
      const archivo = inputArchivo.files?.[0];
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

  // ==========================================================================
  // ⚪ Spectralon — carga temporal por ejecución
  // ==========================================================================

  if (btnCambiarSpectralon && !btnCambiarSpectralon.dataset.bound) {
    btnCambiarSpectralon.addEventListener("click", () => {
      inputSpectralon.value = "";
      inputSpectralon.click();
    });
    btnCambiarSpectralon.dataset.bound = "1";
  }

  if (inputSpectralon && !inputSpectralon.dataset.bound) {
    inputSpectralon.addEventListener("change", () => {
      const f = inputSpectralon.files?.[0];
      const def = nombreSpectralon.getAttribute("data-default") || "SRT-99-120.txt (por defecto)";
      if (f) {
        nombreSpectralon.textContent = `Spectralon seleccionado: ${f.name} (solo esta ejecución)`;
        nombreSpectralon.classList.remove("text-muted");
      } else {
        nombreSpectralon.textContent = def;
        nombreSpectralon.classList.add("text-muted");
      }
    });
    inputSpectralon.dataset.bound = "1";
  }

  // ==========================================================================
  // 🚀 Procesamiento principal (submit + descarga)
  // ==========================================================================

  if (formDatos && !formDatos.dataset.bound) {
    formDatos.addEventListener("submit", async function (ev) {
      ev.preventDefault();

      const hayTipo = !!tipoSelect.value;
      const tieneArchivo = inputArchivo?.files?.length > 0;

      if (!hayTipo) {
        mostrarToast?.("⚠️ Selecciona un tipo de medición antes de procesar.") ??
          alert("⚠️ Selecciona un tipo de medición antes de procesar.");
        return;
      }

      if (!tieneArchivo) {
        mostrarToast?.("⚠️ Debes seleccionar un archivo ZIP antes de procesar.") ??
          alert("⚠️ Debes seleccionar un archivo ZIP antes de procesar.");
        setNombreArchivoRequerido("Debes seleccionar un archivo ZIP.");
        return;
      }

      const fd = new FormData(formDatos);
      setProcesando(true);
      appendLog("⏳ Iniciando procesamiento…");

      try {
        const resp = await fetch(formDatos.action, { method: "POST", body: fd });
        if (!resp.ok) {
          const txt = await resp.text().catch(() => "");
          appendLog(`❌ Error del servidor (${resp.status}). ${txt || ""}`.trim());
          return;
        }

        const blob = await resp.blob();
        const dispo = resp.headers.get("Content-Disposition") || "";
        const filename = dispo.match(/filename="([^"]+)"/i)?.[1] || "resultados.zip";

        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);

        appendLog("✅ Procesamiento completado. Descarga iniciada.");
        playDoneSound?.();
      } catch (err) {
        appendLog(`❌ Error de red o del cliente: ${err}`);
      } finally {
        setProcesando(false);
      }
    });
    formDatos.dataset.bound = "1";
  }

  // ==========================================================================
  // 🧩 Próxima función (placeholder de desarrollo)
  // ==========================================================================

  const btnProx = document.getElementById("btn-proxima-funcion");
  if (btnProx && !btnProx.dataset.bound) {
    btnProx.addEventListener("click", () => {
      const modal = document.createElement("div");
      modal.classList.add("modal-prox");
      modal.innerHTML = `
        <div class="modal-prox-content">
          <h5>⚙️ Implementación en desarrollo</h5>
          <p>Esta funcionalidad estará disponible en futuras versiones de <strong>RadProc WEB</strong>.</p>
          <button id="cerrar-prox" class="btn btn-primary btn-sm mt-2">Cerrar</button>
        </div>`;
      document.body.appendChild(modal);
      document.getElementById("cerrar-prox").addEventListener("click", () => modal.remove());
    });
    btnProx.dataset.bound = "1";
  }

  // ==========================================================================
  // 🧹 Limpiar sesión (estado cliente)
  // ==========================================================================

  const formLimpiar = document.getElementById("form-limpiar") || document.querySelector('form[action$="limpiar_sesion/"]');
  if (formLimpiar && !formLimpiar.dataset.bound) {
    formLimpiar.addEventListener("submit", () => {
      try {
        sessionStorage.clear();
        tipoSelect.value = "";
        tipoSelect.classList.remove("agua", "suelo");
        inputArchivo.value = "";
        nombreSpan.innerHTML = `<span class="text-muted">Ningún archivo seleccionado</span>`;
        logArea.value = "";
        inputSpectralon.value = "";
        const def = nombreSpectralon.getAttribute("data-default") || "SRT-99-120.txt (por defecto)";
        nombreSpectralon.textContent = def;
        nombreSpectralon.classList.add("text-muted");
      } catch (e) {
        console.warn("No se pudo limpiar completamente el estado local:", e);
      }
    });
    formLimpiar.dataset.bound = "1";
  }
});

// ============================================================================
// 📋 Helpers globales del log
// ============================================================================
(function () {
  const getLogEl = () => document.getElementById("log-area");

  function appendLog(msg) {
    const el = getLogEl();
    if (!el) return;
    const ts = new Date().toLocaleString("es-AR", {
      year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit",
      hour12: false,
    });
    const line = `[${ts}] ${msg}`;
    el.value = (el.value ? el.value + "\n" : "") + line;
    el.scrollTop = el.scrollHeight;
  }

  function normalizeLogNewlines() {
    const el = getLogEl();
    if (el) {
      el.value = el.value.replace(/\\n/g, "\n");
      el.scrollTop = el.scrollHeight;
    }
  }

  function clearLog() {
    const el = getLogEl();
    if (el) el.value = "";
  }

  window.appendLog = appendLog;
  window.clearLog = clearLog;
  window.normalizeLogNewlines = normalizeLogNewlines;
  document.addEventListener("DOMContentLoaded", normalizeLogNewlines);
})();



