# -*- encoding: utf-8 -*-
'''
@File    :   monitor_test.py
@Time    :   2021/10/20 11:57:03
@Version :   1.0
@Desc    :   test webhook url: 
                https://open.larksuite.com/open-apis/bot/v2/hook/4e58cd69-5fd2-48dd-931c-e489ee5beffa

            

'''

import requests
import json

url = "https://open.larksuite.com/open-apis/bot/v2/hook/4e58cd69-5fd2-48dd-931c-e489ee5beffa"

header = {
    "Content-Type": "application/json"
}
params ={
    "msg_type":"text",
    "content":{
        "text":"价格通知"
    }
}

data = requests.post(url, headers=header,data=json.dumps(params))
print(data.json())
