from fastapi import APIRouter
from pipeline import get_recommendations
 
router = APIRouter()
 
@router.get("/recommendations/{user_id}")
def recommendations(user_id: str, income: int = 4500):
    return get_recommendations(user_id, income)