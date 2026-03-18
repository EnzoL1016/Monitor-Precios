import re
import logging
import json
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

OUT_OF_STOCK_SELECTORS = [
    ".ui-pdp-stock-information",
    "[data-testid='stock-information']",
    ".stock-unavailable",
    ".out-of-stock",
    "[class*='out-of-stock']",
    "[class*='sin-stock']",
    "[class*='agotado']",
    ".product-unavailable",
]

OUT_OF_STOCK_PHRASES = [
    "sin stock", "sin existencias", "agotado", "out of stock",
    "temporalmente sin stock", "no tenemos stock", "fuera de stock",
    "producto no disponible", "este producto no está disponible",
]

def check_out_of_stock_targeted(soup) -> bool:
    try:
        for sel in OUT_OF_STOCK_SELECTORS:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(" ", strip=True).lower()
                if any(phrase in text for phrase in OUT_OF_STOCK_PHRASES):
                    logger.info(f"[SCRAPER] Sin stock detectado en selector '{sel}': {text[:80]}")
                    return True

        buy_selectors = [
            "button[data-testid*='buy']",
            ".andes-button--filled",
            "[class*='buy']",
            "[data-testid*='add-to-cart']",
            ".add-to-cart",
            "button[class*='comprar']",
            "button[class*='agregar']",
        ]
        has_buy_button = any(soup.select_one(sel) for sel in buy_selectors)

        main_selectors = [
            ".ui-pdp-container",
            "#productInfo",
            ".product-detail",
            ".product-info",
            "[data-component='product-page']",
        ]
        for main_sel in main_selectors:
            main_el = soup.select_one(main_sel)
            if main_el:
                text = main_el.get_text(" ", strip=True).lower()
                if any(phrase in text for phrase in OUT_OF_STOCK_PHRASES) and not has_buy_button:
                    logger.info(f"[SCRAPER] Sin stock detectado en contenedor principal '{main_sel}'")
                    return True

    except Exception as e:
        logger.debug(f"[SCRAPER] Error en check_out_of_stock_targeted: {e}")

    return False

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

def fetch_html(url: str):
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return response.text
    except Exception as e:
        logger.warning(f"[SCRAPER] Error al hacer fetch de {url}: {e}")
        return None

def scrape_store(soup, url):
    domain = urlparse(url).netloc.lower()

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
            element = soup.select_one(selector)
            if element:
                raw_name = element.get_text(" ", strip=True)
                if raw_name and raw_name.upper() != "COMPRA GAMER":
                    name = raw_name
                    if "content_copy" in name:
                        name = name.split("content_copy")[0].strip()
                    logger.debug(f"[SCRAPER] Nombre con selector '{selector}': {name[:60]}")
                    break
    except Exception as e:
        logger.debug(f"[SCRAPER] Error capturando nombre en {domain}: {e}")

    if not name or name.upper() == "COMPRA GAMER":
        name = clean_title(soup)

    # Mercado Libre
    if "mercadolibre" in domain:
        try:
            selectors_ml = [
                ".ui-pdp-price__main-container .ui-pdp-price__second-line .andes-money-amount__fraction",
                ".ui-pdp-price__main-container .andes-money-amount__fraction",
                "span.andes-money-amount__fraction",
            ]
            for sel in selectors_ml:
                element = soup.select_one(sel)
                if element:
                    text = element.get_text(" ", strip=True)
                    val = extract_price_from_text(text)
                    if val:
                        logger.debug(f"[SCRAPER] Precio ML con '{sel}': {val}")
                        return {"name": name, "price": val}
        except Exception as e:
            logger.debug(f"[SCRAPER] Error precio ML: {e}")

    # Compra Gamer
    if "compragamer" in domain:
        try:
            for sel in ["span[class*='text-price']", ".cv-price span", ".price span"]:
                elements = soup.select(sel)
                for element in elements:
                    classes = " ".join(element.get("class", []))
                    if "underline" in classes:
                        continue
                    text = element.get_text(" ", strip=True)
                    val = extract_price_from_text(text)
                    if val and val > 1000:
                        logger.debug(f"[SCRAPER] Precio CG con '{sel}': {val}")
                        return {"name": name, "price": val}
        except Exception as e:
            logger.debug(f"[SCRAPER] Error precio CompraGamer: {e}")

    # Maximus
    if "maximus" in domain:
        try:
            for sel in ["[itemprop='price']", "div.itemBox--price-lg span.value-item--full-price",
                        ".price-main .price-especial", ".precio-especial", "[class*='price-transfer']"]:
                element = soup.select_one(sel)
                if element:
                    content_val = element.get("content")
                    if content_val:
                        val = to_float(content_val)
                    else:
                        val = extract_price_from_text(element.get_text(" ", strip=True))
                    if val:
                        logger.debug(f"[SCRAPER] Precio Maximus con '{sel}': {val}")
                        return {"name": name, "price": val}
        except Exception as e:
            logger.debug(f"[SCRAPER] Error precio Maximus: {e}")

    candidate_lists = [
        collect_json_ld_candidates(soup),
        collect_meta_candidates(soup),
        collect_selector_candidates(soup),
    ]
    candidates = []
    for lst in candidate_lists:
        candidates.extend(lst)

    filtered = []
    for c in candidates:
        cur = c.get("currency")
        cur = cur.upper() if cur else None
        if ("fravega" in domain or "compragamer" in domain or "maximus" in domain or "naldo" in domain) and cur == "USD":
            continue
        filtered.append({"value": c["value"], "currency": cur, "source": c.get("source")})

    if not filtered:
        filtered = candidates

    meta_candidates = [c for c in filtered if c.get("source") in ["jsonld", "meta"]]
    if meta_candidates:
        best_meta = max(meta_candidates, key=lambda x: x["value"])
        return {"name": name, "price": best_meta["value"]}

    ars = [c for c in filtered if c.get("currency") == "ARS"]
    pool = ars if ars else filtered

    min_val = 10000
    if "compragamer" in domain or "maximus" in domain or "naldo" in domain:
        min_val = 100000

    pool = [c for c in pool if c["value"] and c["value"] >= min_val] or pool

    if not pool:
        out_of_stock = check_out_of_stock_targeted(soup)
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
    try:
        domain = urlparse(url).netloc.lower()
        html = fetch_html(url)

        if not html:
            return {"name": "Error: no se pudo obtener la página", "price": None}

        soup = BeautifulSoup(html, "lxml")

        # Amazon
        if "amazon" in domain:
            name = clean_title(soup)

            for sel in [".priceToPay .a-offscreen", "#corePrice_desktop .a-offscreen",
                        "#corePrice_feature_div .a-offscreen",
                        ".a-price[data-a-color='price'] .a-offscreen"]:
                el = soup.select_one(sel)
                if el:
                    val = extract_price_from_text(el.get_text(" ", strip=True))
                    if val:
                        return {"name": name, "price": val}

            m = re.search(
                r'"priceToPay"\s*:\s*\{[^}]{0,300}"amount"\s*:\s*"?([\d.,]+)"?',
                html, flags=re.IGNORECASE
            )
            if m:
                val = to_float(m.group(1))
                if val:
                    return {"name": name, "price": val}

            m2 = re.search(
                r'<span[^>]*data-a-color="price"[^>]*>\s*<span[^>]*class="a-offscreen"[^>]*>([^<]+)</span>',
                html, flags=re.IGNORECASE
            )
            if m2:
                val = extract_price_from_text(m2.group(1))
                if val:
                    return {"name": name, "price": val}

            return {"name": name, "price": None}

        return scrape_store(soup, url)

    except Exception as e:
        logger.exception(f"[SCRAPER] Error en {url}: {e}")
        return {"name": f"Error: {str(e)[:80]}", "price": None}
