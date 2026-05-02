from backend.api.app.api.endpoints import analytics, chat
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.app.core import config
from backend.api.app.api.endpoints import logs

app = FastAPI(
    title=config.settings.PROJECT_NAME,
    version=config.settings.VERSION,
    openapi_url=f"{config.settings.API_V1_STR}/openapi.json",
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(logs.router, prefix=f"{config.settings.API_V1_STR}/logs", tags=["logs"])
app.include_router(analytics.router, prefix=f"{config.settings.API_V1_STR}/analytics", tags=["analytics"])
app.include_router(chat.router, prefix=f"{config.settings.API_V1_STR}/chat", tags=["chat"])


@app.get("/")
def root():
    return {"message": "Welcome to CLAIR OBSCUR API"}
