"""聚合所有路由。新增模块时在此注册即可。"""
from fastapi import APIRouter

from app.api.routes import academic_years, auth, events, registration, schedule, settings

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(academic_years.router)
api_router.include_router(events.router)
api_router.include_router(registration.router)
api_router.include_router(schedule.router)
api_router.include_router(settings.router)
