from typing import List, Optional

from pydantic import BaseModel, Field


class CompetitorPriceBase(BaseModel):
    competitor: str
    title: Optional[str]
    price: float
    url: Optional[str]


class CompetitorPriceCreate(CompetitorPriceBase):
    pass


class PredictionBase(BaseModel):
    predicted_price: float
    margin: Optional[float]


class PredictionCreate(PredictionBase):
    pass


class ProductBase(BaseModel):
    category: str = Field(..., example="Tire")
    brand: str = Field(..., example="Michelin")
    model: Optional[str] = Field(None, example="Primacy 4")
    size: str = Field(..., example="225/45R17")
    type: str = Field(..., example="Summer")
    search_query: Optional[str] = Field(None, example="Sailun Atrezzo eco Шины летние 185/65 R14")


class ProductCreate(ProductBase):
    pass


class CompetitorPrice(CompetitorPriceBase):
    id: int
    scraped_at: Optional[str]

    class Config:
        from_attributes = True


class Prediction(PredictionBase):
    id: int
    created_at: Optional[str]

    class Config:
        from_attributes = True


class Product(ProductBase):
    id: int
    competitor_prices: List[CompetitorPrice] = []
    predictions: List[Prediction] = []

    class Config:
        from_attributes = True
