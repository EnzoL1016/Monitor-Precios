from django.db import models
from django.contrib.auth.models import User

class Product(models.Model):
    """
    Representa un producto que un usuario específico quiere monitorear.
    Incluye soporte para Soft Delete (papelera).
    """
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='products',
        verbose_name="Usuario"
    )
    name = models.CharField(max_length=255, blank=True, verbose_name="Nombre del Producto")
    url = models.URLField(max_length=1000, verbose_name="URL del Producto")
    target_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name="Precio Objetivo"
    )
    current_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True, 
        verbose_name="Precio Actual"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    
    # Campo para Soft Delete: Si tiene fecha, está en la papelera.
    deleted_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name="Fecha de eliminación"
    )

    # Disponibilidad: False si el producto está sin stock o no disponible
    is_available = models.BooleanField(default=True, verbose_name="Disponible")

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    @property
    def is_deleted(self):
        """Retorna True si el producto está en la papelera."""
        return self.deleted_at is not None


class PriceHistory(models.Model):
    """
    Registra cada captura de precio realizada por el scraper.
    """
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='history'
    )
    captured_price = models.DecimalField(max_digits=12, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historial de Precio"
        verbose_name_plural = "Historiales de Precios"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.product.name} - ${self.captured_price} en {self.timestamp}"