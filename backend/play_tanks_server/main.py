from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from play_tanks_server.api.v1.routes import router as api_router
from play_tanks_server.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version="1.0.0"
)


origins = [
    "http://localhost:5173",
    "http://localhost:8000",
    
    # add production domain later
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
     return {"message": "Hello FastAPI"}