from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet

# Usamos un router para manejar automáticamente las rutas de list, create, retrieve, update, delete
router = DefaultRouter()
router.register(r'items', ProductViewSet, basename='product')

urlpatterns = [
    path('', include(router.urls)),
]