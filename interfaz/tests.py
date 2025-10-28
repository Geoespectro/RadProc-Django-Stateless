# =============================================================================
# interfaz/tests.py
# -----------------------------------------------------------------------------
# Pruebas mínimas de salud de la interfaz RadProc (modo stateless)
# Verifica que las rutas principales respondan correctamente.
# =============================================================================

from django.test import TestCase
from django.urls import reverse

class RadProcInterfaceTests(TestCase):
    """Pruebas básicas del módulo de interfaz web."""

    def test_index_view_status(self):
        """La página principal debe responder con código 200."""
        response = self.client.get(reverse("inicio"))

        self.assertEqual(response.status_code, 200)

    def test_configuraciones_view_status(self):
        """La página de configuraciones debe responder correctamente."""
        response = self.client.get(reverse("configuraciones"))
        self.assertEqual(response.status_code, 200)
