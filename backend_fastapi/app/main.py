from fastapi import FastAPI
from app.core import config
from app.api.endpoints import logs
from app.core.database import engine, Base

# Create Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=config.settings.PROJECT_NAME,
    version=config.settings.VERSION,
    openapi_url=f"{config.settings.API_V1_STR}/openapi.json"
)

app.include_router(logs.router, prefix=f"{config.settings.API_V1_STR}/logs", tags=["logs"])

@app.get("/")
def root():
    return {"message": "Welcome to CLAIR OBSCUR API"}
