"""Тест Яндекс.Маркета."""
import sys, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, ".")
from app.parsers.browser import get_driver, close_driver
from app.schemas import ProductCreate
from app.parsers.yandex import fetch_yandex_prices
from app.parsers.ozon import fetch_ozon_prices
from app.ml.predictor import predict_market_price

product = ProductCreate(
    category="Tire", brand="Sailun", model="Atrezzo",
    size="185/65R14", type="Summer",
    search_query="Sailun Atrezzo 185/65 R14",
)

print("YANDEX...")
t = time.time()
ya = fetch_yandex_prices(product)
print(f"  Time: {time.time()-t:.1f}s | Found: {len(ya)}")
for p in ya:
    title = p.title.encode('ascii', 'replace').decode()
    print(f"  [{p.competitor}] {p.price} RUB -- {title[:100]}")

print("\nOZON...")
t = time.time()
oz = fetch_ozon_prices(product)
print(f"  Time: {time.time()-t:.1f}s | Found: {len(oz)}")
for p in oz:
    title = p.title.encode('ascii', 'replace').decode()
    print(f"  [{p.competitor}] {p.price} RUB -- {title[:100]}")

rec = predict_market_price(product, ya + oz)
print(f"\n=== RECOMMENDED: {rec} RUB ===")

close_driver()
