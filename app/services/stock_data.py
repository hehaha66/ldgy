# app/services.py

import asyncio
import random
import json
import logging
import requests
from typing import List, Dict, Any, Optional
from functools import lru_cache

from ..globals import logger

# --- 导入：用于获取随机 User-Agent ---
from fake_useragent import UserAgent


# --- 外部 API 配置信息 ---

def get_eastmoney_fields() -> str:
    """返回东方财富 API 所需的字段参数 (fields)."""
    return 'f12,f13,f14,f19,f139,f148,f2,f4,f1,f125,f18,f3,f152,f6,f20,f21,f9,f23,f8,f5,f37,f49,f100,f7,f10,f17,f16,f15,f62,f70,f71,f64,f65,f76,f77,f82,f83,f26,f38,f54,f57'


SEARCH_API_TOKEN = "D433A59954249B6723224A37D4929D34"
DATA_API_UT_TOKEN = 'fa5fd1943c7b386f172d6893dbfba10b'


# --- UserAgent 的惰性加载 ---
@lru_cache(maxsize=1)
def get_user_agent_generator():
    """
    惰性加载并缓存 UserAgent 实例，避免在应用启动时阻塞。
    """
    try:
        # UserAgent 实例可以缓存 User-Agent 列表，避免每次都去网络获取。
        return UserAgent(
            fallback='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        )
    except Exception as e:
        logger.error(f"初始化 fake_useragent 失败，将使用静态UA: {e}")

        class FallbackUserAgent:
            @property
            def random(self):
                return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"

        return FallbackUserAgent()


# ===================================================================
# 数据处理和字段映射逻辑
# ===================================================================

# 原始字段映射 (作为原始定义的参考，用于生成 PROCESSED_FIELD_MAPPING)
FIELD_MAPPING_RAW = {
    'f12': {'name': '股票代码', 'type': str}, 'f14': {'name': '名称', 'type': str},
    'f2': {'name': '最新价', 'type': float, 'dynamic_precision': True},
    'f3': {'name': '涨跌幅(%)', 'type': float, 'transform': lambda x: x / 100.0 if x is not None else None},
    'f4': {'name': '涨跌额', 'type': float, 'dynamic_precision': True},
    'f6': {'name': '成交额(亿)', 'type': float, 'transform': lambda x: x / 100000000.0 if x is not None else None},
    'f20': {'name': '总市值(亿)', 'type': float, 'transform': lambda x: x / 100000000.0 if x is not None else None},
    'f21': {'name': '流通市值(亿)', 'type': float, 'transform': lambda x: x / 100000000.0 if x is not None else None},
    'f9': {'name': '市盈率', 'type': float, 'transform': lambda x: x / 100.0 if x is not None else None},
    'f23': {'name': '市净率', 'type': float, 'transform': lambda x: x / 100.0 if x is not None else None},
    'f8': {'name': '换手率(%)', 'type': float, 'transform': lambda x: x / 100.0 if x is not None else None},
    'f5': {'name': '总手(万)', 'type': float, 'transform': lambda x: x / 10000.0 if x is not None else None},
    'f37': {'name': '净资产收益率(加权)', 'type': float}, 'f49': {'name': '毛利率', 'type': float},
    'f100': {'name': '所属行业板块', 'type': str},
    'f7': {'name': '振幅(%)', 'type': float, 'transform': lambda x: x / 100.0 if x is not None else None},
    'f10': {'name': '量比', 'type': float, 'transform': lambda x: x / 100.0 if x is not None else None},
    'f18': {'name': '昨收', 'type': float, 'dynamic_precision': True},
    'f17': {'name': '开盘价', 'type': float, 'dynamic_precision': True},
    'f16': {'name': '最低价', 'type': float, 'dynamic_precision': True},
    'f15': {'name': '最高价', 'type': float, 'dynamic_precision': True},
    'f62': {'name': '主力净流入(亿)', 'type': float, 'transform': lambda x: x / 100000000.0 if x is not None else None},
    'f70': {'name': '大单流入(亿)', 'type': float, 'transform': lambda x: x / 100000000.0 if x is not None else None},
    'f71': {'name': '大单流出(亿)', 'type': float, 'transform': lambda x: x / 100000000.0 if x is not None else None},
    'f64': {'name': '超大单流入(亿)', 'type': float, 'transform': lambda x: x / 100000000.0 if x is not None else None},
    'f65': {'name': '超大单流出(亿)', 'type': float, 'transform': lambda x: x / 100000000.0 if x is not None else None},
    'f76': {'name': '中单流入(亿)', 'type': float, 'transform': lambda x: x / 100000000.0 if x is not None else None},
    'f77': {'name': '中单流出(亿)', 'type': float, 'transform': lambda x: x / 100000000.0 if x is not None else None},
    'f82': {'name': '小单流入(亿)', 'type': float, 'transform': lambda x: x / 100000000.0 if x is not None else None},
    'f83': {'name': '小单流出(亿)', 'type': float, 'transform': lambda x: x / 100000000.0 if x is not None else None},
    'f26': {'name': '上市日期', 'type': str,
            'transform': lambda x: f"{s[:4]}-{s[4:6]}-{s[6:]}" if (s := str(x)) and len(s) == 8 else None},
    'f38': {'name': '总股本(亿)', 'type': float, 'transform': lambda x: x / 100000000.0 if x is not None else None},
    'f54': {'name': '总负债(亿)', 'type': float, 'transform': lambda x: x / 100000000.0 if x is not None else None},
    'f57': {'name': '资产负债比率', 'type': float},
    'f1': {'name': '市场类型代码', 'type': int}, 'f13': {'name': '市场代码', 'type': int},
}

PROCESSED_FIELD_MAPPING = []
FIELD_NAME_TO_AN_MAP = {}
AN_TO_FIELD_NAME_MAP = {}

current_a_index = 1
for f_key, raw_config in FIELD_MAPPING_RAW.items():
    a_name = f'a{current_a_index}'
    processed_config = {
        'f_key': f_key,
        'an_name': a_name,
        'name': raw_config['name'],
        'type': raw_config['type'],
        'transform': raw_config.get('transform'),
        'dynamic_precision': raw_config.get('dynamic_precision', False)
    }
    PROCESSED_FIELD_MAPPING.append(processed_config)
    FIELD_NAME_TO_AN_MAP[raw_config['name']] = a_name
    AN_TO_FIELD_NAME_MAP[a_name] = raw_config['name']
    current_a_index += 1


def get_a_field_names() -> List[str]:
    return [config['an_name'] for config in PROCESSED_FIELD_MAPPING]


def get_field_name_to_an_map() -> Dict[str, str]:
    return FIELD_NAME_TO_AN_MAP


def get_an_to_field_name_map() -> Dict[str, str]:
    return AN_TO_FIELD_NAME_MAP


def process_stock_item(raw_item: Dict[str, Any]) -> Dict[str, Any]:
    processed_item = {}
    precision_exponent = 2
    f1_val = raw_item.get('f1')
    if f1_val is not None and f1_val != '-':
        try:
            precision_exponent = int(f1_val)
        except (ValueError, TypeError):
            logger.warning(f"无效的精度指示符f1: '{f1_val}'，将使用默认值 2。")
    divisor_for_price = 10 ** precision_exponent

    for field_config in PROCESSED_FIELD_MAPPING:
        f_key = field_config['f_key']
        an_name = field_config['an_name']
        raw_value = raw_item.get(f_key, '-')
        if raw_value == '-' or raw_value is None:
            processed_item[an_name] = None
            continue
        try:
            converted_value = field_config['type'](raw_value)
            if field_config.get('dynamic_precision', False):
                processed_item[an_name] = converted_value / divisor_for_price
            elif field_config.get('transform'):
                processed_item[an_name] = field_config['transform'](converted_value)
            else:
                processed_item[an_name] = converted_value
        except (ValueError, TypeError):
            processed_item[an_name] = None
            logger.debug(f"字段 '{field_config['name']}' (f_key: {f_key}) 转换失败，原始值: '{raw_value}'")
    return processed_item


# --- 同步爬虫函数 (这些函数将通过 asyncio.to_thread 异步调用) ---

def _fetch_stock_data_sync(selects: str, timeout: float = 10.0) -> list:
    if not selects:
        return []

    ua_generator = get_user_agent_generator()  # 在函数内部获取实例

    k = random.randint(10, 99)
    base_url = f'https://{k}.push2.eastmoney.com/api/qt/ulist/sse'
    params = {
        'secids': selects.replace(' ', ''), 'fields': get_eastmoney_fields(), 'invt': '3',
        'ut': DATA_API_UT_TOKEN, 'fid': '', 'po': '1', 'pi': '0', 'pz': '30000',
        'mpi': '6000', 'dect': '1',
    }
    headers = {'User-Agent': ua_generator.random}

    try:
        response = requests.get(base_url, headers=headers, params=params, stream=True, timeout=timeout)
        response.raise_for_status()
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data:'):
                    json_str = decoded_line[len('data:'):].strip()
                    try:
                        parsed_json = json.loads(json_str)
                        if parsed_json and 'data' in parsed_json and parsed_json['data'] and 'diff' in parsed_json[
                            'data']:
                            return list(parsed_json['data']['diff'].values())
                        else:
                            return []
                    except json.JSONDecodeError:
                        return []
        return []
    except requests.exceptions.RequestException as e:
        logger.warning(f"RequestError in _fetch_stock_data_sync for {selects}: {type(e).__name__} - {e}",
                       exc_info=False)  # 在生产中可以关闭详细exc_info
        return []


def _find_market_info_sync(raw_code: str, timeout: float = 10.0) -> str | None:
    ua_generator = get_user_agent_generator()  # 在函数内部获取实例

    url = "https://searchapi.eastmoney.com/api/suggest/get"
    params = {"input": raw_code, "type": "14", "token": SEARCH_API_TOKEN, "count": 5}
    headers = {"User-Agent": ua_generator.random}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        quote_data = data.get("QuotationCodeTable", {}).get("Data", [])
        if quote_data:
            return quote_data[0].get('QuoteID')
        return None
    except (requests.RequestException, json.JSONDecodeError, IndexError, KeyError, TypeError) as e:
        logger.warning(f"Error in _find_market_info_sync for {raw_code}: {type(e).__name__} - {e}", exc_info=False)
        return None


# --- 异步包装函数 (这些是 FastAPI 路由将直接调用的函数) ---

async def fetch_stock_data_async(selects: str, timeout: float = 10.0) -> list:
    raw_data_list = await asyncio.to_thread(_fetch_stock_data_sync, selects, timeout)
    processed_data_list = [process_stock_item(item) for item in raw_data_list]
    return processed_data_list


async def find_market_info_async(raw_code: str, timeout: float = 5.0) -> str | None:
    return await asyncio.to_thread(_find_market_info_sync, raw_code, timeout)


async def codes_to_market_list_async(codes_str: str, timeout: float = 5.0) -> Dict[str, any]:
    if not isinstance(codes_str, str) or not codes_str:
        return {'valid': "", 'invalid': []}

    code_list = list(set(code.strip().upper() for code in codes_str.split(',') if code.strip()))

    tasks = {code: find_market_info_async(code, timeout) for code in code_list}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    valid_codes = []
    invalid_codes = []
    original_codes = list(tasks.keys())

    for i, res in enumerate(results):
        original_code = original_codes[i]
        if isinstance(res, str) and res:
            try:
                market_code, code_only = res.split('.')
                # 东方财富API：1->上海, 0->深圳。其他市场代码如105->美股, 116->港股
                # 我们需要将1和0转换为它们自己的代码，其他市场的代码直接使用
                # 这是一个简化的处理，实际可能更复杂
                if market_code == '1' or market_code == '0':
                    valid_codes.append(f"{market_code}.{code_only}")
                else:
                    # 对于非A股，API可能返回原始代码，我们需要拼接市场代码
                    valid_codes.append(f"{market_code}.{original_code}")
            except (ValueError, AttributeError):
                invalid_codes.append(original_code)
        else:
            invalid_codes.append(original_code)

    return {'valid': ",".join(valid_codes), 'invalid': invalid_codes}


def get_field_mappings() -> Dict[str, str]:
    return AN_TO_FIELD_NAME_MAP