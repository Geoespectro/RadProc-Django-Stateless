// config.js — STATELESS + modal simple (solo botón "Editar")
console.log("✅ config.js cargado");

document.addEventListener("DOMContentLoaded", function () {
  const tipoConfig = document.getElementById("tipo-config");
  const formConfig = document.getElementById("form-config");

  // ===== helpers UI de tipo =====
  function initUltimoTipo() {
    if (!tipoConfig) return;
    const v = (tipoConfig.value || "").toLowerCase();
    if (v === "agua" || v === "suelo") {
      tipoConfig.dataset.current = v;
    } else if (!tipoConfig.dataset.current) {
      tipoConfig.dataset.current = "agua";
    }
  }
  function actualizarEstiloConfiguracion() {
    if (!tipoConfig) return;
    tipoConfig.classList.remove("agua","suelo","spectralon");
    switch ((tipoConfig.value || "").toLowerCase()) {
      case "agua": tipoConfig.classList.add("agua"); break;
      case "suelo": tipoConfig.classList.add("suelo"); break;
      case "spectralon": tipoConfig.classList.add("spectralon"); break;
    }
  }
  function bloquearOpuesta() {
    if (!tipoConfig) return;
    const v = (tipoConfig.value || "").toLowerCase();
    const aguaOpt  = tipoConfig.querySelector('option[value="agua"]');
    const sueloOpt = tipoConfig.querySelector('option[value="suelo"]');
    if (aguaOpt)  aguaOpt.disabled  = (v === "suelo");
    if (sueloOpt) sueloOpt.disabled = (v === "agua");
  }
  function actualizarHomeHref() {
    const homeBtn = document.querySelector('a[title="Inicio"]');
    if (homeBtn && tipoConfig) {
      const baseTipo = (tipoConfig.dataset.current || (tipoConfig.value || "")).toLowerCase();
      homeBtn.setAttribute("href", "/?tipo=" + encodeURIComponent(baseTipo));
    }
  }

  initUltimoTipo(); actualizarEstiloConfiguracion(); bloquearOpuesta(); actualizarHomeHref();

  if (tipoConfig && !tipoConfig.dataset.bound) {
    tipoConfig.addEventListener("change", function () {
      const selected = (tipoConfig.value || "").toLowerCase();
      if (selected === "spectralon") {
        const ultimo = tipoConfig.dataset.current || "agua";
        window.location.href = "/editar_spectralon/?tipo=" + encodeURIComponent(ultimo);
        return;
      }
      tipoConfig.dataset.current = selected;
      actualizarEstiloConfiguracion(); bloquearOpuesta(); actualizarHomeHref();
      window.location.href = `/configuraciones/?tipo=${encodeURIComponent(selected)}&force_config=1`;
    });
    tipoConfig.dataset.bound = "1";
  }

  // ===== Modal para listas (meas_order, target_list) =====
  const modalEl = document.getElementById("editorListaModal");
  const editor  = document.getElementById("editorTextarea");
  const helpEl  = document.getElementById("editor-help");
  const feedback = document.getElementById("editorFeedback");
  const titleEl = document.getElementById("editorListaLabel");
  const btnAplicar = document.getElementById("btn-aplicar-lista");
  const BS = window.bootstrap;
  const modal = (modalEl && BS) ? new BS.Modal(modalEl, { backdrop:'static' }) : null;

  let currentField = null; // "meas_order" | "target_list"

  function parseToArrayLoose(text) {
    // 1) intentar JSON
    try {
      const parsed = JSON.parse(text);
      if (Array.isArray(parsed)) return parsed.map(String);
    } catch(e) {}
    // 2) coma-separado (permite [] y comillas sueltas)
    let t = String(text || "").trim();
    if (t.startsWith("[") && t.endsWith("]")) t = t.slice(1, -1);
    const parts = t.split(",").map(s => s.trim()).filter(Boolean);
    return parts.map(s => s.replace(/^['"]|['"]$/g, ""));
  }

  function setHelp(field) {
    if (!helpEl) return;
    if (field === "meas_order") {
      helpEl.innerHTML = `
        <strong>Orden de medición</strong> (temporal).
        Valores permitidos: <code>spectralon</code>, <code>target</code>, <code>cielo</code>.<br>
        Podés escribir <em>coma-separado</em> (ej.: <code>spectralon, target, cielo</code>)
        o pegar un JSON (ej.: <code>["spectralon","target"]</code>).
      `;
    } else {
      helpEl.innerHTML = `
        <strong>Lista de targets</strong> (temporal).
        Ejemplo: <code>M1, M2, M3</code> o JSON <code>["M1","M2","M3"]</code>.
      `;
    }
  }

  function openEditor(field) {
    const inputEl = document.getElementById(field);
    if (!inputEl || !modal || !editor) return;
    currentField = field;
    setHelp(field);
    if (titleEl) titleEl.textContent = `Editar ${field}`;
    // mostrar en formato legible
    editor.value = JSON.stringify(parseToArrayLoose(inputEl.value), null, 2);
    feedback.textContent = "";
    feedback.className = "mt-2 small";
    modal.show();
  }

  function applyEditor() {
    const arr = parseToArrayLoose(editor.value);
    if (!arr.length) {
      feedback.className = "mt-2 small text-danger";
      feedback.textContent = "Ingresá al menos un valor (coma-separado o JSON).";
      return;
    }
    // validación domain simple para meas_order
    if (currentField === "meas_order") {
      const ok = arr.every(v => ["spectralon","target","cielo"].includes(v.toLowerCase()));
      if (!ok) {
        feedback.className = "mt-2 small text-danger";
        feedback.textContent = 'Solo se permiten valores: "spectralon", "target", "cielo".';
        return;
      }
    }
    const inputEl = document.getElementById(currentField);
    if (inputEl) inputEl.value = JSON.stringify(arr);
    modal && modal.hide();
  }

  // Botones "Editar"
  document.addEventListener("click", function (e) {
    const btn = e.target.closest(".btn-edit-list");
    if (!btn) return;
    openEditor(btn.getAttribute("data-target"));
  });

  if (btnAplicar) btnAplicar.addEventListener("click", applyEditor);

  // Ctrl/Cmd+Enter para aplicar
  if (editor) {
    editor.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        applyEditor();
      }
    });
  }

  // Normalización al enviar (garantiza JSON válido)
  if (formConfig && !formConfig.dataset.bound) {
    formConfig.addEventListener("submit", function () {
      ["meas_order","target_list"].forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        try {
          const parsed = JSON.parse(el.value);
          if (Array.isArray(parsed)) {
            el.value = JSON.stringify(parsed.map(String));
            return;
          }
        } catch(e){}
        el.value = JSON.stringify(parseToArrayLoose(el.value));
      });
    });
    formConfig.dataset.bound = "1";
  }
});










