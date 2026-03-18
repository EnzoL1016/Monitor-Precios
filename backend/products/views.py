from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from .models import Product
from .serializers import ProductSerializer
from .tasks import scrape_product_price


class RegisterView(APIView):
    """Registro público de nuevos usuarios."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '')

        if not username or not password:
            return Response(
                {'error': 'Usuario y contraseña son requeridos.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Ese nombre de usuario ya está en uso.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if email and User.objects.filter(email=email).exists():
            return Response(
                {'error': 'Ese correo ya está registrado.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        return Response(
            {'message': f'Usuario "{user.username}" creado exitosamente.'},
            status=status.HTTP_201_CREATED
        )


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Solo productos activos del usuario autenticado
        return Product.objects.filter(
            user=self.request.user,
            deleted_at__isnull=True
        ).prefetch_related('history')

    def perform_create(self, serializer):
        product = serializer.save(user=self.request.user)
        import threading
        threading.Thread(target=scrape_product_price, args=(product.id,), daemon=True).start()

    def perform_destroy(self, instance):
        # Soft Delete
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=False, methods=['get'])
    def trash(self, request):
        """Lista productos en la papelera del usuario."""
        queryset = Product.objects.filter(
            user=self.request.user,
            deleted_at__isnull=False
        ).prefetch_related('history')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restaura un producto de la papelera."""
        product = get_object_or_404(
            Product, pk=pk, user=self.request.user, deleted_at__isnull=False
        )
        product.deleted_at = None
        product.save()
        return Response({'status': 'restaurado'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'])
    def hard_delete(self, request, pk=None):
        """Eliminación física permanente."""
        product = get_object_or_404(
            Product, pk=pk, user=self.request.user, deleted_at__isnull=False
        )
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)