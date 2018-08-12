import os
import sys
import requests
import json
def get_session_cookie(username,password,url):
    payload = json.dumps({'username':username,'password':password})
    headers = {
           'connection': "keep-alive",
           'upgrade-insecure-requests': "1",
           'cache-control': "no-cache",
           'content-type': 'application/json'
           }
    response = requests.request("POST", url, data=payload, headers=headers, verify=False)
    try:
       res = response.json()

       if res["session"]["name"] == "JSESSIONID":
          jsessionid = res["session"]["value"]
          return {"JSESSIONID":jsessionid,"values": True}
       else:
          return {"JSESSIONID":"kajldbalidbjwilablujk", "values":False}
    except:
       return {"JSESSIONID":"kajldbalidbjwilablujk", "values":response.text}
