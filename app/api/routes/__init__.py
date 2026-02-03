# API routes
from app.api.routes.team_info import router as team_info_router
from app.api.routes.agent_info import router as agent_info_router
from app.api.routes.model_architecture import router as model_architecture_router
from app.api.routes.execute import router as execute_router
from app.api.routes.students import router as students_router

__all__ = [
    "team_info_router",
    "agent_info_router",
    "model_architecture_router",
    "execute_router",
    "students_router",
]
