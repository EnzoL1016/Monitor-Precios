from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0004_product_deleted_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='is_available',
            field=models.BooleanField(default=True, verbose_name='Disponible'),
        ),
    ]
