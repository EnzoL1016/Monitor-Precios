from rest_framework import serializers
from .models import Product, PriceHistory

class PriceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceHistory
        fields = ['captured_price', 'timestamp']

class ProductSerializer(serializers.ModelSerializer):
    # Esto permite que el frontend reciba la lista de precios anteriores
    history = PriceHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'url', 'target_price',
            'current_price', 'is_available', 'history', 'created_at'
        ]