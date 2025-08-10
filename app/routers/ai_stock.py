# 文件: app/routers/ai_stock.py (最终修复版)

from fastapi import APIRouter, Request, Depends, status
from fastapi.responses import StreamingResponse, Response
import json
import time
from typing import Dict

from ..models import User
from ..common.dependencies import get_user_from_header_or_query
from ..services.iwencai_scraper import IWenCaiScraper, ScraperException
from ..common.response_model import APIException
from ..globals import logger

# ==========================================================
#                   核心修复点在这里
# ==========================================================
# 我们将 APIRouter 的定义恢复到你之前能工作的状态（不包含 prefix）
# prefix 将完全由 main.py 来管理
router = APIRouter()
# ==========================================================


# --- 权限与速率限制逻辑 ---
user_last_request: Dict[int, float] = {}


def check_permissions(user: User):
    """
    检查用户的AI选股权限和速率限制。
    """
    if not user.is_superuser:
        return

    if user.plan in ["pro", "master"]:
        # 对 Pro 和 Master 用户应用一个宽松的速率限制
        RATE_LIMIT_SECONDS = 5
        user_id = user.id
        current_time = time.time()
        last_request_time = user_last_request.get(user_id, 0)
        if current_time - last_request_time < RATE_LIMIT_SECONDS:
            seconds_to_wait = int(RATE_LIMIT_SECONDS - (current_time - last_request_time))
            raise APIException(
                code=status.HTTP_429_TOO_MANY_REQUESTS,
                msg=f"请求过于频繁，请在 {seconds_to_wait} 秒后重试。"
            )
        user_last_request[user_id] = current_time
        return

    elif user.plan == "freemium":
        # 对免费版用户应用严格的速率限制
        RATE_LIMIT_SECONDS = 500
        user_id = user.id
        current_time = time.time()
        last_request_time = user_last_request.get(user_id, 0)
        if current_time - last_request_time < RATE_LIMIT_SECONDS:
            seconds_to_wait = int(RATE_LIMIT_SECONDS - (current_time - last_request_time))
            raise APIException(
                code=status.HTTP_429_TOO_MANY_REQUESTS,
                msg=f"免费版用户请求频率受限，请在 {seconds_to_wait} 秒后重试。"
            )
        user_last_request[user_id] = current_time
        return

    raise APIException(
        code=status.HTTP_403_FORBIDDEN,
        msg="您的账户套餐不支持此功能。"
    )


# --- API 路由定义 ---
@router.head("/stream-query", summary="处理对AI选股流的HEAD预检请求")
def head_stream_query():
    return Response(status_code=status.HTTP_200_OK)


@router.get("/stream-query", summary="以SSE流方式执行AI选股查询")
async def stream_query(
        request: Request,
        question: str,
        secondary_intent: str,
        current_user: User = Depends(get_user_from_header_or_query)
):
    try:
        check_permissions(current_user)
    except APIException as e:
        async def error_stream(error_message: str):
            error_payload = json.dumps({'message': error_message})
            yield f"event: error\ndata: {error_payload}\n\n"

        return StreamingResponse(error_stream(e.detail), media_type="text/event-stream")

    scraper = IWenCaiScraper()

    async def event_generator():
        try:
            data_found = False
            async for data_chunk in scraper.fetch_data_stream(question, secondary_intent):
                if await request.is_disconnected():
                    logger.warning(f"客户端 {current_user.email} 断开连接，停止发送 AI 数据流。")
                    break
                if data_chunk:
                    data_found = True
                    yield f"data: {json.dumps(data_chunk, ensure_ascii=False)}\n\n"

            done_message = "Stream completed successfully." if data_found else "抱歉，未能根据您的条件找到匹配结果。"
            yield f"event: done\ndata: {json.dumps({'message': done_message})}\n\n"

        except ScraperException as e:
            logger.error(f"AI 选股服务失败: {e.message}")
            error_payload = json.dumps({'message': e.message})
            yield f"event: error\ndata: {error_payload}\n\n"
        except Exception as e:
            logger.error(f"AI 选股流式查询时发生未知错误: {e}", exc_info=True)
            error_payload = json.dumps({'message': "查询时发生未知服务器内部错误，请稍后重试。"})
            yield f"event: error\ndata: {error_payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")