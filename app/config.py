from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://postgres:1234@localhost:5432/tire_price_db"
    secret_key: str = "change_this_secret"
    debug: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
