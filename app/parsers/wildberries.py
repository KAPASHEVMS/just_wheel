from typing import List
from urllib.parse import quote_plus

from ..schemas import CompetitorPriceCreate, ProductCreate
from .browser import get_driver

MAX_RESULTS = 5
WB_HOME = "https://www.wildberries.ru/"


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
        title = " ".join(title.split())[:120]
        return float(val), title
    return 0.0, text[:120]


def fetch_wildberries_prices(product: ProductCreate) -> List[CompetitorPriceCreate]:
    query = _build_query(product)
    url = f"https://www.wildberries.ru/catalog/0/search.aspx?search={quote_plus(query)}"

    try:
        driver = get_driver()
        driver.get(url)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time

        # Ждём прохождения антибота
        try:
            WebDriverWait(driver, 30).until_not(
                EC.title_contains("Почти готово")
            )
        except Exception:
            pass

        time.sleep(3)

        prices: List[CompetitorPriceCreate] = []
        seen_urls = set()

        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/catalog/']")
        for link in links[:15]:
            try:
                href = link.get_attribute("href")
                if not href or "/catalog/" not in href or "/search" in href:
                    continue
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                # parent^2 = карточка (через JS для textContent)
                try:
                    parent = link.find_element(By.XPATH, "../..")
                except Exception:
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
                    full_url = f"https://www.wildberries.ru{full_url}"

                prices.append(CompetitorPriceCreate(
                    competitor="Wildberries", title=title, price=price, url=full_url,
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
            competitor="Wildberries", title=display_title, price=0.0, url=WB_HOME,
        )
    ]
