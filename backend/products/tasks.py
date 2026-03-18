import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Product, PriceHistory
from .scraper import get_mercadolibre_data

logger = logging.getLogger(__name__)


def scrape_product_price(product_id):
    """
    Obtiene el precio, guarda el historial y notifica si hay oferta.
    """
    try:
        product = Product.objects.get(id=product_id)
        price_before = product.current_price

        data = get_mercadolibre_data(product.url)
        logger.info(f"[SCRAPER] Resultado para {product.url}: {data}")

        if data['price']:
            product.current_price = data['price']
            product.is_available = True
            if not product.name or product.name == "Procesando...":
                product.name = data['name']
            product.save()

            PriceHistory.objects.create(
                product=product,
                captured_price=data['price']
            )

            target = float(product.target_price)
            current = float(data['price'])
            price_before_float = float(price_before) if price_before is not None else None

            if current <= target:
                # Enviar alerta si:
                # 1. Es la primera vez (price_before_float es None)
                # 2. El precio venía por encima del objetivo y ahora bajó (cruce del umbral)
                # 3. El precio cambió a un valor diferente y sigue cumpliendo el objetivo
                should_notify = (
                    price_before_float is None
                    or price_before_float > target
                    or price_before_float != current
                )
                if should_notify:
                    logger.info(f"[ALERTA] {product.name} — precio {current} cumple objetivo {target} (anterior: {price_before_float})")
                    send_alert_email(product)
        else:
            # Sin precio: usar el campo 'available' del scraper para distinguir
            # entre error técnico (available=True) y sin stock real (available=False)
            scraper_available = data.get('available', True)  # default=True = error de scraper, no sin stock
            product.is_available = scraper_available
            if data.get('name') and not data['name'].startswith('Error:'):
                if not product.name or product.name == "Procesando...":
                    product.name = data['name']
            product.save()
            if scraper_available:
                logger.warning(f"[SCRAPER] No se obtuvo precio (posible error de scraper) para {product.url}")
            else:
                logger.info(f"[SCRAPER] Producto marcado como sin stock para {product.url}")

    except Product.DoesNotExist:
        logger.error(f"[SCRAPER] Producto con ID {product_id} no existe")
    except Exception as e:
        logger.exception(f"[SCRAPER] Error inesperado al procesar producto {product_id}: {e}")


def send_alert_email(product):
    """
    Envía un correo HTML profesional al usuario dueño del producto.
    """
    username = product.user.username
    recipient = product.user.email
    if not recipient:
        logger.warning(f"[EMAIL] El usuario {username} no tiene correo registrado.")
        return

    subject = f"🎯 ¡Tu precio objetivo fue alcanzado! — {product.name}"

    plain_message = (
        f"¡Hola {username}!\n\n"
        f"El producto que estabas siguiendo ha alcanzado tu precio objetivo.\n\n"
        f"Producto: {product.name}\n"
        f"Precio Actual: ${product.current_price}\n"
        f"Tu Objetivo: ${product.target_price}\n\n"
        f"Link de compra: {product.url}\n\n"
        f"¡Aprovechá antes de que suba!"
    )

    html_message = f"""
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Precio Alcanzado</title>
</head>
<body style="margin:0;padding:0;background-color:#0f0f10;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f0f10;padding:40px 16px;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

          <!-- HEADER -->
          <tr>
            <td align="center" style="padding-bottom:32px;">
              <div style="display:inline-block;background:linear-gradient(135deg,#1a73e8,#0d47a1);border-radius:16px;padding:14px 28px;">
                <span style="color:#ffffff;font-size:20px;font-weight:800;letter-spacing:-0.5px;">📊 PriceMonitor</span>
              </div>
            </td>
          </tr>

          <!-- CARD PRINCIPAL -->
          <tr>
            <td style="background-color:#1e1f20;border-radius:24px;border:1px solid #37393b;overflow:hidden;">

              <!-- BANNER VERDE -->
              <div style="background:linear-gradient(135deg,#1a3a22,#0f2a18);padding:32px;text-align:center;border-bottom:1px solid #2d5a35;">
                <div style="font-size:48px;margin-bottom:12px;">🎯</div>
                <h1 style="color:#4ade80;font-size:26px;font-weight:800;margin:0 0 8px 0;letter-spacing:-0.5px;">¡Precio objetivo alcanzado!</h1>
                <p style="color:#86efac;font-size:15px;margin:0;">Hola <strong>{username}</strong>, tenemos buenas noticias para vos.</p>
              </div>

              <!-- CUERPO -->
              <div style="padding:32px;">

                <!-- NOMBRE DEL PRODUCTO -->
                <p style="color:#9ca3af;font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin:0 0 8px 0;">Producto</p>
                <p style="color:#e3e3e3;font-size:18px;font-weight:700;margin:0 0 28px 0;line-height:1.4;">{product.name}</p>

                <!-- PRECIOS -->
                <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
                  <tr>
                    <td width="48%" style="background-color:#131314;border:2px solid #4ade80;border-radius:16px;padding:20px;text-align:center;">
                      <p style="color:#6b7280;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin:0 0 8px 0;">Precio Actual</p>
                      <p style="color:#4ade80;font-size:28px;font-weight:800;margin:0;">${float(product.current_price):,.0f}</p>
                    </td>
                    <td width="4%"></td>
                    <td width="48%" style="background-color:#131314;border:1px solid #37393b;border-radius:16px;padding:20px;text-align:center;">
                      <p style="color:#6b7280;font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin:0 0 8px 0;">Tu Objetivo</p>
                      <p style="color:#60a5fa;font-size:28px;font-weight:800;margin:0;">${float(product.target_price):,.0f}</p>
                    </td>
                  </tr>
                </table>

                <!-- CTA BUTTON -->
                <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
                  <tr>
                    <td align="center">
                      <a href="{product.url}" target="_blank"
                         style="display:inline-block;background:linear-gradient(135deg,#1a73e8,#0d47a1);color:#ffffff;font-size:15px;font-weight:700;text-decoration:none;padding:16px 40px;border-radius:14px;letter-spacing:0.3px;">
                         🛍️ Ver producto y comprar
                      </a>
                    </td>
                  </tr>
                </table>

                <!-- AVISO -->
                <div style="background-color:#131314;border:1px solid #37393b;border-radius:12px;padding:14px 18px;">
                  <p style="color:#6b7280;font-size:12px;margin:0;line-height:1.6;">
                    ⚡ Los precios pueden cambiar en cualquier momento. Te recomendamos aprovechar esta oportunidad cuanto antes.
                  </p>
                </div>

              </div>
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td align="center" style="padding-top:28px;">
              <p style="color:#4b5563;font-size:12px;margin:0;">
                Este correo fue enviado por <strong style="color:#6b7280;">PriceMonitor</strong> porque tenés un producto monitoreado.<br>
                <a href="mailto:preciosmonitor@gmail.com" style="color:#4b5563;text-decoration:none;">preciosmonitor@gmail.com</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"[EMAIL] Alerta HTML enviada a {recipient} por {product.name}")
    except Exception as e:
        logger.exception(f"[EMAIL] Error al enviar alerta para {product.name}: {e}")


def update_all_products_prices():
    """
    Tarea periódica que actualiza precios de todos los productos activos.
    """
    active_products = Product.objects.filter(deleted_at__isnull=True)
    logger.info(f"[SCRAPER] Iniciando actualización masiva de {active_products.count()} productos")
    for product in active_products:
        scrape_product_price(product.id)