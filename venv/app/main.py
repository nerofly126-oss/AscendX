from fastapi import FastAPI
from app.auth import routes as auth_routes
from app.database import Base, engine

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="FastAPI Auth System")

# Register routes
app.include_router(auth_routes.router)
