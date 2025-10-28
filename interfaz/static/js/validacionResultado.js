// =============================================================================
// interfaz/static/js/validacionResultado.js
// -----------------------------------------------------------------------------
// Módulo de control del modal de advertencia ante configuraciones inválidas
// o resultados anómalos en el procesamiento.
// 
// Estructura general:
//   1) Creación dinámica del DOM y estilos del modal
//   2) Renderizado de vistas (home y detalles técnicos)
//   3) API pública: mostrarModalAdvertencia(), manejarResultadoValidacion()
// =============================================================================

(function () {

  // ===========================================================================
  // 1️⃣ CREACIÓN DEL MODAL Y ESTILOS
  // ---------------------------------------------------------------------------
  // Genera dinámicamente el DOM y el bloque de estilos del modal.
  // Se asegura de que solo exista una instancia activa.
  // ===========================================================================
  function ensureModalDOM() {
    if (document.getElementById('rp-modal-overlay')) return;

    const style = document.createElement('style');
    style.id = 'rp-modal-style';
    style.textContent = `
      #rp-modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.45);
        display: none; align-items: center; justify-content: center; z-index: 9999; }
      #rp-modal { width: min(720px, 92vw); background: #fff; color: #111; border-radius: 14px;
        box-shadow: 0 20px 60px rgba(0,0,0,.35); overflow: hidden;
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif; }
      #rp-modal header { background: #ffe8cc; padding: 14px 18px; border-bottom: 1px solid #ffd5a3;
        display:flex; align-items:center; justify-content:space-between; }
      #rp-modal header h3 { margin: 0; font-size: 1.15rem; }
      #rp-modal .rp-close { background: transparent; border: none; font-size: 1.3rem;
        cursor: pointer; padding: 4px 8px; line-height: 1; }
      #rp-modal .rp-body { padding: 18px; font-size: 1rem; max-height:70vh; overflow-y:auto; }
      #rp-modal footer { display:flex; justify-content:flex-end; gap:10px; padding: 12px 18px;
        background:#f7f7f7; border-top: 1px solid #eee; }
      #rp-modal .rp-btn { border: 1px solid #ccc; padding: 8px 14px; border-radius: 8px; cursor:pointer;
        background:#fff; transition: all .2s ease; }
      #rp-modal .rp-btn.primary { background:#0d6efd; border-color:#0d6efd; color:#fff; }
      #rp-modal .rp-btn:hover { background:#e9ecef; }
      #rp-modal .rp-btn.primary:hover { background:#0b5ed7; }

      .rp-detalle h4, .rp-detalle h5 { margin-top: 0.8em; color:#333; }
      .rp-detalle pre { background:#f6f6f6; border:1px solid #ddd; border-radius:6px;
        padding:8px 10px; font-size:0.9rem; overflow-x:auto; }
      .rp-detalle code { color:#0d6efd; }
    `;
    document.head.appendChild(style);

    const overlay = document.createElement('div');
    overlay.id = 'rp-modal-overlay';
    overlay.innerHTML = `
      <div id="rp-modal" role="dialog" aria-modal="true" aria-labelledby="rp-modal-title">
        <header>
          <h3 id="rp-modal-title">Aviso</h3>
          <button class="rp-close" aria-label="Cerrar">&times;</button>
        </header>
        <div class="rp-body"><p></p></div>
        <footer></footer>
      </div>
    `;
    document.body.appendChild(overlay);

    // Cierre por clic en overlay o botón de cierre
    const close = () => overlay.style.display = 'none';
    overlay.addEventListener('click', (e) => { if (e.target.id === 'rp-modal-overlay') close(); });
    overlay.querySelector('.rp-close').addEventListener('click', close);
  }


  // ===========================================================================
  // 2️⃣ RENDERIZADO DE CONTENIDO DEL MODAL
  // ---------------------------------------------------------------------------
  // Incluye dos modos:
  //   - Home: mensaje principal de advertencia.
  //   - Detalles técnicos: guía educativa para revisar configuración.
  // ===========================================================================
  function renderDetalles() {
    const overlay = document.getElementById('rp-modal-overlay');
    const titleEl = overlay.querySelector('#rp-modal-title');
    const bodyEl  = overlay.querySelector('.rp-body');
    const footerEl = overlay.querySelector('footer');

    titleEl.textContent = "Detalles técnicos de la configuración";
    bodyEl.innerHTML = `
      <div id="detalle-configuracion" class="rp-detalle">
        <h4>Cómo revisar tu configuración</h4>
        <p>
          Este mensaje aparece cuando la <b>configuración seleccionada</b> no coincide con la
          <b>estructura real del conjunto de datos</b> que subiste.
          El procesamiento se completó correctamente, pero las mediciones no pudieron
          agruparse de forma coherente, por lo que el paquete generado solo contiene
          información general (<code>metadata.json</code>).
        </p>

        <h5>1️⃣ Verifica el valor de <code>spectrum</code></h5>
        <p>Indica cuántos espectros individuales componen una medición completa.</p>
        <pre><code>spectrum = 10
meas_order = ["spectralon", "target"]</code></pre>

        <h5>2️⃣ Revisa el orden de medición (<code>meas_order</code>)</h5>
        <p>Define si se midió primero el <b>Spectralon</b> o el <b>Target</b>.
        Un orden incorrecto puede alterar la interpretación de los resultados.</p>

        <h5>3️⃣ Comprueba la lista de objetivos (<code>target_list</code>)</h5>
        <p>Determina los nombres asignados a cada medición y su correspondencia
        dentro de los archivos cargados. Verifica que coincidan con los datos de campo.</p>

        <h5>✅ Consejo final</h5>
        <p>
          Antes de volver a procesar, asegurate de que los parámetros utilizados correspondan
          al instrumento, protocolo de medición y condiciones de campaña.
          Si tenés dudas, consultá el <b>manual de usuario</b> o las especificaciones técnicas.
        </p>
      </div>
    `;

    footerEl.innerHTML = `<button class="rp-btn primary" id="rp-cerrar-detalle">Cerrar</button>`;
    footerEl.querySelector('#rp-cerrar-detalle').addEventListener('click', () => {
      overlay.style.display = 'none';
    });
  }


  function renderHome(titulo, htmlMsg) {
    const overlay = document.getElementById('rp-modal-overlay');
    const titleEl = overlay.querySelector('#rp-modal-title');
    const bodyEl  = overlay.querySelector('.rp-body');
    const footerEl = overlay.querySelector('footer');

    titleEl.textContent = titulo || 'Aviso';
    bodyEl.innerHTML = `<p>${htmlMsg || 'Ocurrió una condición a revisar.'}</p>`;

    // Footer con acciones disponibles
    footerEl.innerHTML = `
      <button class="rp-btn" id="rp-modal-detalles">Ver detalles técnicos</button>
      <button class="rp-btn primary" id="rp-modal-aceptar">Entendido</button>
    `;

    // Bind de botones (siempre sobre el DOM recién pintado)
    footerEl.querySelector('#rp-modal-aceptar').addEventListener('click', () => {
      overlay.style.display = 'none';
    });
    footerEl.querySelector('#rp-modal-detalles').addEventListener('click', renderDetalles);

    overlay.style.display = 'flex';
  }


  // ===========================================================================
  // 3️⃣ API PÚBLICA DEL MÓDULO
  // ---------------------------------------------------------------------------
  // Exposición global de funciones accesibles desde index.js y otros scripts.
  // ===========================================================================
  function mostrarModalAdvertencia(titulo, htmlMsg) {
    ensureModalDOM();
    renderHome(titulo, htmlMsg);
  }

  function verificarYMostrarAviso(resultado) {
    if (resultado && resultado.soloMetaDatos) {
      mostrarModalAdvertencia(
        "Parámetros fuera de rango",
        "Se detectó que el paquete descargado contiene solo <b>metadata</b>. " +
        "Esto suele ocurrir cuando la configuración (por ejemplo, <code>spectrum</code> o <code>meas_order</code>) " +
        "no coincide con el conjunto de datos subido. Revisa la configuración y vuelve a intentar."
      );
    }
  }

  function manejarResultadoValidacion({ mensaje }) {
    try {
      const limpio = String(mensaje || "").trim();
      if (!limpio) return;
      mostrarModalAdvertencia(
        "Configuración incompatible con los datos",
        limpio.replace(/\n/g, "<br>")
      );
    } catch (err) {
      console.warn("No se pudo mostrar el modal de validación:", err);
    }
  }

  // Registrar funciones globales
  window.manejarResultadoValidacion = manejarResultadoValidacion;
  window.mostrarModalAdvertencia = mostrarModalAdvertencia;
  window.verificarYMostrarAviso = verificarYMostrarAviso;

})();

// =============================================================================
// FIN DEL MÓDULO
// -----------------------------------------------------------------------------
// Este script se ejecuta de forma autónoma y provee las funciones necesarias
// para mostrar mensajes y guías al usuario cuando la validación detecta
// inconsistencias entre la configuración y los datos cargados.
// =============================================================================






