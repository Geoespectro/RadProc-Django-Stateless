from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Admin de Django
    path('admin/', admin.site.urls),

    # App principal: interfaz
    path('', include('interfaz.urls')),
]
