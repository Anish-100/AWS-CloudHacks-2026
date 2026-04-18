from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from goals import router as goals_router
from transactions import router as transactions_router

app = FastAPI(title="Puran API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(goals_router)
app.include_router(transactions_router)

handler = Mangum(app, lifespan="off")
