# 文件: app/services/iwencai_scraper.py

import httpx
import asyncio
import json
import math
import os
import subprocess
from typing import AsyncGenerator, List, Dict, Any

from ..globals import logger
from fake_useragent import UserAgent


# ==========================================================
#         【新增】自定义异常类
# ==========================================================
class ScraperException(Exception):
    """自定义爬虫异常，用于封装对用户友好的错误信息。"""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


# ==========================================================

REQUEST_COOKIES = {
    "other_uid": "Ths_iwencai_Xuangu_vdvjnt4x1qr8qltcbtsoakhlu7j43xs2",
    "ta_random_userid": "ju99ai1yph",
    "cid": "6a6505ed12d53a4a5774c39ec5f58f661733312372",
    "ComputerID": "6a6505ed12d53a4a5774c39ec5f58f661733312372",
    "WafStatus": "0",
    "u_ukey": "A10702B8689642C6BE607730E11E6E4A",
    "u_uver": "1.0.0",
    "u_dpass": "aQiX%2BohyVMY2fOPx4ElbVVxNc%2FMXa4NLbd0NjOD1%2F1O0J6UTkGFDTt1crNeImieCHi80LrSsTFH9a%2B6rtRvqGg%3D%3D",
    "u_did": "E3A1B5703E9C4C8084612762553BC3A0",
    "u_ttype": "WEB",
    "guideState": "1",
    "wencai_pc_version": "1",
    "user_status": "1",
    "cuc": "po7l089f0pfv",
    "sess_tk": "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6InNlc3NfdGtfMSIsImJ0eSI6InNlc3NfdGsifQ.eyJqdGkiOiI2NzU4YjI4ZS1hM2U1LTQ3OWMtODQyMi1kYjM5NjFmMjdlMDYiLCJpYXQiOjE3NTM5Mzc5ODcsImV4cCI6MTc1NDU0Mjc4Nywic3ViIjoiNzk3MDMyMDY1IiwiaXNzIjoidXBhc3MuaXdlbmNhaS5jb20iLCJhdWQiOiIyMDIwMTExODUyODg5MDcyIiwiY3VocyI6IjU3OTY2NGIzZWQ3NTJlMDU0N2EyNDJiM2MwNThiZmJiOGM0MWYxNjFhYjdmMjE0ZGUyMDhiMzM2YzY1MzgyNzEifQ.k3cEza89REZ_EtoTaH5gkJaNABhK-A3A7PshXg8iqauj1SpV91HKXRPXvLBokyd4Gh42kq_H_1ZfCgVqwwptOQ",
}


class IWenCaiScraper:
    GET_ROBOT_DATA_URL = "https://www.iwencai.com/customized/chart/get-robot-data"
    GET_DATA_LIST_URL = "https://www.iwencai.com/gateway/urp/v7/landing/getDataList"

    def __init__(self):
        self._cookies = REQUEST_COOKIES
        try:
            self.ua = UserAgent(fallback='Mozilla/5.0')
        except Exception:
            class FallbackUA:
                @property
                def random(
                        self): return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'

            self.ua = FallbackUA()
        self.async_client = httpx.AsyncClient(cookies=self._cookies, timeout=20.0)

    async def _get_v_value_async(self) -> str:
        js_file_path = os.path.join(os.path.dirname(__file__), '2.js')
        if not os.path.exists(js_file_path):
            raise ScraperException("服务器内部配置错误 (缺少JS依赖)。")

        def run_node_sync():
            try:
                result = subprocess.run(
                    ['node', js_file_path], capture_output=True, text=True, check=True, encoding='utf-8'
                )
                lines = result.stdout.strip().splitlines()
                if not lines: raise ValueError("Node.js 脚本未返回有效数据。")
                return lines[-1]
            except FileNotFoundError:
                raise ScraperException("服务器环境错误 (缺少Node.js运行时)。")
            except subprocess.CalledProcessError as e:
                logger.error(f"执行 '2.js' 失败: {e.stderr.strip()}")
                raise ScraperException("无法生成有效的请求凭证。")
            except Exception as e:
                logger.error(f"执行 '2.js' 时发生未知错误: {e}")
                raise ScraperException("生成请求凭证时发生未知错误。")

        return await asyncio.to_thread(run_node_sync)

    async def fetch_data_stream(self, question: str, secondary_intent: str) -> AsyncGenerator[
        List[Dict[str, Any]], None]:

        try:
            v_value = await self._get_v_value_async()
            self.async_client.headers['hexin-v'] = v_value
            self.async_client.headers['user-agent'] = self.ua.random

            # --- 获取第一页数据 ---
            resp = await self.async_client.post(self.GET_ROBOT_DATA_URL, json={
                "source": "Ths_iwencai_Xuangu", "version": "2.0", "question": question, "perpage": 100,
                "page": 1, "secondary_intent": secondary_intent,
                "add_info": "{\"urp\":{\"scene\":1,\"company\":1,\"business\":1},\"contentType\":\"json\",\"searchInfo\":true}",
                "rsh": self._cookies.get('other_uid')
            })
            resp.raise_for_status()
            json_data = resp.json()

            component = \
            json_data.get('data', {}).get('answer', [{}])[0].get('txt', [{}])[0].get('content', {}).get('components',
                                                                                                        [{}])[0]
            if not component or 'data' not in component:
                raise ScraperException("无法解析问财返回的数据结构，可能是查询条件无结果或接口已变更。")

            result_data = component['data']
            meta_extra = result_data['meta']['extra']
            params = {
                'condition': meta_extra.get('condition'),
                'urp_sort_index': result_data['meta'].get('urp_sort_index'),
                'logid': json_data.get('data', {}).get('logid'),
                'sessionid': result_data['meta'].get('sessionid'),
                'iwc_token': meta_extra.get('token'),
                'comp_id': component.get('cid'),
                'uuid': component.get('puuid'),
            }
            first_page_results = result_data.get('datas', [])
            total_pages = math.ceil(meta_extra.get('row_count', 0) / 100)

            if first_page_results:
                yield first_page_results

            if total_pages <= 1: return

            # --- 并发获取剩余分页 ---
            tasks = []
            for page_num in range(2, total_pages + 1):
                page_data = {
                    "query": question, "page": str(page_num), "perpage": "100", "source": "Ths_iwencai_Xuangu",
                    "logid": params['logid'], "ret": "json_all", "sessionid": params['sessionid'],
                    "iwc_token": params['iwc_token'], "user_id": self._cookies.get('other_uid'),
                    "uuids[0]": params['uuid'], "query_type": secondary_intent, "comp_id": params['comp_id'],
                    "business_cat": "soniu", "uuid": params['uuid'], "condition": params['condition'],
                    "urp_sort_index": params['urp_sort_index']
                }
                tasks.append(self.async_client.post(self.GET_DATA_LIST_URL, data=page_data))

            for task in asyncio.as_completed(tasks):
                try:
                    res = await task
                    res.raise_for_status()
                    json_data = res.json()
                    if components := json_data.get('answer', {}).get('components'):
                        if data := components[0].get('data'):
                            if page_results := data.get('datas'):
                                yield page_results
                except httpx.HTTPStatusError as e:
                    logger.warning(f"处理分页响应时出错 (状态码: {e.response.status_code})")
                except Exception as e:
                    logger.warning(f"处理分页时发生未知异常: {e}")

        except httpx.HTTPStatusError as e:
            logger.error(f"请求问财服务器失败，状态码: {e.response.status_code}", exc_info=False)
            if e.response.status_code == 403:
                raise ScraperException("当前查询人数过多，请稍后再试。")
            else:
                raise ScraperException(f"数据服务暂时不可用 (状态码: {e.response.status_code})。")
        except ScraperException:
            raise
        except Exception as e:
            logger.error(f"爬虫执行时发生未知严重错误: {e}", exc_info=True)
            raise ScraperException("执行查询时发生未知内部错误，请联系管理员。")

    async def fetch_all_data_once(self, question: str, secondary_intent: str) -> list:
        all_data = []
        async for data_chunk in self.fetch_data_stream(question, secondary_intent):
            all_data.extend(data_chunk)
        return all_data