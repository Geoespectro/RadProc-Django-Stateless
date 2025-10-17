// ============================================================================
// sound.js — Control del sonido de finalización de procesamiento
// ---------------------------------------------------------------------------
// Controla:
//   - Desbloqueo de reproducción automática (por interacción del usuario)
//   - Función global playDoneSound() para reproducir el audio “done-sound”
// ---------------------------------------------------------------------------
// Compatible con navegadores que requieren interacción manual antes de
// permitir la reproducción de sonidos (iOS, Chrome, etc.).
// ============================================================================

(function () {

  /* ==========================================================================
     1) REFERENCIAS DOM Y ESTADO INTERNO
  ========================================================================== */
  const audio = document.getElementById("done-sound");
  if (!audio) return; // Si no hay audio, se sale silenciosamente

  let unlocked = false; // indica si ya se “desbloqueó” la reproducción


  /* ==========================================================================
     2) FUNCIÓN DE DESBLOQUEO
     Desbloquea la reproducción automática tras la primera interacción
  ========================================================================== */
  function tryUnlock() {
    if (unlocked) return;

    // Intento de desbloqueo tras clic/tecla/toque
    audio.play().then(() => {
      audio.pause();
      audio.currentTime = 0;
      unlocked = true;

      // Una vez desbloqueado, se quitan los listeners
      window.removeEventListener("click", tryUnlock, true);
      window.removeEventListener("keydown", tryUnlock, true);
      window.removeEventListener("touchstart", tryUnlock, true);
    }).catch(() => {
      // Si falla (ej. iOS antes de interacción), reintenta en siguiente evento
    });
  }

  // Listeners para las primeras interacciones del usuario
  window.addEventListener("click", tryUnlock, true);
  window.addEventListener("keydown", tryUnlock, true);
  window.addEventListener("touchstart", tryUnlock, true);


  /* ==========================================================================
     3) API GLOBAL — Reproducción del sonido de finalización
  ========================================================================== */
  window.playDoneSound = function () {
    if (!unlocked) return; // respeta las políticas de autoplay
    try {
      audio.currentTime = 0;
      audio.play();
    } catch (_) {
      // Evita romper el flujo si el audio falla
    }
  };
})();

