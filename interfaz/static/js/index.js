// index.js — stateless: sin persistencia automática del LOG y limpieza total al "Limpiar"
document.addEventListener("DOMContentLoaded", function () {
  const tipoSelect = document.getElementById("tipo-medicion");
  const hiddenMedicion = document.getElementById("tipo-medicion-hidden");

  // Tomamos el input de archivo por name="zipfile" (tu HTML)
  const inputArchivo = document.querySelector('input[name="zipfile"]');

  const formDatos = document.getElementById("form-datos");
  const btnProcesar =
    document.getElementById("btn-procesar") ||
    (formDatos ? formDatos.querySelector('button[type="submit"]') : null);

  const nombreSpan = document.getElementById("nombre-carpeta-datos");
  const logArea = document.querySelector('textarea.form-control');

  // --- Helpers UI ---
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

  // --- Estado inicial ---
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
    }
    setNombreArchivoRequerido();
  } else {
    setNombreArchivoOk("");
  }

  // --- Cambios de tipo ---
  if (tipoSelect) {
    tipoSelect.addEventListener("change", function () {
      const valor = this.value || "";
      if (hiddenMedicion) hiddenMedicion.value = valor;
      aplicarColorSelect();
      habilitarCargaSiHayTipo();

      if (sessionStorage.getItem("archivo_seleccionado") === "1") {
        if (typeof mostrarToast === 'function') {
          mostrarToast("ℹ️ Cambiaste el tipo de medición. Verifica que el ZIP corresponda al tipo seleccionado.");
        }
      }
    });
  }

  // --- Interacción con input file ---
  if (inputArchivo) {
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
  }

  // --- Validación al enviar ---
  if (formDatos) {
    formDatos.addEventListener("submit", function (e) {
      const hayTipo = !!(tipoSelect && tipoSelect.value);
      const tieneArchivo = inputArchivo && inputArchivo.files && inputArchivo.files.length > 0;

      if (!hayTipo) {
        e.preventDefault();
        typeof mostrarToast === 'function'
          ? mostrarToast("⚠️ Selecciona un tipo de medición antes de procesar.")
          : alert("⚠️ Selecciona un tipo de medición antes de procesar.");
        return;
      }
      if (!tieneArchivo) {
        e.preventDefault();
        typeof mostrarToast === 'function'
          ? mostrarToast("⚠️ Debes seleccionar un archivo ZIP antes de procesar.")
          : alert("⚠️ Debes seleccionar un archivo ZIP antes de procesar.");
        setNombreArchivoRequerido("Debes seleccionar un archivo ZIP.");
        return;
      }
    });
  }

  // === Spectralon auto-submit (si está en esta página) ===
  const inputSpectralon = document.getElementById("input-spectralon");
  const formSpectralon = document.getElementById("form-spectralon");
  if (inputSpectralon && formSpectralon) {
    inputSpectralon.addEventListener("change", () => {
      if (inputSpectralon.files.length > 0) {
        formSpectralon.submit();
      }
    });
  }

  // ====== LIMPIAR: borra todo el estado del lado cliente antes de salir ======
  (function () {
    // Si tu form de limpiar tiene id en el template, mejor: <form id="form-limpiar" ...>
    const formLimpiar = document.getElementById("form-limpiar") ||
                        document.querySelector('form[action$="limpiar_sesion/"]');

    if (!formLimpiar) return;

    formLimpiar.addEventListener("submit", function () {
      try {
        // Estado del navegador
        sessionStorage.clear();
        // Si usás alguna preferencia en localStorage para el select, podés limpiarla aquí:
        // localStorage.removeItem("tipo_seleccionado");

        // UI inmediata (así el usuario ve todo vacío al instante)
        if (tipoSelect) {
          tipoSelect.value = "";
          tipoSelect.classList.remove("agua", "suelo");
        }
        if (inputArchivo) {
          inputArchivo.value = "";
        }
        if (nombreSpan) {
          nombreSpan.innerHTML = `<span class="text-muted">Ningún archivo seleccionado</span>`;
        }
        if (logArea) {
          logArea.value = "";
        }
      } catch (e) {
        console.warn("No se pudo limpiar completamente el estado local:", e);
      }
      // el submit continúa y el backend hace request.session.flush()
    });
  })();

  // === Modal de clave (si existe en esta página) ===
  (function () {
    const btnCambiar = document.getElementById("btn-cambiar-spectralon");
    const confirmarClaveBtn = document.getElementById("confirmar-clave-btn");
    const claveInput = document.getElementById("clave-input");
    const modalEl = document.getElementById("claveModal");
    const modalClave = modalEl ? new bootstrap.Modal(modalEl, { backdrop: 'static' }) : null;

    if (btnCambiar && inputSpectralon && confirmarClaveBtn && claveInput && modalClave) {
      btnCambiar.addEventListener("click", () => {
        claveInput.value = "";
        modalClave.show();
      });

      confirmarClaveBtn.addEventListener("click", () => {
        const clave = claveInput.value;
        const CLAVE_CORRECTA = "1234";
        if (clave === CLAVE_CORRECTA) {
          modalClave.hide();
          setTimeout(() => inputSpectralon.click(), 200);
        } else {
          if (typeof mostrarToast === 'function') mostrarToast("❌ Clave incorrecta.");
          else alert("❌ Clave incorrecta.");
          claveInput.value = "";
        }
      });
    }
  })();
});



