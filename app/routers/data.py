# 文件: app/routers/data.py

from fastapi import APIRouter, Depends, Query, status
from typing import Dict, List, Any
import asyncio

from ..common.response_model import ResponseModel, APIException
from ..common.dependencies import get_user_from_header_or_query
from ..services import get_field_mappings, get_historical_data_as_json
from ..globals import logger
from ..models import User

# 核心修改：APIRouter() 不再包含 prefix
router = APIRouter()


@router.get("/field-mappings", response_model=ResponseModel[Dict[str, str]])
def get_field_mappings_route():
    """获取数据字段的映射关系。"""
    try:
        mappings = get_field_mappings()
        return ResponseModel(data=mappings)
    except Exception as e:
        logger.error(f"获取字段映射失败: {e}", exc_info=True)
        raise APIException(code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg="获取字段映射失败")


@router.get("/download-history", response_model=ResponseModel[List[Dict[str, Any]]])
async def download_historical_data(
        codes: str = Query(..., description="股票代码，多个用逗号分隔"),
        start_date: str = Query(..., description="开始日期 (YYYY-MM-DD)"),
        end_date: str = Query(..., description="结束日期 (YYYY-MM-DD)"),
        period: str = Query("daily", description="数据周期: daily, weekly, monthly"),
        adjust: str = Query("qfq", description="复权方式: qfq(前复权), hfq(后复权), none(不复权)"),
        current_user: User = Depends(get_user_from_header_or_query)
):
    """下载指定股票代码的历史K线数据。"""
    try:
        code_list = [code.strip() for code in codes.split(',') if code.strip()]
        tasks = [get_historical_data_as_json(code, start_date, end_date, adjust, period) for code in code_list]
        results = await asyncio.gather(*tasks)

        all_data = []
        for res in results:
            if res and res.get('data'):
                all_data.extend(res['data'])
        return ResponseModel(data=all_data)
    except Exception as e:
        logger.error(f"下载历史数据失败: {e}", exc_info=True)
        raise APIException(code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg="获取历史数据失败")