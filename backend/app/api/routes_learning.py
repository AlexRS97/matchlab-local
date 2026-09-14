from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/learning", tags=["learning"])


@router.get("/status")
def status(request: Request):
    return request.app.state.runtime.learning.status()


@router.post("/update", status_code=202)
async def update(request: Request):
    return request.app.state.runtime.learning.start()


@router.post("/train", status_code=202)
async def train(request: Request):
    return request.app.state.runtime.learning.start(force_train=True)
