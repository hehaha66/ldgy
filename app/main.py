# 文件: app/main.py (最终版)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import json

from .database import engine, Base
from .common.response_model import APIException, ResponseModel
from .routers import auth, admin, data, monitor, subscription, ai_stock, workspace, stream, notifications

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="雷达股眼 (LDSTOCK) API - 最终版",
    version="5.0.0",
    description="提供了用户认证、数据监控、AI选股以及高级工作区管理等功能。"
)

@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    content_dict = ResponseModel(code=exc.code, msg=exc.msg, data=None).model_dump()
    return JSONResponse(status_code=exc.code, content=content_dict)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(data.router, prefix="/api/data", tags=["Data"])
app.include_router(monitor.router, prefix="/api/monitor", tags=["Monitor"])
app.include_router(subscription.router, prefix="/api/subscription", tags=["Subscription"])
app.include_router(ai_stock.router, prefix="/api/ai_stock", tags=["AI Stock"])
app.include_router(workspace.router, prefix="/api/workspaces", tags=["Workspaces"])
app.include_router(stream.router, prefix="/api/stream", tags=["Streaming"])

app.include_router(notifications.router, prefix="/api", tags=["Notifications"])


@app.get("/", tags=["Default"], response_model=ResponseModel[str])
def read_root():
    return ResponseModel(data="Welcome to the final version of LDSTOCK API!")

@app.on_event("startup")
async def startup_event():
    print("\n" + "="*50)
    print("      所有已注册的 FastAPI 路由      ")
    print("="*50)
    route_list = []
    for route in app.routes:
        if hasattr(route, "methods"):
            route_list.append({"path": route.path, "name": route.name, "methods": sorted(list(route.methods))})
    print(json.dumps(route_list, indent=2))
    print("="*50 + "\n")