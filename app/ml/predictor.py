"""Корреляционно-регрессионный анализ — обучение на ВСЕХ товарах.

Признаки: brand_id, diameter, width, is_winter
Цель: медианная цена в группе (по search_query).
"""
import re
from collections import defaultdict
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from typing import List

from ..schemas import CompetitorPriceCreate, ProductCreate

SIZE_RE = re.compile(r'(\d{3})\s*/\s*(\d{2,3})\s*R\s*(\d{2})', re.IGNORECASE)


def _extract_brand(query: str) -> str:
    q = query or ""
    q = q.replace("Шины ", "").replace("Диски ", "")
    parts = q.split()
    return parts[0].lower() if parts else "unknown"


def _extract_size(query: str) -> tuple[int, int]:
    m = SIZE_RE.search(query or "")
    if m:
        return int(m.group(1)), int(m.group(3))
    return 0, 0


def _build_brand_index(db_products: list) -> dict[str, int]:
    brands = set()
    for item in db_products:
        if item.price > 0:
            brands.add(_extract_brand(item.search_query or ""))
    return {b: i for i, b in enumerate(sorted(brands))}


def _compute_stats(prices):
    if not prices:
        return {"avg": 0, "median": 0, "min": 0, "max": 0, "range": 0, "count": 0}
    arr = np.array(prices)
    return {
        "avg": float(np.mean(arr)), "median": float(np.median(arr)),
        "min": float(np.min(arr)), "max": float(np.max(arr)),
        "range": float(np.max(arr) - np.min(arr)), "count": len(prices),
    }


def _train_from_db(db_products: list):
    if not db_products or len(db_products) < 3:
        return None, {}
    brand_index = _build_brand_index(db_products)
    if not brand_index:
        return None, {}
    groups = defaultdict(list)
    meta = {}
    for item in db_products:
        if item.price <= 0:
            continue
        q = item.search_query or ""
        groups[q].append(item.price)
        if q not in meta:
            brand = _extract_brand(q)
            w, d = _extract_size(q)
            is_w = 1 if "зим" in q.lower() else 0
            meta[q] = (brand, w, d, is_w)
    X_rows, y_rows = [], []
    for q, prices in groups.items():
        if len(prices) < 1:
            continue
        brand, w, d, is_w = meta[q]
        bid = brand_index.get(brand, 0)
        X_rows.append([float(bid), float(d), float(w), float(is_w)])
        stats = _compute_stats(prices)
        y_rows.append(stats["median"])
    if len(X_rows) < 3:
        return None, {}
    model = LinearRegression()
    model.fit(np.array(X_rows), np.array(y_rows))
    y_pred = model.predict(np.array(X_rows))
    info = {
        "r2": round(r2_score(np.array(y_rows), y_pred), 4),
        "n_samples": len(X_rows),
        "n_queries": len(groups),
        "intercept": round(float(model.intercept_), 2),
        "brand_count": len(brand_index),
    }
    return model, info


def predict_market_price(product, competitor_prices, db_products=None):
    prices = [p.price for p in competitor_prices if p.price > 0]
    if db_products and len(db_products) >= 3:
        model, info = _train_from_db(db_products)
        if model:
            brand_index = _build_brand_index(db_products)
            query = product.search_query or ""
            brand = _extract_brand(query)
            w, d = _extract_size(query)
            is_w = 1 if "зим" in query.lower() else 0
            bid = brand_index.get(brand, 0)
            X_new = np.array([[float(bid), float(d), float(w), float(is_w)]])
            pred = model.predict(X_new)[0]
            pred = float(pred)
            if prices:
                median = float(np.median(prices))
                pred = float(np.clip(pred, median * 0.6, median * 1.5))
            return round(max(pred, 100), 2)
    if not prices:
        return 0.0
    arr = np.array(prices)
    return round(float(np.median(arr)) * 0.7 + float(np.mean(arr)) * 0.3, 2)


def get_feature_importance(db_products):
    model, info = _train_from_db(db_products)
    if model is None:
        return {}, {}
    names = ["brand_id", "diameter", "width", "is_winter"]
    coefs = model.coef_.tolist() if hasattr(model.coef_, 'tolist') else list(model.coef_)
    return dict(zip(names, coefs)), info
