# 文件: app/routers/monitor.py (最终修正版)

import asyncio
import json
import datetime
import threading
from fastapi import APIRouter, Request, Query, Depends, status

from fastapi.responses import StreamingResponse

from ..models import User
from ..common.dependencies import get_user_from_header_or_query
from ..common.response_model import ResponseModel, APIException
from ..services.stock_data import get_field_mappings, fetch_stock_data_async, codes_to_market_list_async
from ..plans import PLANS_CONFIG

# 从全局模块导入 logger 和新添加的状态管理器
from ..globals import (
    logger,
    LAST_KNOWN_GOOD_DATA, LAST_GOOD_DATA_LOCK,
    ACTIVE_CONNECTIONS, CONNECTION_LOCK
)

router = APIRouter()


@router.get("/sse/market-data")
async def stream_market_data(
        request: Request,
        codes: str = Query(..., description="股票代码，多个用逗号分隔"),
        interval: float = Query(5.0, ge=0.2, description="刷新间隔(秒)"),
        current_user: User = Depends(get_user_from_header_or_query)
):
    """通过 Server-Sent Events (SSE) 实时推送市场数据 (融合了健壮性逻辑)。"""

    # --- 1. 权限检查升级 ---
    user_plan_config = PLANS_CONFIG.get(current_user.plan, PLANS_CONFIG["freemium"])
    user_client_id = f"USER_{current_user.id}"

    # 检查套餐是否过期 (admin角色豁免)
    # **【已修正】** 使用 is_superuser 替代不存在的 role 字段
    if not current_user.is_superuser and current_user.expires_at and datetime.datetime.utcnow() > current_user.expires_at:
        raise APIException(code=status.HTTP_403_FORBIDDEN, msg="您的订阅已过期，请续费后使用。")

    # 检查代码数量
    code_list = [code.strip().upper() for code in codes.split(',') if code.strip()]
    max_codes = user_plan_config.get("max_codes", -1)
    if max_codes != -1 and len(code_list) > max_codes:
        raise APIException(code=status.HTTP_403_FORBIDDEN, msg=f"超出套餐允许的最大股票代码数量 ({max_codes})。")

    # 检查请求间隔
    min_interval = user_plan_config.get("min_interval", 5)
    if interval < min_interval:
        raise APIException(code=status.HTTP_403_FORBIDDEN, msg=f"请求间隔太快，您的套餐最低允许 {min_interval} 秒。")

    # --- 2. 连接数管理 ---
    max_connections = user_plan_config.get("max_connections", 1)
    with CONNECTION_LOCK:
        current_connections = ACTIVE_CONNECTIONS.get(user_client_id, 0)
        if max_connections != -1 and current_connections >= max_connections:
            raise APIException(code=status.HTTP_429_TOO_MANY_REQUESTS, msg=f"连接数已达上限 ({max_connections})。")
        ACTIVE_CONNECTIONS[user_client_id] = current_connections + 1
        logger.info(
            f"为用户 {current_user.email} ({current_user.plan} 套餐) 建立连接。当前连接数: {ACTIVE_CONNECTIONS[user_client_id]}")

    async def event_generator():
        try:
            # --- 3. 增强的用户反馈：处理无效代码 ---
            conversion_result = await codes_to_market_list_async(codes, timeout=interval)
            market_codes_str = conversion_result['valid']
            invalid_codes = conversion_result['invalid']

            if invalid_codes:
                warning_message = f"注意：以下代码无效或无法识别，已被忽略: {', '.join(invalid_codes)}"
                payload = {"timestamp": datetime.datetime.utcnow().isoformat(), "data": [], "status": "warning",
                           "message": warning_message}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            if not market_codes_str:
                if not invalid_codes:
                    info_message = "未提供任何有效代码。"
                    payload = {"timestamp": datetime.datetime.utcnow().isoformat(), "data": [], "status": "info",
                               "message": info_message}
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                return

            logger.info(f"SSE 流开始为 {current_user.email} 处理, 市场代码: {market_codes_str}")

            while True:
                if await request.is_disconnected():
                    logger.info(f"客户端 {current_user.email} 断开连接。")
                    break

                # --- 4. 核心健壮性逻辑：获取数据并使用“最后一次成功数据”缓存 ---
                data_to_send = []
                try:
                    processed_data = await fetch_stock_data_async(market_codes_str, timeout=interval)
                    if processed_data:
                        with LAST_GOOD_DATA_LOCK:
                            LAST_KNOWN_GOOD_DATA[market_codes_str] = processed_data
                        data_to_send = processed_data
                        status_msg, message = "live", "实时数据"
                    else:
                        with LAST_GOOD_DATA_LOCK:
                            data_to_send = LAST_KNOWN_GOOD_DATA.get(market_codes_str, [])
                        status_msg, message = "live", "实时数据"
                        logger.warning(f"上游API为 {market_codes_str} 返回空数据, 已为 {current_user.email} 提供缓存。")

                except Exception as e:
                    with LAST_GOOD_DATA_LOCK:
                        data_to_send = LAST_KNOWN_GOOD_DATA.get(market_codes_str, [])
                    status_msg, message = f"live", f"实时数据"
                    logger.error(f"获取 {market_codes_str} 数据时发生异常: {e}。已为 {current_user.email} 提供缓存。",
                                 exc_info=False)

                # --- 5. 丰富的SSE载荷 ---
                payload = {
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "data": data_to_send,
                    "status": status_msg,
                    "message": message
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

                await asyncio.sleep(interval)

        except Exception as e:
            logger.error(f"SSE 流发生严重错误 for {current_user.email}: {e}", exc_info=True)
            error_payload = json.dumps({'message': f"An error occurred in the stream: {e}", 'status': 'error'})
            yield f"event: error\ndata: {error_payload}\n\n"
        finally:
            # 确保在任何情况下都能减少连接计数
            with CONNECTION_LOCK:
                if user_client_id in ACTIVE_CONNECTIONS:
                    ACTIVE_CONNECTIONS[user_client_id] -= 1
                    if ACTIVE_CONNECTIONS[user_client_id] <= 0:
                        del ACTIVE_CONNECTIONS[user_client_id]
            logger.info(
                f"SSE 连接关闭，释放资源: {current_user.email}。剩余连接数: {ACTIVE_CONNECTIONS.get(user_client_id, 0)}")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/config/field-map", response_model=ResponseModel[dict])
def get_data_field_map():
    """获取监控数据所使用的字段映射。(保持原有结构)"""
    return ResponseModel(data=get_field_mappings())