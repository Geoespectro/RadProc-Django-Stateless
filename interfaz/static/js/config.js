// ✅ Mostrar en consola que el JS fue cargado (opcional)
console.log("✅ config.js cargado");

// Obtener el <select> de tipo de configuración
const tipoConfig = document.getElementById("tipo-config");

function actualizarEstiloConfiguracion() {
  if (!tipoConfig) return;

  // Limpiar clases previas
  tipoConfig.classList.remove("agua", "suelo", "spectralon");

  // ✅ Aplicar color según valor actual (aunque no se haya cambiado aún)
  switch (tipoConfig.value) {
    case "agua":
      tipoConfig.classList.add("agua");
      break;
    case "suelo":
      tipoConfig.classList.add("suelo");
      break;
    case "spectralon":
      tipoConfig.classList.add("spectralon");
      break;
  }
}

// ✅ Aplicar el color al iniciar
actualizarEstiloConfiguracion();

// ✅ Detectar cambios y redirigir
if (tipoConfig) {
  tipoConfig.addEventListener("change", function () {
    const selected = tipoConfig.value;

    if (selected === "spectralon") {
      window.location.href = "/editar_spectralon/";
    } else {
      window.location.href = `/configuraciones/?tipo=${selected}&force_config=1`;
    }
  });
}







