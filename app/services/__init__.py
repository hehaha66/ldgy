# 文件: app/services/__init__.py

from .stock_data import (
    get_an_to_field_name_map,
    fetch_stock_data_async,
    codes_to_market_list_async,
)
from .data_service import get_historical_data_as_json
from .iwencai_scraper import IWenCaiScraper

# 为旧函数名提供一个别名，确保向后兼容
get_field_mappings = get_an_to_field_name_map