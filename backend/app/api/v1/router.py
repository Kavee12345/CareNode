from fastapi import APIRouter
from app.api.v1 import auth, users, documents, chat, health_timeline, agent

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(documents.router)
api_router.include_router(chat.router)
api_router.include_router(health_timeline.router)
api_router.include_router(agent.router)
