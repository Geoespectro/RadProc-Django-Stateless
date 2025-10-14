// validacionResultado.js
(function () {
  // ====== Modal simple “sin dependencias” ======
  function ensureModalDOM() {
    if (document.getElementById('rp-modal-overlay')) return;

    const style = document.createElement('style');
    style.id = 'rp-modal-style';
    style.textContent = `
      #rp-modal-overlay {
        position: fixed; inset: 0; background: rgba(0,0,0,.45);
        display: none; align-items: center; justify-content: center;
        z-index: 9999;
      }
      #rp-modal {
        width: min(720px, 92vw);
        background: #fff; color: #111;
        border-radius: 14px; box-shadow: 0 20px 60px rgba(0,0,0,.35);
        overflow: hidden; font-family: system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
      }
      #rp-modal header {
        background: #ffe8cc; padding: 14px 18px; border-bottom: 1px solid #ffd5a3;
        display:flex; align-items:center; justify-content:space-between;
      }
      #rp-modal header h3 { margin: 0; font-size: 1.15rem; }
      #rp-modal .rp-close {
        background: transparent; border: none; font-size: 1.3rem; cursor: pointer;
        padding: 4px 8px; line-height: 1;
      }
      #rp-modal .rp-body { padding: 18px; font-size: 1rem; max-height:70vh; overflow-y:auto; }
      #rp-modal .rp-body p { margin: 0 0 10px 0; }
      #rp-modal footer {
        display:flex; justify-content:flex-end; gap:10px; padding: 12px 18px; background:#f7f7f7;
        border-top: 1px solid #eee;
      }
      #rp-modal .rp-btn {
        border: 1px solid #ccc; padding: 8px 14px; border-radius: 8px; cursor:pointer; background:#fff;
      }
      #rp-modal .rp-btn.primary { background:#0d6efd; border-color:#0d6efd; color:#fff; }

      /* Estilos del detalle */
      .rp-detalle h4, .rp-detalle h5 { margin-top: 0.8em; color:#333; }
      .rp-detalle pre {
        background:#f6f6f6; border:1px solid #ddd; border-radius:6px;
        padding:8px 10px; font-size:0.9rem; overflow-x:auto;
      }
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
        <footer>
          <button class="rp-btn" id="rp-modal-detalles">Ver detalles técnicos</button>
          <button class="rp-btn primary" id="rp-modal-aceptar">Entendido</button>
        </footer>
      </div>
    `;
    document.body.appendChild(overlay);

    const close = () => overlay.style.display = 'none';
    const resetBody = () => {
      const bodyEl = overlay.querySelector('.rp-body');
      bodyEl.innerHTML = `<p>Ocurrió una condición a revisar.</p>`;
      const titleEl = overlay.querySelector('#rp-modal-title');
      titleEl.textContent = "Aviso";
    };

    overlay.addEventListener('click', (e) => { if (e.target.id === 'rp-modal-overlay') close(); });
    overlay.querySelector('.rp-close').addEventListener('click', close);
    overlay.querySelector('#rp-modal-aceptar').addEventListener('click', close);

    // === Acción del botón "Ver detalles técnicos" ===
    overlay.querySelector('#rp-modal-detalles').addEventListener('click', () => {
      const bodyEl = overlay.querySelector('.rp-body');
      const titleEl = overlay.querySelector('#rp-modal-title');
      titleEl.textContent = "Detalles técnicos de la configuración";

      bodyEl.innerHTML = `
        <div id="detalle-configuracion" class="rp-detalle">
          <h4>Cómo revisar tu configuración</h4>
          <p>
            Este mensaje aparece cuando la <b>configuración seleccionada</b> no coincide con la
            <b>estructura real del conjunto de datos</b> que subiste.
            El procesamiento se ejecutó, pero no se pudieron agrupar correctamente las mediciones,
            por eso el paquete solo contiene información general (<code>metadata.json</code>).
          </p>

          <h5>1️⃣ Verifica el valor de <code>spectrum</code></h5>
          <p>
            El parámetro <b>spectrum</b> indica cuántos espectros individuales corresponden a una
            sola medición. Si elegís un número incorrecto, el sistema no podrá asociar bien los
            archivos de tu set.
          </p>
          <p>
            <b>Ejemplo:</b><br>
            Si tu campaña tiene 320 archivos y cada medición incluye 10 espectros de
            <i>Spectralon</i> y 10 de <i>Target</i>, entonces debes usar:
          </p>
          <pre><code>spectrum = 10
meas_order = ["spectralon", "target"]</code></pre>
          <p>
            En este caso el total de archivos se calcula como:<br>
            <code>total = spectrum × cantidad_de_tipos × cantidad_de_mediciones</code><br>
            <i>(Ejemplo: 10 × 2 × 16 = 320 archivos)</i>
          </p>

          <h5>2️⃣ Revisa el orden de medición (<code>meas_order</code>)</h5>
          <p>
            Define si primero se midió el <b>Spectralon</b> o el <b>Target</b> en cada bloque.
            Si el orden no coincide con tus datos, los resultados pueden verse alterados.
          </p>
          <p>Normalmente se utiliza:</p>
          <pre><code>meas_order = ["spectralon", "target"]</code></pre>

          <h5>3️⃣ Comprueba tu lista de objetivos (<code>target_list</code>)</h5>
          <p>
            Este parámetro solo afecta los nombres de los resultados. No causa errores, pero te
            ayuda a identificar correctamente cada medición:
          </p>
          <pre><code>target_list = ["hoja", "suelo", "agua"]</code></pre>

          <h5>✅ Consejo final</h5>
          <p>
            Si no estás seguro de los valores adecuados, utiliza la <b>configuración por defecto</b>
            y verifica que tu conjunto de datos provenga de una campaña estructurada de la misma forma.
          </p>
          <p>
            Si el mensaje vuelve a aparecer, revisa la cantidad de archivos en tu ZIP y compara con la
            fórmula anterior. Asegúrate de que el número total sea múltiplo de
            <code>spectrum × cantidad de tipos definidos</code>.
          </p>
          <div style="text-align:right; margin-top:1rem;">
            <button class="rp-btn primary" id="rp-volver">Volver</button>
          </div>
        </div>
      `;

      overlay.querySelector('#rp-volver').addEventListener('click', () => {
        resetBody();
        close();
      });
    });
  }

  // ====== Función principal para mostrar el modal ======
  function mostrarModalAdvertencia(titulo, htmlMsg) {
    ensureModalDOM();
    const overlay = document.getElementById('rp-modal-overlay');
    const titleEl = overlay.querySelector('#rp-modal-title');
    const bodyEl  = overlay.querySelector('.rp-body');

    titleEl.textContent = titulo || 'Aviso';
    bodyEl.innerHTML = `<p>${htmlMsg || 'Ocurrió una condición a revisar.'}</p>`;
    overlay.style.display = 'flex';
  }

  // ====== Compatibilidad con función previa ======
  function verificarYMostrarAviso(resultado) {
    if (resultado && resultado.soloMetaDatos) {
      mostrarModalAdvertencia(
        "Parámetros fuera de rango",
        "Se detectó que el paquete descargado contiene solo <b>metadata</b>. " +
        "Esto suele ocurrir cuando la configuración (p. ej., <code>spectrum</code>) " +
        "no es compatible con el set de datos subido. Revisa la configuración y vuelve a intentar."
      );
    }
  }

  // expone en global
  window.mostrarModalAdvertencia = mostrarModalAdvertencia;
  window.verificarYMostrarAviso = verificarYMostrarAviso;
})();





