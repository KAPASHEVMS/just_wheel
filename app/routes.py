import re
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from . import crud, ml, parsers, schemas
from .database import Base, engine, get_db
from .parsers.browser import close_driver

SIZE_PATTERN = re.compile(r'(\d{3})\s*/\s*(\d{2,3})\s*R\s*(\d{2})', re.IGNORECASE)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
    close_driver()


app = FastAPI(title="Market Price Estimator", lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")


# ===== ГЛАВНАЯ =====
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ===== API =====
@app.get("/api/queries")
def api_search_queries(q: str = "", db: Session = Depends(get_db)):
    if not q:
        return JSONResponse([])
    results = crud.search_queries(db, q)
    return JSONResponse(results)


# ===== ПАРСИНГ =====
@app.get("/parse", response_class=HTMLResponse)
def parse_page(request: Request, db: Session = Depends(get_db)):
    queries = crud.get_distinct_queries(db)
    history = {}
    for q in queries:
        items = crud.get_parsed_products(db, q)
        history[q] = items[:5]
    return templates.TemplateResponse("parse.html", {
        "request": request, "history": history,
    })


@app.post("/parse", response_class=HTMLResponse)
def parse_action(
    request: Request,
    category: str = Form("Tire"),
    brand: str = Form(""),
    width: str = Form(""),
    profile: str = Form(""),
    radius: str = Form(""),
    wheel_radius: str = Form(""),
    db: Session = Depends(get_db),
):
    # Собираем поисковый запрос
    if category == "Wheel":
        search_query = f"Диски {brand}"
        if wheel_radius:
            search_query += f" R{wheel_radius}"
    else:
        search_query = f"Шины {brand}"
        if width and profile and radius:
            search_query += f" {width}/{profile} R{radius}"
        elif width and radius:
            search_query += f" {width}/ R{radius}"
        elif radius:
            search_query += f" R{radius}"

    search_query = search_query.strip()

    product_data = schemas.ProductCreate(
        category=category, brand=brand, size="Unknown",
        type="Summer", search_query=search_query,
    )
    # Проверяем, есть ли уже товары для этого запроса
    existing_products = crud.get_parsed_products(db, search_query)
    existing_count = len(existing_products)

    prices = parsers.fetch_ozon_prices(product_data)
    save_prices = [p for p in prices if p.price > 0]
    replaced = False
    if save_prices:
        crud.save_parsed_products(db, search_query, save_prices, replace=True)
        replaced = existing_count > 0

    queries = crud.get_distinct_queries(db)
    history = {}
    for q in queries:
        items = crud.get_parsed_products(db, q)
        history[q] = items[:5]

    return templates.TemplateResponse("parse.html", {
        "request": request, "prices": save_prices,
        "search_query": search_query, "history": history,
        "brand": brand, "width": width, "profile": profile,
        "radius": radius, "wheel_radius": wheel_radius,
        "replaced": replaced,
    })


# ===== УДАЛЕНИЕ ТОВАРА =====
@app.get("/delete-parsed/{product_id}")
def delete_parsed(product_id: int, db: Session = Depends(get_db)):
    crud.delete_parsed_product(db, product_id)
    return RedirectResponse("/parsed", status_code=303)


@app.get("/clear-parsed")
def clear_parsed(db: Session = Depends(get_db)):
    crud.clear_parsed_products(db)
    return RedirectResponse("/parsed", status_code=303)


@app.get("/edit-parsed/{product_id}", response_class=HTMLResponse)
def edit_parsed_form(product_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.query(crud.models.ParsedProduct).filter(crud.models.ParsedProduct.id == product_id).first()
    if not item:
        return RedirectResponse("/parsed", status_code=303)
    return templates.TemplateResponse("edit_parsed.html", {
        "request": request, "item": item,
    })


@app.post("/edit-parsed/{product_id}")
def edit_parsed_save(
    product_id: int,
    request: Request,
    title: str = Form(""),
    price: float = Form(0.0),
    url: str = Form(""),
    db: Session = Depends(get_db),
):
    item = db.query(crud.models.ParsedProduct).filter(crud.models.ParsedProduct.id == product_id).first()
    if item:
        if title:
            item.title = title
        if price > 0:
            item.price = price
        if url:
            item.url = url
        db.commit()
    return RedirectResponse("/parsed", status_code=303)


# ===== ВСЕ ТОВАРЫ (CRUD) =====
@app.get("/parsed", response_class=HTMLResponse)
def parsed_list(request: Request, db: Session = Depends(get_db)):
    items = crud.get_parsed_products(db)
    return templates.TemplateResponse("parsed_list.html", {
        "request": request, "items": items,
    })


# ===== ОЦЕНКА ЦЕНЫ =====
@app.get("/estimate", response_class=HTMLResponse)
def estimate_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("estimate.html", {
        "request": request,
    })


@app.post("/estimate", response_class=HTMLResponse)
def estimate_action(
    request: Request,
    search_query: str = Form(...),
    category: str = Form("Tire"),
    type: str = Form("Summer"),
    db: Session = Depends(get_db),
):
    items = crud.get_parsed_products(db, search_query)
    competitor_prices = [
        schemas.CompetitorPriceCreate(
            competitor=item.competitor, title=item.title,
            price=item.price, url=item.url,
        )
        for item in items if item.price > 0
    ]

    all_products = crud.get_parsed_products(db)

    recommended = ml.predict_market_price(
        schemas.ProductCreate(
            category=category, brand="Unknown", size="Unknown",
            type=type, search_query=search_query,
        ),
        competitor_prices,
        db_products=all_products,
    )

    # Проверяем, была ли уже оценка для этого запроса
    existing = crud.get_latest_estimate(db, search_query)
    existing_data = None
    if existing:
        existing_data = {
            "recommended_price": existing.recommended_price,
            "created_at": existing.created_at.strftime("%d.%m.%Y %H:%M"),
        }

    # НЕ сохраняем — пользователь решит сам
    return templates.TemplateResponse("result.html", {
        "request": request, "search_query": search_query,
        "category": category, "type": type,
        "competitor_prices": competitor_prices,
        "recommended": recommended,
        "existing": existing_data,
    })


@app.post("/save-estimate")
def save_estimate_action(
    search_query: str = Form(...),
    category: str = Form("Tire"),
    type: str = Form("Summer"),
    recommended: float = Form(...),
    items_count: int = Form(0),
    db: Session = Depends(get_db),
):
    crud.save_estimate(db, search_query, recommended, category, type, items_count)
    return RedirectResponse("/estimates", status_code=303)


# ===== ИСТОРИЯ ОЦЕНОК =====
@app.get("/estimates", response_class=HTMLResponse)
def estimates_list(request: Request, db: Session = Depends(get_db)):
    items = crud.get_estimates(db)
    return templates.TemplateResponse("estimates.html", {
        "request": request, "items": items,
    })


@app.get("/delete-estimate/{estimate_id}")
def delete_estimate_route(estimate_id: int, db: Session = Depends(get_db)):
    crud.delete_estimate(db, estimate_id)
    return RedirectResponse("/estimates", status_code=303)


@app.get("/clear-estimates")
def clear_estimates_route(db: Session = Depends(get_db)):
    crud.clear_estimates(db)
    return RedirectResponse("/estimates", status_code=303)


@app.get("/edit-estimate/{estimate_id}", response_class=HTMLResponse)
def edit_estimate_form(estimate_id: int, request: Request, db: Session = Depends(get_db)):
    item = db.query(crud.models.Estimate).filter(crud.models.Estimate.id == estimate_id).first()
    if not item:
        return RedirectResponse("/estimates", status_code=303)
    return templates.TemplateResponse("edit_estimate.html", {
        "request": request, "item": item,
    })


@app.post("/edit-estimate/{estimate_id}")
def edit_estimate_save(
    estimate_id: int,
    search_query: str = Form(...),
    recommended_price: float = Form(...),
    category: str = Form("Tire"),
    type: str = Form("Summer"),
    db: Session = Depends(get_db),
):
    item = db.query(crud.models.Estimate).filter(crud.models.Estimate.id == estimate_id).first()
    if item:
        item.search_query = search_query
        item.recommended_price = recommended_price
        item.category = category
        item.type = type
        db.commit()
    return RedirectResponse("/estimates", status_code=303)


# ===== СТРАНИЦА АНАЛИЗА =====
@app.get("/analysis", response_class=HTMLResponse)
def analysis_page(request: Request, db: Session = Depends(get_db)):
    all_products = crud.get_parsed_products(db)
    importance, model_info = ml.get_feature_importance(all_products)

    # Вычисляем статистики для отображения
    total = len(all_products)
    queries = crud.get_distinct_queries(db)
    estimates = crud.get_estimates(db)

    # Описательные имена признаков
    feature_labels = {
        "brand_id": "Бренд (числовой код)",
        "diameter": "Диаметр шины (R14→14)",
        "width": "Ширина профиля (185→185)",
        "is_winter": "Зимняя/летняя (1/0)",
    }

    return templates.TemplateResponse("analysis.html", {
        "request": request,
        "total_products": total,
        "total_queries": len(queries),
        "total_estimates": len(estimates),
        "importance": importance,
        "model_info": model_info,
        "feature_labels": feature_labels,
        "model_trained": len(importance) > 0,
    })
