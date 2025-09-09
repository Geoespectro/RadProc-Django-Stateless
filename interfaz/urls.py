from django.urls import path
from . import views

urlpatterns = [
    path('', views.vista_principal, name='inicio'),
    path('procesar/', views.procesar, name='procesar'),

    path('configuraciones/', views.vista_configuraciones, name='configuraciones'),
    path('guardar_config/', views.guardar_config, name='guardar_config'),

    path('editar_spectralon/', views.editar_spectralon, name='editar_spectralon'),
    path('guardar_spectralon/', views.guardar_spectralon, name='guardar_spectralon'),
    path('cambiar_spectralon/', views.cambiar_spectralon, name='cambiar_spectralon'),

    path('manual/', views.manual_usuario, name='manual_usuario'),
    path('limpiar_sesion/', views.limpiar_sesion, name='limpiar_sesion'),
    path('descargar_resultados/', views.descargar_resultados, name='descargar_resultados'),
]


