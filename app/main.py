# 文件: app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# 导入你的模块
from .database import engine, Base
from .common.response_model import APIException, ResponseModel
from .routers import auth, admin, data, monitor, subscription, ai_stock

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="雷达股眼 (LDSTOCK) API - 最终版",
    version="5.0.0"
)

# --- 全局异常处理器 ---
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.code,
        content=ResponseModel(code=exc.code, msg=exc.msg, data=None).model_dump()
    )

# --- CORS 中间件 ---
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


# --- 根路由 ---
@app.get("/", tags=["Default"], response_model=ResponseModel[str])
def read_root():
    return ResponseModel(data="Welcome to the final version of LDSTOCK API!")

