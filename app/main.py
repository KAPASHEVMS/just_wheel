from fastapi.staticfiles import StaticFiles

from .routes import app

app.mount("/static", StaticFiles(directory="app/static"), name="static")
