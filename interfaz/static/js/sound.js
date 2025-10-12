// interfaz/static/js/sound.js
(function () {
  // Busca el <audio> por id. Si no existe, sale silenciosamente.
  const audio = document.getElementById('done-sound');
  if (!audio) return;

  let unlocked = false;

  function tryUnlock() {
    if (unlocked) return;
    // Intento de “desbloqueo” tras una interacción del usuario
    audio.play().then(() => {
      audio.pause();
      audio.currentTime = 0;
      unlocked = true;
      window.removeEventListener('click', tryUnlock, true);
      window.removeEventListener('keydown', tryUnlock, true);
      window.removeEventListener('touchstart', tryUnlock, true);
    }).catch(() => {
      // Si falla (p. ej. iOS antes de interacción), probaremos en el próximo evento
    });
  }

  window.addEventListener('click', tryUnlock, true);
  window.addEventListener('keydown', tryUnlock, true);
  window.addEventListener('touchstart', tryUnlock, true);

  // API global para reproducir el sonido cuando termine el procesamiento
  window.playDoneSound = function () {
    if (!unlocked) return; // respeta políticas de autoplay
    try {
      audio.currentTime = 0;
      audio.play();
    } catch (_) {
      // Evita romper el flujo si falla el audio
    }
  };
})();
