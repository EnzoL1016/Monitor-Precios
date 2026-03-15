import re
import logging
import json
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# -----------------------------
# Selectores específicos de sin stock por sitio
# (solo se buscan dentro de contenedores de compra, NO en todo el HTML)
# -----------------------------
OUT_OF_STOCK_SELECTORS = [
    # Mercado Libre
    ".ui-pdp-stock-information",        # contenedor de stock específico de ML
    "[data-testid='stock-information']",
    # Genéricos
    ".stock-unavailable",
    ".out-of-stock",
    "[class*='out-of-stock']",
    "[class*='sin-stock']",
    "[class*='agotado']",
    ".product-unavailable",
]

# Frases de sin stock: SOLO se usan para validar el texto de los selectores anteriores,
# nunca sobre el HTML completo.
OUT_OF_STOCK_PHRASES = [
    "sin stock", "sin existencias", "agotado", "out of stock",
    "temporalmente sin stock", "no tenemos stock", "fuera de stock",
    "producto no disponible", "este producto no está disponible",
]

def check_out_of_stock_targeted(page) -> bool:
    """
    Verifica sin stock ÚNICAMENTE en elementos específicos relacionados a compra/stock.
    NO escanea el HTML completo (evita falsos positivos en filtros, footer, etc.).
    """
    try:
        # Intentar selectores específicos de sin stock
        for sel in OUT_OF_STOCK_SELECTORS:
            el = page.query_selector(sel)
            if el:
                text = el.inner_text().strip().lower()
                if any(phrase in text for phrase in OUT_OF_STOCK_PHRASES):
                    logger.info(f"[SCRAPER] Sin stock detectado en selector '{sel}': {text[:80]}")
                    return True

        # Verificar ausencia de botón de compra como señal secundaria
        buy_selectors = [
            "button[data-testid*='buy']",
            ".andes-button--filled",         # ML
            "[class*='buy']",
            "[data-testid*='add-to-cart']",
            ".add-to-cart",
            "button[class*='comprar']",
            "button[class*='agregar']",
        ]
        has_buy_button = any(page.query_selector(sel) for sel in buy_selectors)

        # Buscar solo en el contenedor principal del producto (no footer ni sidebar)
        main_selectors = [
            ".ui-pdp-container",       # Mercado Libre
            "#productInfo",            # tiendas genéricas
            ".product-detail",
            ".product-info",
            "[data-component='product-page']",
        ]
        for main_sel in main_selectors:
            main_el = page.query_selector(main_sel)
            if main_el:
                text = main_el.inner_text().lower()
                if any(phrase in text for phrase in OUT_OF_STOCK_PHRASES) and not has_buy_button:
                    logger.info(f"[SCRAPER] Sin stock detectado en contenedor principal '{main_sel}'")
                    return True

    except Exception as e:
        logger.debug(f"[SCRAPER] Error en check_out_of_stock_targeted: {e}")

    return False

# -----------------------------
# Normalización y parsing numérico
# -----------------------------
def normalize_number_string(s: str) -> str:
    s = s.strip()
    has_comma = "," in s
    has_dot = "." in s
    if has_comma and has_dot:
        if s.rfind(",") > s.rfind("."):
            return s.replace(".", "").replace(",", ".")
        else:
            return s.replace(",", "")
    if has_comma and not has_dot:
        parts = s.split(",")
        if len(parts[-1]) == 2:
            return s.replace(".", "").replace(",", ".")
        return s.replace(",", "")
    if has_dot and not has_comma:
        parts = s.split(".")
        if len(parts) == 1:
            return s
        if len(parts[-1]) == 2:
            return "".join(parts[:-1]).replace(".", "") + "." + parts[-1]
        return s.replace(".", "")
    return s

def to_float(s: str):
    try:
        return float(normalize_number_string(str(s)))
    except:
        return None

def extract_price_from_text(text):
    if not text:
        return None
    t = text.replace("\xa0", " ").strip()
    numbers = re.findall(r'[\d.,]+', t)
    for raw in numbers:
        val = to_float(raw)
        if val and 10 <= val <= 50000000:
            return val
    return None

# -----------------------------
# Utilidades comunes
# -----------------------------
def clean_title(soup):
    h1 = soup.find("h1")
    if h1:
        t = h1.get_text(" ", strip=True)
        if t and t.upper() != "COMPRA GAMER":
            return t

    el = soup.find(["span", "div"], class_=lambda c: c and (
        "title" in c.lower() or "product" in c.lower()))
    if el:
        t = el.get_text(" ", strip=True)
        if t and t.upper() != "COMPRA GAMER":
            return t

    meta = soup.find("meta", {"property": "og:title"})
    if meta and meta.get("content"):
        t = meta["content"].strip()
        if t and t.upper() != "COMPRA GAMER":
            return t

    title_tag = soup.find("title")
    if title_tag:
        t = title_tag.get_text(" ", strip=True)
        if t and t.upper() != "COMPRA GAMER":
            return t

    return "Producto"

def collect_json_ld_candidates(soup):
    cands = []
    for sc in soup.find_all("script", {"type": "application/ld+json"}):
        content = sc.string or sc.text
        if not content:
            continue
        try:
            data = json.loads(content)
        except Exception:
            continue
        nodes = []
        if isinstance(data, dict):
            nodes = [data]
            if "@graph" in data and isinstance(data["@graph"], list):
                nodes.extend(data["@graph"])
        elif isinstance(data, list):
            nodes = data

        def add_offer(offer):
            if not isinstance(offer, dict):
                return
            price = offer.get("price") or offer.get("priceSpecification", {}).get("price")
            currency = offer.get("priceCurrency") or offer.get("priceSpecification", {}).get("priceCurrency")
            val = to_float(price) if price is not None else None
            if val:
                cands.append({"value": val, "currency": (currency or "").upper() or None, "source": "jsonld"})

        for node in nodes:
            if not isinstance(node, dict):
                continue
            offers = node.get("offers")
            if not offers and isinstance(node.get("mainEntity"), dict):
                offers = node["mainEntity"].get("offers")
            if isinstance(offers, dict):
                add_offer(offers)
            elif isinstance(offers, list):
                for o in offers:
                    add_offer(o)
    return cands

def collect_meta_candidates(soup):
    cands = []
    meta_map = [
        {"tag": "meta", "attrs": {"itemprop": "price"}, "cur": {"itemprop": "priceCurrency"}},
        {"tag": "meta", "attrs": {"property": "product:price:amount"}, "cur": {"property": "product:price:currency"}},
        {"tag": "meta", "attrs": {"property": "og:price:amount"}, "cur": {"property": "og:price:currency"}},
        {"tag": "meta", "attrs": {"name": "price"}, "cur": {"name": "price:currency"}},
    ]
    for spec in meta_map:
        m = soup.find(spec["tag"], spec["attrs"])
        if m and m.get("content"):
            val = extract_price_from_text(m["content"])
            currency = None
            cmeta = soup.find("meta", spec["cur"])
            if cmeta and cmeta.get("content"):
                currency = cmeta["content"].upper()
            if val:
                cands.append({"value": val, "currency": currency, "source": "meta"})
    return cands

def collect_selector_candidates(soup):
    cands = []
    selectors = [
        "span.andes-money-amount__fraction",
        ".ui-pdp-price__part",
        "[data-testid='price']",
        "[data-test-id*='price']",
        "[data-testid*='price']",
        "[data-price]",
        "[class*='price']",
        "[class*='precio']",
        "[class*='amount']",
        "[id*='price']",
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(" ", strip=True)
            val = extract_price_from_text(text)
            if not val and el.has_attr("content"):
                val = extract_price_from_text(el["content"])
            if val:
                cands.append({"value": val, "currency": None, "source": f"selector:{sel}"})
    return cands

# -----------------------------
# Función general
# -----------------------------
def scrape_store(page, url):
    domain = urlparse(url).netloc.lower()
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(1500)

    # --- Nombre del producto ---
    name = None
    try:
        name_selectors = [
            "h1.ui-pdp-title",
            "div.title-product h1",
            "h1.product-details__info__title",
            ".product-info__name",
            "h2.entry-title",
            ".entry-title",
            "h1",
            "[data-testid='product-title']",
            ".product-title",
            ".product-name",
        ]
        for selector in name_selectors:
            if "product-details__info__title" in selector:
                try:
                    page.wait_for_selector(selector, timeout=4000)
                except:
                    pass
            element = page.query_selector(selector)
            if element:
                raw_name = element.inner_text().strip()
                if raw_name and raw_name.upper() != "COMPRA GAMER":
                    name = raw_name
                    if "content_copy" in name:
                        name = name.split("content_copy")[0].strip()
                    logger.debug(f"[SCRAPER] Nombre con selector '{selector}': {name[:60]}")
                    break
    except Exception as e:
        logger.debug(f"[SCRAPER] Error capturando nombre en {domain}: {e}")

    html = page.content()
    soup = BeautifulSoup(html, "html.parser")

    if not name or name.upper() == "COMPRA GAMER":
        name = clean_title(soup)
        logger.debug(f"[SCRAPER] Nombre por fallback: {name[:60]}")

    # --- Captura de precios por handlers específicos ---

    # Mercado Libre
    if "mercadolibre" in domain:
        try:
            selectors_ml = [
                ".ui-pdp-price__main-container .ui-pdp-price__second-line .andes-money-amount__fraction",
                ".ui-pdp-price__main-container .andes-money-amount__fraction",
                "span.andes-money-amount__fraction",
            ]
            for sel in selectors_ml:
                try:
                    page.wait_for_selector(sel, timeout=2000)
                except:
                    pass
                element = page.query_selector(sel)
                if element:
                    text = element.inner_text().strip()
                    val = extract_price_from_text(text)
                    if val:
                        logger.debug(f"[SCRAPER] Precio ML con '{sel}': {val}")
                        return {"name": name, "price": val}
        except Exception as e:
            logger.debug(f"[SCRAPER] Error precio ML: {e}")

    # Compra Gamer
    if "compragamer" in domain:
        try:
            selectors_cg = [
                "span[class*='text-price']:not([class*='underline'])",
                ".cv-price span[class*='text-price']",
                ".price span[class*='text-price']",
            ]
            for sel in selectors_cg:
                try:
                    page.wait_for_selector(sel, timeout=5000)
                except:
                    pass
                elements = page.query_selector_all(sel)
                for element in elements:
                    text = element.inner_text().strip()
                    parent_class = element.evaluate("el => el.parentElement.className")
                    if "underline" in str(parent_class):
                        continue
                    val = extract_price_from_text(text)
                    if val and val > 1000:
                        logger.debug(f"[SCRAPER] Precio CG con '{sel}': {val}")
                        return {"name": name, "price": val}
        except Exception as e:
            logger.debug(f"[SCRAPER] Error precio CompraGamer: {e}")

    # Maximus
    if "maximus" in domain:
        try:
            selectors_max = [
                "[itemprop='price']",               # Schema.org (más fiable)
                "div.itemBox--price-lg span.value-item--full-price",
                ".price-main .price-especial",
                ".precio-especial",
                "[class*='price-transfer']",
            ]
            for sel in selectors_max:
                element = page.query_selector(sel)
                if element:
                    # Para itemprop=price, leer el atributo content
                    content_val = element.get_attribute("content")
                    if content_val:
                        val = to_float(content_val)
                    else:
                        val = extract_price_from_text(element.inner_text().strip())
                    if val:
                        logger.debug(f"[SCRAPER] Precio Maximus con '{sel}': {val}")
                        return {"name": name, "price": val}
        except Exception as e:
            logger.debug(f"[SCRAPER] Error precio Maximus: {e}")

    # --- Para el resto: recolectar candidatos de metadatos y selectores ---
    candidate_lists = [
        collect_json_ld_candidates(soup),
        collect_meta_candidates(soup),
        collect_selector_candidates(soup),
    ]
    candidates = []
    for lst in candidate_lists:
        candidates.extend(lst)

    # Filtrar USD en dominios locales
    filtered = []
    for c in candidates:
        cur = c.get("currency")
        cur = cur.upper() if cur else None
        if ("fravega" in domain or "compragamer" in domain or "maximus" in domain or "naldo" in domain) and cur == "USD":
            continue
        filtered.append({"value": c["value"], "currency": cur, "source": c.get("source")})

    if not filtered:
        filtered = candidates

    # Prioridad a metadatos
    meta_candidates = [c for c in filtered if c.get("source") in ["jsonld", "meta"]]
    if meta_candidates:
        best_meta = max(meta_candidates, key=lambda x: x["value"])
        logger.debug(f"[SCRAPER] {domain} por metadatos: {best_meta}")
        return {"name": name, "price": best_meta["value"]}

    # Fallback: selectores visuales
    ars = [c for c in filtered if c.get("currency") == "ARS"]
    pool = ars if ars else filtered

    min_val = 10000
    if "compragamer" in domain or "maximus" in domain or "naldo" in domain:
        min_val = 100000

    pool = [c for c in pool if c["value"] and c["value"] >= min_val] or pool

    if not pool:
        # NO se pudo extraer ningún precio: ahora SÍ verificamos sin stock de forma quirúrgica
        out_of_stock = check_out_of_stock_targeted(page)
        logger.info(f"[SCRAPER] Sin precio en {domain}, sin stock detectado: {out_of_stock}")
        return {"name": name, "price": None, "available": not out_of_stock}

    if "fravega" in domain:
        best = min(pool, key=lambda x: x["value"])
    else:
        best = max(pool, key=lambda x: x["value"])

    logger.debug(f"[SCRAPER] {domain} candidatos visuales: {pool} | elegido: {best}")
    return {"name": name, "price": best["value"]}


# -----------------------------
# Entrypoint
# -----------------------------
def get_mercadolibre_data(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--single-process",
                "--no-zygote",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-default-apps",
                "--mute-audio",
                "--no-first-run",
            ]
        )
        context = browser.new_context(
            locale="es-AR",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            domain = urlparse(url).netloc.lower()

            # --- Amazon: estrategia multi-nivel ---
            if "amazon" in domain:
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                name = clean_title(soup)

                # 1) Selector DOM directo: .priceToPay es el bloque del precio de contado del producto
                #    Es más confiable que la regex porque Amazon puede tener multiple `.a-price` en la página
                amazon_selectors = [
                    ".priceToPay .a-offscreen",             # precio contado principal
                    "#corePrice_desktop .a-offscreen",      # precio en desktop
                    "#corePrice_feature_div .a-offscreen",  # feature div
                    ".a-price[data-a-color='price'] .a-offscreen",  # precio destacado
                ]
                for sel in amazon_selectors:
                    try:
                        page.wait_for_selector(sel, timeout=2000)
                    except:
                        pass
                    el = page.query_selector(sel)
                    if el:
                        text = el.inner_text().strip()
                        val = extract_price_from_text(text)
                        if val:
                            logger.debug(f"[SCRAPER] Amazon precio con selector '{sel}': {val}")
                            return {"name": name, "price": val}

                # 2) Regex acotada en el JSON embebido: busca "priceToPay" y toma el primer
                #    "amount" (valor numérico) dentro del mismo bloque de ~300 chars.
                #    Evita DOTALL ilimitado que cruzaba objetos de importación/envío.
                m = re.search(
                    r'"priceToPay"\s*:\s*\{[^}]{0,300}"amount"\s*:\s*"?([\d.,]+)"?',
                    html, flags=re.IGNORECASE
                )
                if m:
                    val = to_float(m.group(1))
                    if val:
                        logger.debug(f"[SCRAPER] Amazon precio por regex JSON amount: {val}")
                        return {"name": name, "price": val}

                # 3) Regex del span de precio visible (data-a-color="price")
                m2 = re.search(
                    r'<span[^>]*data-a-color="price"[^>]*>\s*<span[^>]*class="a-offscreen"[^>]*>([^<]+)</span>',
                    html, flags=re.IGNORECASE
                )
                if m2:
                    val = extract_price_from_text(m2.group(1))
                    if val:
                        logger.debug(f"[SCRAPER] Amazon precio por regex span: {val}")
                        return {"name": name, "price": val}


            result = scrape_store(page, url)
            return result

        except Exception as e:
            logger.exception(f"[SCRAPER] Error en {url}: {e}")
            return {"name": f"Error: {str(e)[:80]}", "price": None}
        finally:
            try:
                browser.close()
            except:
                pass
