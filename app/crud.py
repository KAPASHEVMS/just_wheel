from sqlalchemy.orm import Session

from . import models, schemas


def get_product_by_details(db: Session, brand: str, size: str, type_: str):
    return db.query(models.Product).filter(
        models.Product.brand == brand,
        models.Product.size == size,
        models.Product.type == type_,
    ).first()


def create_product(db: Session, product: schemas.ProductCreate):
    db_product = models.Product(
        category=product.category,
        brand=product.brand,
        model=product.model,
        size=product.size,
        type=product.type,
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def create_competitor_prices(db: Session, product_id: int, prices: list[schemas.CompetitorPriceCreate]):
    created = []
    for price_data in prices:
        item = models.CompetitorPrice(
            product_id=product_id,
            competitor=price_data.competitor,
            title=price_data.title,
            price=price_data.price,
            url=price_data.url,
        )
        db.add(item)
        created.append(item)
    db.commit()
    return created


def create_prediction(db: Session, product_id: int, prediction: schemas.PredictionCreate):
    db_prediction = models.Prediction(
        product_id=product_id,
        predicted_price=prediction.predicted_price,
        margin=prediction.margin,
    )
    db.add(db_prediction)
    db.commit()
    db.refresh(db_prediction)
    return db_prediction


def save_parsed_products(db: Session, search_query: str, prices: list[schemas.CompetitorPriceCreate], replace: bool = True):
    """Сохраняет спаршенные товары. Если replace=True — удаляет старые записи для этого запроса."""
    if replace:
        db.query(models.ParsedProduct).filter(models.ParsedProduct.search_query == search_query).delete()
    saved = []
    for p in prices:
        item = models.ParsedProduct(
            search_query=search_query,
            title=p.title,
            price=p.price,
            url=p.url,
            competitor=p.competitor,
        )
        db.add(item)
        saved.append(item)
    db.commit()
    return saved


def get_parsed_products(db: Session, search_query: str = None) -> list[models.ParsedProduct]:
    """Возвращает сохранённые спаршенные товары по запросу или все."""
    q = db.query(models.ParsedProduct)
    if search_query:
        q = q.filter(models.ParsedProduct.search_query == search_query)
    return q.order_by(models.ParsedProduct.created_at.desc()).all()


def get_distinct_queries(db: Session) -> list[str]:
    """Возвращает список уникальных поисковых запросов из parsed_products."""
    result = db.query(models.ParsedProduct.search_query).distinct().all()
    return [r[0] for r in result]


def search_queries(db: Session, prefix: str) -> list[str]:
    """Возвращает список запросов, начинающихся с prefix."""
    result = db.query(models.ParsedProduct.search_query).filter(
        models.ParsedProduct.search_query.ilike(f"{prefix}%")
    ).distinct().limit(15).all()
    return [r[0] for r in result]


def delete_parsed_product(db: Session, product_id: int):
    db.query(models.ParsedProduct).filter(models.ParsedProduct.id == product_id).delete()
    db.commit()


def save_estimate(db: Session, search_query: str, recommended_price: float, category: str, type: str, items_count: int):
    # Удаляем старую оценку для этого запроса, если есть
    db.query(models.Estimate).filter(models.Estimate.search_query == search_query).delete()
    item = models.Estimate(
        search_query=search_query,
        recommended_price=recommended_price,
        category=category,
        type=type,
        items_count=items_count,
    )
    db.add(item)
    db.commit()
    return item


def get_estimates(db: Session) -> list[models.Estimate]:
    return db.query(models.Estimate).order_by(models.Estimate.created_at.desc()).all()


def delete_estimate(db: Session, estimate_id: int):
    db.query(models.Estimate).filter(models.Estimate.id == estimate_id).delete()
    db.commit()


def clear_parsed_products(db: Session):
    db.query(models.ParsedProduct).delete()
    db.commit()


def clear_estimates(db: Session):
    db.query(models.Estimate).delete()
    db.commit()


def get_latest_estimate(db: Session, search_query: str):
    return db.query(models.Estimate).filter(
        models.Estimate.search_query == search_query
    ).order_by(models.Estimate.created_at.desc()).first()
