// ============================================================================
// config.js — Lógica de la vista "Configuraciones"
// ---------------------------------------------------------------------------
// Controla:
//  - Selector de tipo de configuración (agua, suelo, spectralon)
//  - Bloqueo dinámico y redirección entre vistas
//  - Edición de listas (meas_order y target_list) mediante modal Bootstrap
//  - Validación y normalización de datos JSON
// ============================================================================

console.log("✅ config.js cargado");

document.addEventListener("DOMContentLoaded", function () {
  const tipoConfig = document.getElementById("tipo-config");
  const formConfig = document.getElementById("form-config");

  // ==========================================================================
  // 🔧 Helpers UI (control del select principal)
  // ==========================================================================

  /** Guarda el último tipo seleccionado (agua/suelo) */
  function initUltimoTipo() {
    if (!tipoConfig) return;
    const v = (tipoConfig.value || "").toLowerCase();
    tipoConfig.dataset.current = ["agua", "suelo"].includes(v) ? v : "agua";
  }

  /** Aplica color temático al select */
  function actualizarEstiloConfiguracion() {
    if (!tipoConfig) return;
    tipoConfig.classList.remove("agua", "suelo", "spectralon");
    tipoConfig.classList.add((tipoConfig.value || "").toLowerCase());
  }

  /** Bloquea la opción opuesta al tipo actual */
  function bloquearOpuesta() {
    if (!tipoConfig) return;
    const v = (tipoConfig.value || "").toLowerCase();
    const aguaOpt = tipoConfig.querySelector('option[value="agua"]');
    const sueloOpt = tipoConfig.querySelector('option[value="suelo"]');
    if (aguaOpt) aguaOpt.disabled = v === "suelo";
    if (sueloOpt) sueloOpt.disabled = v === "agua";
  }

  /** Actualiza el botón Inicio del navbar con el tipo actual */
  function actualizarHomeHref() {
    const homeBtn = document.querySelector('a[title="Inicio"]');
    if (homeBtn && tipoConfig) {
      const baseTipo = (tipoConfig.dataset.current || tipoConfig.value || "").toLowerCase();
      homeBtn.href = `/?tipo=${encodeURIComponent(baseTipo)}`;
    }
  }

  // Estado inicial del select
  initUltimoTipo();
  actualizarEstiloConfiguracion();
  bloquearOpuesta();
  actualizarHomeHref();

  // Evento de cambio de tipo
  if (tipoConfig && !tipoConfig.dataset.bound) {
    tipoConfig.addEventListener("change", () => {
      const selected = (tipoConfig.value || "").toLowerCase();
      if (selected === "spectralon") {
        // Redirigir al editor TXT
        const ultimo = tipoConfig.dataset.current || "agua";
        window.location.href = `/editar_spectralon/?tipo=${encodeURIComponent(ultimo)}`;
        return;
      }
      tipoConfig.dataset.current = selected;
      actualizarEstiloConfiguracion();
      bloquearOpuesta();
      actualizarHomeHref();
      // Refresca la vista de configuraciones
      window.location.href = `/configuraciones/?tipo=${encodeURIComponent(selected)}&force_config=1`;
    });
    tipoConfig.dataset.bound = "1";
  }

  // ==========================================================================
  // 🧩 Modal Bootstrap para editar listas meas_order / target_list
  // ==========================================================================

  const modalEl = document.getElementById("editorListaModal");
  const editor = document.getElementById("editorTextarea");
  const helpEl = document.getElementById("editor-help");
  const feedback = document.getElementById("editorFeedback");
  const titleEl = document.getElementById("editorListaLabel");
  const btnAplicar = document.getElementById("btn-aplicar-lista");
  const BS = window.bootstrap;
  const modal = modalEl && BS ? new BS.Modal(modalEl, { backdrop: "static" }) : null;

  let currentField = null; // almacena qué campo se está editando

  /** Convierte texto a array de strings, tolerante a formatos */
  function parseToArrayLoose(text) {
    try {
      const parsed = JSON.parse(text);
      if (Array.isArray(parsed)) return parsed.map(String);
    } catch (_) {}
    let t = String(text || "").trim();
    if (t.startsWith("[") && t.endsWith("]")) t = t.slice(1, -1);
    return t
      .split(",")
      .map((s) => s.trim().replace(/^['"]|['"]$/g, ""))
      .filter(Boolean);
  }

  /** Muestra ayuda contextual según el campo */
  function setHelp(field) {
    if (!helpEl) return;
    helpEl.innerHTML =
      field === "meas_order"
        ? `<strong>Orden de medición</strong> (temporal).<br>
           Valores permitidos: <code>spectralon</code>, <code>target</code>, <code>cielo</code>.<br>
           Podés escribir coma-separado o pegar JSON.`
        : `<strong>Lista de targets</strong> (temporal). Ejemplo: <code>M1, M2, M3</code> o JSON equivalente.`;
  }

  /** Abre el modal de edición */
  function openEditor(field) {
    const inputEl = document.getElementById(field);
    if (!inputEl || !modal || !editor) return;
    currentField = field;
    setHelp(field);
    titleEl && (titleEl.textContent = `Editar ${field}`);
    editor.value = JSON.stringify(parseToArrayLoose(inputEl.value), null, 2);
    feedback.textContent = "";
    feedback.className = "mt-2 small";
    modal.show();
  }

  /** Valida y aplica cambios del modal */
  function applyEditor() {
    const arr = parseToArrayLoose(editor.value);
    if (!arr.length) {
      feedback.className = "mt-2 small text-danger";
      feedback.textContent = "Ingresá al menos un valor (coma-separado o JSON).";
      return;
    }

    if (currentField === "meas_order") {
      const ok = arr.every((v) => ["spectralon", "target", "cielo"].includes(v.toLowerCase()));
      if (!ok) {
        feedback.className = "mt-2 small text-danger";
        feedback.textContent = 'Solo se permiten valores: "spectralon", "target", "cielo".';
        return;
      }
    }

    const inputEl = document.getElementById(currentField);
    if (inputEl) inputEl.value = JSON.stringify(arr);
    modal?.hide();
  }

  // Abrir modal desde botones "Editar"
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".btn-edit-list");
    if (btn) openEditor(btn.dataset.target);
  });

  btnAplicar?.addEventListener("click", applyEditor);

  // Atajo: Ctrl/Cmd + Enter aplica cambios
  editor?.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      applyEditor();
    }
  });

  // ==========================================================================
  // 💾 Normalización antes de enviar formulario
  // ==========================================================================

  if (formConfig && !formConfig.dataset.bound) {
    formConfig.addEventListener("submit", () => {
      ["meas_order", "target_list"].forEach((id) => {
        const el = document.getElementById(id);
        if (!el) return;
        try {
          const parsed = JSON.parse(el.value);
          if (Array.isArray(parsed)) {
            el.value = JSON.stringify(parsed.map(String));
            return;
          }
        } catch (_) {}
        el.value = JSON.stringify(parseToArrayLoose(el.value));
      });
    });
    formConfig.dataset.bound = "1";
  }
});










