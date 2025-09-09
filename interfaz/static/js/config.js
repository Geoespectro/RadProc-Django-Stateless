// static/js/config.js — STATELESS y sin sorpresas al volver
// - Aplica estilo (agua/suelo/spectralon) al <select>
// - Bloquea la opción opuesta
// - El botón "Inicio" conserva el tipo (agua/suelo)
// - AL IR A SPECTRALON: pasa siempre el último tipo no-spectralon en ?tipo=...

console.log("✅ config.js cargado");

document.addEventListener("DOMContentLoaded", function () {
  const tipoConfig = document.getElementById("tipo-config");
  if (!tipoConfig) return;

  // Guarda el último tipo NO-spectralon (para ida y vuelta al editor)
  function initUltimoTipo() {
    const v = (tipoConfig.value || "").toLowerCase();
    // Sólo guardamos si es agua/suelo
    if (v === "agua" || v === "suelo") {
      tipoConfig.dataset.current = v;
    } else if (!tipoConfig.dataset.current) {
      // Fallback razonable si llegara "spectralon" (no debería por redirección del server)
      tipoConfig.dataset.current = "agua";
    }
  }

  function actualizarEstiloConfiguracion() {
    tipoConfig.classList.remove("agua", "suelo", "spectralon");
    switch ((tipoConfig.value || "").toLowerCase()) {
      case "agua":       tipoConfig.classList.add("agua"); break;
      case "suelo":      tipoConfig.classList.add("suelo"); break;
      case "spectralon": tipoConfig.classList.add("spectralon"); break;
    }
  }

  function bloquearOpuesta() {
    const v = (tipoConfig.value || "").toLowerCase();
    const aguaOpt  = tipoConfig.querySelector('option[value="agua"]');
    const sueloOpt = tipoConfig.querySelector('option[value="suelo"]');
    if (aguaOpt)  aguaOpt.disabled  = (v === "suelo");
    if (sueloOpt) sueloOpt.disabled = (v === "agua");
  }

  function actualizarHomeHref() {
    const homeBtn = document.querySelector('a[title="Inicio"]');
    if (homeBtn) {
      // Usamos SIEMPRE el último no-spectralon para volver a Inicio
      const baseTipo = (tipoConfig.dataset.current || (tipoConfig.value || "")).toLowerCase();
      homeBtn.setAttribute("href", "/?tipo=" + encodeURIComponent(baseTipo));
    }
  }

  // Estado inicial
  initUltimoTipo();
  actualizarEstiloConfiguracion();
  bloquearOpuesta();
  actualizarHomeHref();

  if (!tipoConfig.dataset.bound) {
    tipoConfig.addEventListener("change", function () {
      const selected = (tipoConfig.value || "").toLowerCase();

      // Si eligen Spectralon, navegamos al editor con el ÚLTIMO tipo no-spectralon
      if (selected === "spectralon") {
        const ultimo = tipoConfig.dataset.current || "agua";
        window.location.href = "/editar_spectralon/?tipo=" + encodeURIComponent(ultimo);
        return;
      }

      // Si eligen agua/suelo, actualizamos el "último tipo" y navegamos a su config
      tipoConfig.dataset.current = selected;

      actualizarEstiloConfiguracion();
      bloquearOpuesta();
      actualizarHomeHref();

      window.location.href = `/configuraciones/?tipo=${encodeURIComponent(selected)}&force_config=1`;
    });

    tipoConfig.dataset.bound = "1";
  }
});










