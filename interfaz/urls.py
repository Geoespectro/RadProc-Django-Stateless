# interfaz/urls.py — listo para STATeless

from django.urls import path
from . import views

urlpatterns = [
    # === Página principal ===
    path('', views.vista_principal, name='inicio'),

    # === Procesamiento STATeless (1 paso) ===
    path('procesar/', views.procesar, name='procesar'),

    # === Configuración (UI existente; overrides en sesión) ===
    path('configuraciones/', views.vista_configuraciones, name='configuraciones'),
    path('guardar_config/', views.guardar_config, name='guardar_config'),

    # === Compatibilidad con tu UI actual ===
    # Subir ZIP ahora procesa y devuelve ZIP directo (STATeless)
    path('subir_zip/', views.subir_zip, name='subir_zip'),
    # Mantiene endpoint pero informa que el flujo es directo
    path('procesar_datos/', views.procesar_datos, name='procesar_datos'),
    # Ya no hay persistencia; informa al usuario
    path('descargar_resultados/', views.descargar_resultados, name='descargar_resultados'),

    # === Archivos Spectralon (UI de compatibilidad en sesión) ===
    path('editar_spectralon/', views.editar_spectralon, name='editar_spectralon'),
    path('guardar_spectralon/', views.guardar_spectralon, name='guardar_spectralon'),
    path('cambiar_spectralon/', views.cambiar_spectralon, name='cambiar_spectralon'),

    # === Extras ===
    path('manual/', views.manual_usuario, name='manual_usuario'),
    path('limpiar_sesion/', views.limpiar_sesion, name='limpiar_sesion'),
    path('clave_spectralon/', views.clave_spectralon, name='clave_spectralon'),
]

