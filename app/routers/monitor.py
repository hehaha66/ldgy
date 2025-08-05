# 文件: app/routers/monitor.py

import asyncio
import json
import datetime
from fastapi import APIRouter, Request, Query, Depends, status

from fastapi.responses import StreamingResponse

from ..models import User
from ..common.dependencies import get_user_from_header_or_query
from ..common.response_model import ResponseModel, APIException
from ..services import get_field_mappings, fetch_stock_data_async, codes_to_market_list_async
from ..globals import logger
from ..plans import PLANS_CONFIG  # <-- 导入套餐配置

# 核心修改：APIRouter() 不再包含 prefix
router = APIRouter()


@router.get("/sse/market-data")
async def stream_market_data(
        request: Request,
        codes: str = Query(..., description="股票代码，多个用逗号分隔"),
        interval: float = Query(5.0, ge=0.2, description="刷新间隔(秒)"),
        current_user: User = Depends(get_user_from_header_or_query)
):
    """通过 Server-Sent Events (SSE) 实时推送市场数据。"""
    # --- 权限检查 ---
    # current_user 对象已经经过 apply_plan_limits 处理，包含了正确的套餐信息
    user_plan_config = PLANS_CONFIG.get(current_user.plan, PLANS_CONFIG["freemium"])

    code_list = [code.strip() for code in codes.split(',') if code.strip()]
    if user_plan_config["max_codes"] != -1 and len(code_list) > user_plan_config["max_codes"]:
        raise APIException(code=status.HTTP_403_FORBIDDEN,
                           msg=f"超出套餐允许的最大股票代码数量 ({user_plan_config['max_codes']})。")

    if interval < user_plan_config["min_interval"]:
        raise APIException(code=status.HTTP_403_FORBIDDEN,
                           msg=f"请求间隔太快，您的套餐最低允许 {user_plan_config['min_interval']} 秒。")

    # 可以在这里添加基于 current_user.id 的最大连接数检查

    async def event_generator():
        try:
            conversion_result = await codes_to_market_list_async(codes)
            market_codes_str = conversion_result['valid']

            if not market_codes_str:
                # 处理所有代码都无效的情况
                payload = {"error": "All provided stock codes are invalid."}
                yield f"event: error\ndata: {json.dumps(payload)}\n\n"
                return

            while True:
                if await request.is_disconnected():
                    logger.info(f"客户端 {current_user.email} 断开连接。")
                    break

                processed_data = await fetch_stock_data_async(market_codes_str)
                payload = {"timestamp": datetime.datetime.utcnow().isoformat(), "data": processed_data}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                await asyncio.sleep(interval)
        except Exception as e:
            logger.error(f"SSE 流错误: {e}", exc_info=True)
            error_payload = json.dumps({'message': f"An error occurred in the stream: {e}"})
            yield f"event: error\ndata: {error_payload}\n\n"
        finally:
            logger.info(f"SSE 连接关闭: {current_user.email}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/config/field-map", response_model=ResponseModel[dict])
def get_data_field_map():
    """获取监控数据所使用的字段映射。"""
    return ResponseModel(data=get_field_mappings())