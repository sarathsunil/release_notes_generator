import os
import sys
import json
import requests
import random
import string
import urllib
def jira_query_pull(issues_url,session_cookie):
    headers = {
           'connection': "keep-alive",
           'upgrade-insecure-requests': "1",
           'cache-control': "no-cache",
           'content-type': 'application/json',
           'cookie': 'JSESSIONID='+session_cookie
           }
    response = requests.get(issues_url, headers=headers, verify=False).json()
    project_id = str(response['fields']['project']['id'])
    title = response['fields']['summary']
    description = response['fields'][customer_description_id]
    release_tag = response['fields'][release_tag_id]
    return {"project_id":project_id,"title":title,"description":description,"release_tag":release_tag}
def jira_field_id_mapping(field_name,issue_id,ip,port,session_cookie):
    headers = {
           'connection': "keep-alive",
           'upgrade-insecure-requests': "1",
           'cache-control': "no-cache",
           'content-type': 'application/json',
           'cookie': 'JSESSIONID='+session_cookie
           }
    url = "http://"+(ip)+":"+(str(port))+"/rest/api/2/issue/"+issue_id+"/editmeta"
    response = requests.get(url,headers=headers,verify=False).json()
    for item in response['fields'].keys():
      if response['fields'][item]['name'] == field_name:
         return item

def jira_release_tag_look_up(ip,port,session_cookie,project_name,release_tag,customer_description_id):
     headers = {
           'connection': "keep-alive",
           'upgrade-insecure-requests': "1",
           'cache-control': "no-cache",
           'content-type': 'application/json',
           'cookie': 'JSESSIONID='+session_cookie
           }
     url = 'http://'+ip+':'+str(port)+'/rest/api/2/search?jql=%22Code%20Integration%22%20%3D%20Yes%20AND%20%22Release%20Tag%22%20~%20'+release_tag+'%20AND%20project%20%3D%20'+project_name
     #url = 'http://'+ip+':'+str(port)+'/rest/api/2/search?jql=%22Code%20Integration%22%20%3D%20Yes%20AND%20%22Release%20Tag%22%20~%20'+release_tag


     response = requests.get(url,headers=headers,verify=False).json()
     #jira_customer_description = reduce(lambda x,y: str(x[customer_description_id])+"\n|###|"+str(y[customer_description_id]) if y[customer_description_id] != None, response['issues'])
     jira_list = []
     for item in response['issues']:
          retain = {'issue_id':item['key'],'customer_description':''}
          if item['fields'][customer_description_id] != None:
             retain['customer_description'] = item['fields'][customer_description_id]
             jira_list.append(retain)
     jira_customer_description = """"""
     for item in jira_list:
          jira_customer_description= jira_customer_description+"<h3>ISSUE ID : "+item['issue_id'] + "</h3></p><p>"
          jira_customer_description= jira_customer_description+"<h3>DESCRIPTION : </h3> "+item['customer_description'] + "</p><p>"
          jira_customer_description= jira_customer_description+"</p><p>"
     return jira_customer_description      

def jira_validate(issue_url,session_cookie):
    headers = {
           'connection': "keep-alive",
           'upgrade-insecure-requests': "1",
           'cache-control': "no-cache",
           'content-type': 'application/json',
           'cookie': 'JSESSIONID='+session_cookie
           }
    response = requests.get(issue_url, headers=headers, verify=False).json()
    status = str(response['fields']['status'])
    return status

def jira_query_update(username,password,field_id,ip,port,issue_id):
    # headers = {
    #         'connection': "keep-alive",
    #         'upgrade-insecure-requests': "1",
    #         'cache-control': "no-cache",
    #         'content-type': 'application/json',
    #         'cookie': 'JSESSIONID='+session_cookie
    #         }
    # data = json.dumps({"fields":{field_id:[{"value":"Yes"}]}})
    # response = requests.request('PUT', issues_url, data=data, headers=headers,verify=False)
    # return response.status_code
    curl_string = r"""curl -D- -u 'myusername:mypassword' -X PUT --data "{\"fields\":{\"my_field_id\":{\"value\" : \"Yes\"}}}" -H "Content-Type: application/json" http://my_jira_ip:my_jira_port/rest/api/latest/issue/my_issue_id/"""
    curl_string = curl_string.replace('myusername',username)
    curl_string = curl_string.replace('mypassword',password)
    curl_string = curl_string.replace('my_field_id',field_id)
    curl_string = curl_string.replace('my_jira_ip',ip)
    curl_string = curl_string.replace('my_jira_port',str(port))
    curl_string = curl_string.replace('my_issue_id',issue_id)
    os.system('sudo '+curl_string+' >curl_out')
    try:
       return open('/home/curl_out','r').read().split('\n')[0].split()[1]
    except IndexError:
       return 404
    #filename_out = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))
    #os.system("cat /tmp/curl_writer | /bin/bash > /tmp/"+filename_out)
    #return open('/tmp/'+filename_out,'r').read().split('\n')[0].split()[1]
