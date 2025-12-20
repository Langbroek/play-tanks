from fastapi import APIRouter

from .models_3d.model_routes import router as model_router


router = APIRouter()

router.include_router(model_router)


@router.get("/ping")
def ping():
    return {"ping": "pong v1"}


@router.get("/env")
def get_env():
    from play_tanks_server.core.config import settings
    return {
        "app_name": settings.app_name,
        "debug": settings.debug,
        "model_folder": settings.models_dir
    }