from app.main import app
print(f"App: {app.title}")
print("Routes:", [r.path for r in app.routes])
