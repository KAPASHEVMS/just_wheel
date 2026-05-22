from typing import List
from urllib.parse import quote_plus

from ..schemas import CompetitorPriceCreate, ProductCreate
from .browser import get_driver

MAX_RESULTS = 5
YANDEX_HOME = "https://market.yandex.ru/"


def _build_query(product: ProductCreate) -> str:
    if product.search_query:
        return product.search_query.strip()
    parts = [product.brand, product.model, product.size]
    return " ".join(p for p in parts if p and p != "Unknown").strip()


def _extract_price_and_title(text: str):
    import re as _re
    match = _re.search(r"(\d[\d\s\u00A0]{2,9})", text)
    if not match:
        return 0.0, text[:120]
    raw = match.group(1)
    raw = raw.replace(" ", "").replace("\u00A0", "").replace("\u2009", "").replace("\u202F", "")
    try:
        val = int(raw)
    except ValueError:
        return 0.0, text[:120]
    if 50 < val < 10000000:
        title = (text[:match.start()] + " " + text[match.end():]).strip()
        import re as _re2
        title = _re2.sub(r'\d+\s*отзыв[ао][в]?', '', title)
        title = _re2.sub(r'\d+\.\d+\s*★?\s*\d*\s*отзыв[ао][в]?', '', title)
        title = " ".join(title.split())[:120]
        return float(val), title
    return 0.0, text[:120]


def fetch_yandex_prices(product: ProductCreate) -> List[CompetitorPriceCreate]:
    query = _build_query(product)
    url = f"https://market.yandex.ru/search?text={quote_plus(query)}"

    try:
        driver = get_driver()
        driver.get(url)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time

        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/product/'], article, div[data-zone-name='snippet']"))
            )
        except Exception:
            pass

        time.sleep(3)

        prices: List[CompetitorPriceCreate] = []
        seen_urls = set()

        # Ищем карточки товаров
        for selector in ["a[href*='/product/']", "article a[href]", "div[data-zone-name='snippet'] a[href]"]:
            links = driver.find_elements(By.CSS_SELECTOR, selector)
            if links:
                break

        for link in links[:15]:
            try:
                href = link.get_attribute("href")
                if not href or ("/product/" not in href and "/offer/" not in href):
                    continue
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                parent = link.find_element(By.XPATH, "../..")
                text = driver.execute_script("return arguments[0].textContent.trim()", parent)
                text = text[:500]
                if len(text) < 10:
                    parent = link.find_element(By.XPATH, "..")
                    text = driver.execute_script("return arguments[0].textContent.trim()", parent)
                    text = text[:500]

                if len(text) < 10:
                    continue

                price, title = _extract_price_and_title(text)
                if price <= 50 or not title or len(title) < 3:
                    continue

                full_url = href
                if full_url.startswith("/"):
                    full_url = f"https://market.yandex.ru{full_url}"

                prices.append(CompetitorPriceCreate(
                    competitor="Yandex", title=title, price=price, url=full_url,
                ))
                if len(prices) >= MAX_RESULTS:
                    break
            except Exception:
                continue

        if prices:
            return prices

    except Exception:
        pass

    display_title = product.search_query or f"{product.brand} {product.model or ''} {product.size}".strip()
    return [
        CompetitorPriceCreate(
            competitor="Yandex", title=display_title, price=0.0, url=YANDEX_HOME,
        )
    ]
