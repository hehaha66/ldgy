import requests
import json
import math
from fake_useragent import UserAgent
import subprocess
import os
import random
def get_v_value():

    script_dir = os.path.dirname(os.path.abspath(__file__))

    js_file_path = os.path.join(script_dir, '2.js')
    
    if not os.path.exists(js_file_path):
        print(f"错误: 脚本 '2.js' 在目录 {script_dir} 中未找到。")
        return None

    result = subprocess.run(
        ['node', js_file_path],
        capture_output=True,

        text=True,
        check=True,
        encoding='utf-8'
    )
    lines = result.stdout.strip().splitlines()
    if lines:
        return lines[-1]



request_cookies = {
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
    "sess_tk": "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6InNlc3NfdGtfMSIsImJ0eSI6InNlc3NfdGsifQ.eyJqdGkiOiI2NzU4YjI4ZS1hM2U1LTQ3OWMtODQyMi1kYjM5NjFmMjdlMDYiLCJpYXQiOjE3NTM5Mzc5ODcsImV4cCI6MTc1NDU0Mjc4Nywic3ViIjoiNzk3MDMyMDY1IiwiaXNzIjoidXBhc3MuaXdlbmNhaS5jb20iLCJhdWQiOiIyMDIwMTExODUyODg5MDcyIiwiY3VocyI6IjU3OTY2NGIzZWQ3NTJlMDU0N2EyNDJiM2MwNThiZmJiOGM0MWYxNjFhYjdmMjE0ZGUyMDhiMzM2YzY1MzgyNzEifQ.k3cEza89REZ_EtoTaH5gkJaNABhK-A3A7PshXg8iqauj1SpV91HKXRPXvLBokyd4Gh42kq_H_1ZfCgVqwwptOQ",
    "cuc": "po7l089f0pfv"
}
try:
    ua = UserAgent()
except Exception:
    ua = type('UserAgent', (object,), {'random': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'})()


def get_no1_page(question, secondary_intent, user_agent, cookies):
    """
    获取第一页的数据，并从中提取后续请求需要的参数。
    新增了 user_agent 和 cookies 参数。
    """
    headers = {
        "content-type": "application/json",
        "hexin-v": cookies.get('v'),
        "user-agent": user_agent
    }
    url = "https://www.iwencai.com/customized/chart/get-robot-data"
    data = {
        "source": "Ths_iwencai_Xuangu",
        "version": "2.0",
        "query_area": "",
        "block_list": "",
        "add_info": "{\"urp\":{\"scene\":1,\"company\":1,\"business\":1},\"contentType\":\"json\",\"searchInfo\":true}",
        "question": question,
        "perpage": "100",
        "page": 1,
        "secondary_intent": secondary_intent,
        "log_info": "{\"input_type\":\"click\"}",
        "rsh": cookies.get('other_uid')
    }
    perpage = int(data.get("perpage", 100))
    data_str = json.dumps(data, separators=(',', ':'))
    response = requests.post(url, headers=headers, cookies=cookies, data=data_str)
    response.raise_for_status()
    json_data = response.json()
    component = json_data['data']['answer'][0]['txt'][0]['content']['components'][0]
    result_data = component['data']
    meta_extra = result_data['meta']['extra']
    params_for_all_pages = {
        'condition': meta_extra.get('condition'),
        'urp_sort_index': result_data['meta'].get('urp_sort_index'),
        'logid': json_data['data'].get('logid'),
        'sessionid': result_data['meta'].get('sessionid'),
        'iwc_token': meta_extra.get('token'),
        'comp_id': component.get('cid'),
        'uuid': component.get('puuid'),
    }
    first_page_results = result_data.get('datas', [])
    total_count = meta_extra.get('row_count', 0)
    total_pages = math.ceil(total_count / perpage)
    return params_for_all_pages, first_page_results, total_pages


def get_all_page(question, secondary_intent, params, page_num, user_agent, cookies):
    headers = {
        "accept": "application/json, text/plain, */*",
        "hexin-v": cookies.get('v'),
        "user-agent": user_agent
    }
    url = "https://www.iwencai.com/gateway/urp/v7/landing/getDataList"
    data = {
        "query": question,
        "condition": params['condition'],
        "urp_sort_index": params['urp_sort_index'],
        "source": "Ths_iwencai_Xuangu",
        "perpage": "100",
        "page": str(page_num),
        "urp_sort_way": "desc",
        "codelist": "",
        "page_id": "",
        "logid": params['logid'],
        "ret": "json_all",
        "sessionid": params['sessionid'],
        "iwc_token": params['iwc_token'],
        "user_id": cookies.get('other_uid'),
        "uuids[0]": params['uuid'],
        "query_type": secondary_intent,
        "comp_id": params['comp_id'],
        "business_cat": "soniu",
        "uuid": params['uuid']
    }
    response = requests.post(url, headers=headers, cookies=cookies, data=data)
    response.raise_for_status()
    json_data = response.json()
    if json_data and json_data.get('answer'):
        components = json_data['answer'].get('components')
        if components and len(components) > 0:
            data_component = components[0].get('data')
            if data_component:
                return data_component.get('datas', [])
    return []


def fetch_all_data(question, secondary_intent, cookies):
    try:
        v_value = get_v_value()
        if v_value:
            cookies['v'] = v_value
        else:
            print("无法获取 'v' 值，终止执行。")
            return None

        random_user_agent = ua.random
        params, first_page_results, total_pages = get_no1_page(question, secondary_intent, user_agent=random_user_agent, cookies=cookies)
        all_results = first_page_results
        for page_num in range(2, total_pages + 1):
            try:
                page_results = get_all_page(question, secondary_intent, params, page_num, user_agent=random_user_agent, cookies=cookies)
                if page_results:
                    all_results.extend(page_results)
            except Exception as e:
                print(f"Error fetching page {page_num}: {e}")
                continue
        return all_results
    except Exception as e:
        print(f"Error fetching first page: {e}")
        return None

a = 0
if __name__ == "__main__":
    c = {'美股': 'usstock', 'A股': 'stock', '港股': 'hkstock'}
    while True:
        question = random.choice(['阳线，成交量>10万，macd金叉', '成交量>5万，macd金叉', '阳线', '阳线，macd金叉',
                                 'macd金叉'])
        secondary_intent = random.choice(['usstock', 'stock', 'hkstock'])
        all_data = fetch_all_data(question, secondary_intent, request_cookies)
        if all_data:
            a += 1
            print(f"\n成功获取到 {len(all_data)} 条数据。")
        else :
            break
    print(a)