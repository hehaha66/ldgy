# app/data_service.py

import asyncio
import requests
import pandas as pd
from typing import List, Dict, Any
from functools import lru_cache
from ..globals import logger
from fake_useragent import UserAgent


@lru_cache(maxsize=1)
def get_user_agent_generator():
    """
    惰性加载并缓存 UserAgent 实例，以避免在应用启动时因网络请求而阻塞。
    """
    try:
        # UserAgent 实例会尝试从网络获取最新的UA列表
        # fallback 参数确保在网络失败时，有一个可用的默认UA
        return UserAgent(
            fallback='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36')
    except Exception as e:
        logger.error(f"初始化 fake_useragent 失败，将使用静态UA: {e}")

        # 定义一个简单的回退类，如果UserAgent初始化完全失败
        class FallbackUserAgent:
            @property
            def random(self):
                return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"

        return FallbackUserAgent()


async def _find_market_info_from_api_async(raw_code: str) -> (str | None, str | None):
    """
    异步版本：将 Ticker 转换为东方财富的 QuoteID 和标准 Ticker
    返回一个元组 (quote_id, security_code)
    """
    ua_generator = get_user_agent_generator()  # 在函数内部获取 UserAgent 实例

    url = "https://searchapi.eastmoney.com/api/suggest/get"
    params = {"input": raw_code, "type": "14", "token": "D433A59954249B6723224A37D4929D34", "count": 1}
    headers = {'User-Agent': ua_generator.random}

    try:
        # 使用 asyncio.to_thread 将同步的 requests.get 调用放入单独的线程中
        response = await asyncio.to_thread(
            requests.get, url, params=params, headers=headers, timeout=5
        )
        response.raise_for_status()
        data = response.json()
        first_result = data.get("QuotationCodeTable", {}).get("Data", [])[0]
        quote_id = first_result.get('QuoteID')
        security_code = first_result.get('SecurityCode')
        return quote_id, security_code
    except (requests.RequestException, IndexError, KeyError, TypeError) as e:
        logger.warning(f"在 _find_market_info_from_api_async 中为 {raw_code} 查找市场信息失败: {e}", exc_info=False)
        return None, None


async def _fetch_raw_data_logic(code: str, period: str, start_date: str, end_date: str, adjust: str) -> (
pd.DataFrame | None, str):
    """
    获取原始数据的核心逻辑。
    注意：akshare 的大部分函数是同步阻塞的，需要使用 asyncio.to_thread 调用。
    """
    import akshare as ak  # 在函数内部导入，避免模块加载时的潜在问题

    market = "unknown"
    df = None
    try:
        int(code)
        market = "A-Share" if len(code) > 5 else "HK-Share"
    except ValueError:
        market = "US-Share"

    try:
        if period in ['daily', 'weekly', 'monthly']:
            symbol_to_fetch = code
            if market == "US-Share":
                quote_id, _ = await _find_market_info_from_api_async(code)
                if not quote_id: return None, market
                symbol_to_fetch = quote_id

            if market == "A-Share":
                df = await asyncio.to_thread(ak.stock_zh_a_hist, symbol=symbol_to_fetch, period="daily",
                                             start_date=start_date, end_date=end_date, adjust=adjust)
            elif market == "HK-Share":
                df = await asyncio.to_thread(ak.stock_hk_hist, symbol=symbol_to_fetch, period="daily",
                                             start_date=start_date, end_date=end_date, adjust=adjust)
            elif market == "US-Share":
                df = await asyncio.to_thread(ak.stock_us_hist, symbol=symbol_to_fetch, period="daily",
                                             start_date=start_date, end_date=end_date, adjust=adjust)
        else:  # 分时数据
            symbol_to_fetch = code
            if market == "US-Share":
                _, security_code = await _find_market_info_from_api_async(code)
                if not security_code: return None, market
                symbol_to_fetch = security_code

            if market == "A-Share":
                df = await asyncio.to_thread(ak.stock_zh_a_hist_min_em, symbol=symbol_to_fetch, period=period,
                                             adjust=adjust)
            elif market == "HK-Share":
                df = await asyncio.to_thread(ak.stock_hk_hist_min_em, symbol=symbol_to_fetch, period=period,
                                             adjust=adjust)
            elif market == "US-Share":
                df = await asyncio.to_thread(ak.stock_us_hist_min_em, symbol=symbol_to_fetch, period=period,
                                             adjust=adjust)

    except Exception as e:
        logger.error(f"AKShare 获取数据时出错 - 代码: {code}, 周期: {period}, 错误: {e}", exc_info=False)
        df = None

    return df, market


def aggregate_kline_data(df: pd.DataFrame, period: str = 'daily') -> pd.DataFrame:
    """
    将日线数据聚合为周线或月线。
    """
    if df.empty or period == 'daily':
        return df

    df['日期'] = pd.to_datetime(df['日期'])
    df.set_index('日期', inplace=True)

    ohlc_rule = {'开盘': 'first', '最高': 'max', '最低': 'min', '收盘': 'last', '成交量': 'sum', '成交额': 'sum'}

    period_map = {'weekly': 'W', 'monthly': 'M'}
    if period in period_map:
        df_agg = df.resample(period_map[period]).apply(ohlc_rule)
        df_agg.dropna(inplace=True)
        return df_agg.reset_index()

    return df.reset_index()


async def get_historical_data_as_json(
        code_str: str,
        start_date: str,
        end_date: str,
        adjust: str,
        period: str
) -> Dict[str, Any]:
    """
    获取历史K线数据，并以JSON格式返回。
    """
    raw_code = code_str.strip()

    df, market = await _fetch_raw_data_logic(raw_code, period, start_date, end_date, adjust)

    if df is not None and not df.empty:
        df_period = df

        if '日期' in df_period.columns:
            if period in ['weekly', 'monthly']:
                df_period = aggregate_kline_data(df, period)
            rename_map = {'日期': 'date', '开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low',
                          '成交量': 'volume', '成交额': 'turnover'}
        elif '时间' in df_period.columns:
            rename_map = {'时间': 'date', '开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low',
                          '成交量': 'volume', '成交额': 'turnover'}
        else:
            return {"market": market, "code": raw_code, "data": [], "message": "在获取的数据中未找到日期/时间列"}

        df_period.rename(columns=rename_map, inplace=True)

        if 'date' in df_period.columns:
            df_period['date'] = df_period['date'].astype(str)

        data_list = df_period.to_dict(orient='records')

        return {
            "market": market,
            "code": raw_code,
            "data": data_list,
            "message": f"成功获取 {len(data_list)} 条记录。"
        }
    else:
        return {
            "market": market,
            "code": raw_code,
            "data": [],
            "message": "获取数据失败或代码无效。"
        }