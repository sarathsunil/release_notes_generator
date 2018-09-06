import os
import sys
import json
import requests
import random
import string
import urllib
#ACCESS_TOKEN = 'jvf_XerGPuvnB3DEzWbk'
#URL = 'http://ec2-52-37-43-131.us-west-2.compute.amazonaws.com/api/v4/projects/4/repository/commits?ref_name=feature_branch_1&private_token='+ACCESS_TOKEN
def get_commit_messages(project_id,ref_name,access_token,gitlab_repo_url):
    headers = {
              'connection': "keep-alive",
              'upgrade-insecure-requests': "1",
              'cache-control': "no-cache",
              'content-type': 'application/json'
              }
    response = requests.request('GET',gitlab_repo_url+'/api/v4/projects/'+project_id+'/repository/commits?ref_name='+ref_name+'&private_token='+access_token,headers=headers).json()
    messages = map(lambda x: x['message'],response)
    return messages

