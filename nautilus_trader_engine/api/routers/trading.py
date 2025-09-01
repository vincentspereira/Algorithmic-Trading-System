
from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def get_trading_status():
    return {"status": "Trading router placeholder"}
