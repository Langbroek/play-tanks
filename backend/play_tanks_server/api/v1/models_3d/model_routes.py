from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pathlib import Path

from play_tanks_server.core.config import settings


router = APIRouter(prefix="/models", tags=["3D Models"])


def load_model(path: Path):
    with open(path, 'rb') as f:
        yield from f


@router.get("/")
def get_models():
    model_path = Path(settings.models_dir)
    models = []
    for file in model_path.iterdir():
        if file.is_file() and file.suffix == ".obj":
            models.append(file.name)

    return {"models": [models]}


@router.get("/{model_name}")
def get_model(model_name: str):
    model_path = Path(settings.models_dir) / model_name
    if model_path.suffix != '.obj':
        model_path = model_path.with_suffix('.obj')
    if not model_path.exists() or not model_path.is_file():
        return {"error": "Model not found"}, 404

    return StreamingResponse(
        load_model(model_path), 
        media_type='application/octet-stream', 
        headers={
          "Content-Disposition": f'attachment; filename="{model_path.name}"'
        }
    )
        