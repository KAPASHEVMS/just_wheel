from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from .database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)
    brand = Column(String, nullable=False)
    model = Column(String, nullable=True)
    size = Column(String, nullable=False)
    type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    competitor_prices = relationship("CompetitorPrice", back_populates="product")
    predictions = relationship("Prediction", back_populates="product")


class CompetitorPrice(Base):
    __tablename__ = "competitor_prices"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    competitor = Column(String, nullable=False)
    title = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    url = Column(String, nullable=True)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="competitor_prices")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    predicted_price = Column(Float, nullable=False)
    margin = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    product = relationship("Product", back_populates="predictions")


class ParsedProduct(Base):
    __tablename__ = "parsed_products"

    id = Column(Integer, primary_key=True, index=True)
    search_query = Column(String, nullable=False)
    title = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    url = Column(String, nullable=True)
    competitor = Column(String, default="Ozon")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Estimate(Base):
    __tablename__ = "estimates"

    id = Column(Integer, primary_key=True, index=True)
    search_query = Column(String, nullable=False)
    recommended_price = Column(Float, nullable=False)
    category = Column(String, nullable=True)
    type = Column(String, nullable=True)
    items_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
