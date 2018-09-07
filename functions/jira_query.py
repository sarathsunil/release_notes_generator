import os
import sys
import json
import requests
import random
import string
import urllib
import logging
from datetime import datetime
sys.path.insert(0, '/webhook_handler/settings')
from urls_all import PROTOCOL
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
def root_dir():  # pragma: no cover
    return os.path.abspath(os.path.dirname(__file__))

#FUNCTION PULL DESCRIPTION/TITLE/RELEASE VERSION PER ISSUE FROM JIRA
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

#FUNCTION TO PULL FIELD ID BY FIELD NAME
def jira_field_id_mapping(field_name,ip,port,session_cookie):
    headers = {
           'connection': "keep-alive",
           'upgrade-insecure-requests': "1",
           'cache-control': "no-cache",
           'content-type': 'application/json',
           'cookie': 'JSESSIONID='+session_cookie
           }
    url = PROTOCOL+(ip)+":"+(str(port))+"/rest/api/2/field"
    response = requests.get(url,headers=headers,verify=False).json()
    field_id = list(filter(lambda x: x['name']==field_name,response))[0]['id']
    return field_id

#FUNCTION TO GET PROJECT NAME BY PROJECT KEY
def jira_get_project_name_by_key(ip,port,project_key,session_cookie):
    headers = {
           'connection': "keep-alive",
           'upgrade-insecure-requests': "1",
           'cache-control': "no-cache",
           'content-type': 'application/json',
           'cookie': 'JSESSIONID='+session_cookie
           }
    url = PROTOCOL+(ip)+":"+(str(port))+"/rest/api/2/project/"+project_key
    response = requests.get(url,headers=headers,verify=False).json()
    return response['name']

#GET ALL VERSIONS OF A PARTICULAR PROJECT
def jira_get_versions_all(IP,PORT,project_id,session_cookie):
    headers = {
           'connection': "keep-alive",
           'upgrade-insecure-requests': "1",
           'cache-control': "no-cache",
           'content-type': 'application/json',
           'cookie': 'JSESSIONID='+session_cookie
           }
    url = PROTOCOL+IP+':'+str(PORT)+'/rest/api/2/project/'+project_id+'/versions/'
    response = requests.get(url,headers=headers,verify=False).json()
    if type(response) is dict and "errorMessages" in response.keys():
       return []
    res = [item['name'] for item in response]
    return res
#GET ALL VERSIONS BETWEEN TWO SPECIFIED VERSION - AFTER START DATE OF FIRST RELEASE MENTIONED AND BEFORE START DATE OF LAST RELEASE
def jira_get_versions(IP,PORT,project_id,start_release,end_release,session_cookie):
    if start_release not in jira_get_versions_all(IP,PORT,project_id,session_cookie):
       return {"errorMessages":["No project could be found with key and Release specified."],"errors":{}}
    if end_release not in jira_get_versions_all(IP,PORT,project_id,session_cookie):
       return {"errorMessages":["No project could be found with key and Release specified."],"errors":{}}
    headers = {
           'connection': "keep-alive",
           'upgrade-insecure-requests': "1",
           'cache-control': "no-cache",
           'content-type': 'application/json',
           'cookie': 'JSESSIONID='+session_cookie
           }
    url = PROTOCOL+IP+':'+str(PORT)+'/rest/api/2/project/'+project_id+'/versions/'
    response = requests.get(url,headers=headers,verify=False).json()

    #SORT BASED ON START DATE OF THE RELEASE
    res = []
    for item in response:
      if 'startDate' in item.keys():
        item['startDate1'] = datetime.strptime(item['startDate'],'%Y-%m-%d')
        res.append(item)
    res = sorted(res, key= lambda k: k['startDate1'])
    res1 = res

    #REMOVE ALL RELEASES THAT COME BEFORE AND INCLUDING START RELEASE: res1
    for release in res:
        if release['name']!= start_release:
           res1.remove(release)
        if release['name']==start_release:
           res1.remove(release)
           break
    res2 = []

    #ADD RELEASES TO res2 UNTIL END RELEASE IS ALSO ADDED
    for release in res1:
        if release['name']!=end_release:
           res2.append(release)
        if release['name'] == end_release:
           res2.append(release)
           break

    #RETURN ONLY RELEASE NAMES
    return [item['name'] for item in res2 if 'name' in item.keys()]

#CHECK FOR UNFINISHED EPICS OR INITIATIVES
def check_undone_epic_intiative(issue_id,project_name,ip,port,session_cookie):
    headers = {
           'connection': "keep-alive",
           'upgrade-insecure-requests': "1",
           'cache-control': "no-cache",
           'content-type': 'application/json',
           'cookie': 'JSESSIONID='+session_cookie
           }
    issue_type_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/issue/'+issue_id+'?fields=issuetype'
    issue_type = requests.get(issue_type_url,headers=headers,verify=False).json()['fields']['issuetype']['name']
    if issue_type=='Task' or issue_type=='Bug':
       undone_epic_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20No%20AND%20project%20%3D%20'+project_name+'%20AND%20issue%20in%20linkedIssues(%22'+issue_id+'%22)%20AND%20issuetype%20!%3D%20Initiatives%20AND%20issuetype%20!%3D%20Epic%20AND%20issuetype%20!%3D%20Story'
    if issue_type=='Story':
       undone_epic_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20No%20AND%20project%20%3D%20'+project_name+'%20AND%20issue%20in%20linkedIssues(%22'+issue_id+'%22)%20AND%20issuetype%20!%3D%20Initiatives%20AND%20issuetype%20!%3D%20Epic'
    if issue_type=='Epic':
       undone_epic_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20No%20AND%20project%20%3D%20'+project_name+'%20AND%20issue%20in%20linkedIssues(%22'+issue_id+'%22)%20AND%20issuetype%20!%3D%20Initiatives'
    undone_epic_response = requests.get(undone_epic_url,headers=headers,verify=False).json()
    if len(undone_epic_response['issues'])!=0:
       return False
    else:
       return True

# RETURNS ALL THE EPICS AND LINKED ISSUES/USER STORIES/MERGED ISSUES ASSOCIATED WITH EPIC IN DONE STATE
def parse_epic_response(epic_response,ip,port,session_cookie,release_tag,project_name):
    epic_description=[]
    story_description=[]
    task_description=[]
    bug_description=[]
    merged_description =[]
    epic_issue_id = []
    story_issue_id = []
    task_issue_id = []
    bug_issue_id = []
    merged_issue_id = []
    internal_issue_id = []
    for epic in epic_response['issues']:
        retain_epic = {'issue_id':epic['key'],'summary':epic['fields']['summary'],'description':epic['fields']['description'],'link':None,'label':epic['fields']['labels']}
        epic_issue_id.append(epic['key'])
        epic_description.append(retain_epic)
    headers = {
           'connection': "keep-alive",
           'upgrade-insecure-requests': "1",
           'cache-control': "no-cache",
           'content-type': 'application/json',
           'cookie': 'JSESSIONID='+session_cookie
           }
    for issues in epic_response['issues']:
         story_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20Yes%20AND%20fixVersion%20%3D%20'+release_tag+'%20AND%20project%20%3D%20'+project_name+'%20AND%20issuetype%20%3D%20Story%20AND%20%22Epic%20Link%22%20%3D%20'+issues['id']
         task_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20Yes%20AND%20fixVersion%20%3D%20'+release_tag+'%20AND%20project%20%3D%20'+project_name+'%20AND%20issuetype%20%3D%20Task%20AND%20%22Epic%20Link%22%20%3D%20'+issues['id']
         bug_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20Yes%20AND%20fixVersion%20%3D%20'+release_tag+'%20AND%20project%20%3D%20'+project_name+'%20AND%20issuetype%20%3D%20Bug%20AND%20%22Epic%20Link%22%20%3D%20'+issues['id']
         story_response = requests.get(story_url,headers=headers,verify=False).json()
         task_response = requests.get(task_url,headers=headers,verify=False).json()
         bug_response = requests.get(task_url,headers=headers,verify=False).json()
         responses = epic_response['issues']+story_response['issues']+task_response['issues']+bug_response['issues']

         #CHECK IF ISSUE IS MERGED - ADD TO MERGED ISSUES INSTEAD
         for item in responses:
             if(("Merged" in item['fields']['labels']) and (item['key'] not in merged_issue_id)):
                 retain_merged = {'issue_id':item['key'],'summary':item['fields']['summary'],'description':item['fields']['description'],'link':issues['id'],'label':item['fields']['labels']}
                 merged_issue_id.append(item['key'])
                 merged_description.append(retain_merged)
         for story in story_response['issues']:
             retain_story = {'issue_id':story['key'],'summary':story['fields']['summary'],'description':story['fields']['description'],'link':issues['id'],'label':story['fields']['labels']}
             story_issue_id.append(story['key'])
             story_description.append(retain_story)
         for task in task_response['issues']:
             retain_task = {'issue_id':task['key'],'summary':task['fields']['summary'],'description':task['fields']['description'],'link':issues['id'],'label':task['fields']['labels']}
             task_issue_id.append(task['key'])
             task_description.append(retain_task)
         for bug in bug_response['issues']:
             retain_bug = {'issue_id':bug['key'],'summary':bug['fields']['summary'],'description':bug['fields']['description'],'link':issues['id'],'label':bug['fields']['labels']}
             bug_issue_id.append(bug['key'])
             bug_description.append(retain_bug)
    bug_description = [item for item in bug_description if item['issue_id'] not in merged_issue_id]
    task_description = [item for item in task_description if item['issue_id'] not in merged_issue_id]
    epic_description = [item for item in epic_description if item['issue_id'] not in merged_issue_id]
    story_description = [item for item in story_description if item['issue_id'] not in merged_issue_id]
    #initiative_description = [item for item in initiative_description if item not in merged_description]
    return {"EPICS":epic_description,"STORIES":story_description,"TASKS":task_description,"BUGS":bug_description,"MERGED_ISSUE":merged_description,"ISSUE_IDS":epic_issue_id+story_issue_id+task_issue_id+bug_issue_id}

# RETURNS ALL THE INITIATIVES AND LINKED EPICS/USER STORIES/MERGED ISSUES ASSOCIATED WITH INITIATIVES IN DONE STATE
def parse_initiative_response(initiative_response,ip,port,session_cookie,release_tag,project_name):
    initiative_description = []
    epic_description = []
    story_description=[]
    task_description=[]
    bug_description=[]
    merged_description=[]
    initiative_issue_id = []
    epic_issue_id = []
    story_issue_id = []
    task_issue_id = []
    bug_issue_id = []
    merged_issue_id = []
    for initiative in initiative_response['issues']:
        retain_initiative = {'issue_id':initiative['key'],'summary':initiative['fields']['summary'],'description':initiative['fields']['description'],'link':None,'label':initiative['fields']['labels']}
        initiative_issue_id.append(initiative['key'])
        initiative_description.append(retain_initiative)
    headers = {
           'connection': "keep-alive",
           'upgrade-insecure-requests': "1",
           'cache-control': "no-cache",
           'content-type': 'application/json',
           'cookie': 'JSESSIONID='+session_cookie
           }
    for issues in initiative_response['issues']:
         story_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20Yes%20AND%20fixVersion%20%3D%20'+release_tag+'%20AND%20project%20%3D%20'+project_name+'%20AND%20issuetype%20%3D%20Story%20AND%20issue%20in%20linkedIssues(%22'+issues['id']+'%22)'
         task_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20Yes%20AND%20fixVersion%20%3D%20'+release_tag+'%20AND%20project%20%3D%20'+project_name+'%20AND%20issuetype%20%3D%20Task%20AND%20issue%20in%20linkedIssues(%22'+issues['id']+'%22)'
         bug_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20Yes%20AND%20fixVersion%20%3D%20'+release_tag+'%20AND%20project%20%3D%20'+project_name+'%20AND%20issuetype%20%3D%20Bug%20AND%20issue%20in%20linkedIssues(%22'+issues['id']+'%22)'
         epic_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20Yes%20AND%20fixVersion%20%3D%20'+release_tag+'%20AND%20project%20%3D%20'+project_name+'%20AND%20issuetype%20%3D%20Epic%20AND%20issue%20in%20linkedIssues(%22'+issues['id']+'%22)'
         epic_response = requests.get(epic_url,headers=headers,verify=False).json()
         story_response = requests.get(story_url,headers=headers,verify=False).json()
         task_response = requests.get(task_url,headers=headers,verify=False).json()
         bug_response = requests.get(task_url,headers=headers,verify=False).json()
         responses = epic_response['issues']+story_response['issues']+task_response['issues']+bug_response['issues']+initiative_response['issues']

         #CHECK IF ISSUE IS MERGED - ADD TO MERGED ISSUES INSTEAD
         for item in responses:
             if(("Merged" in item['fields']['labels']) and (item['key'] not in merged_issue_id)):
                 retain_merged = {'issue_id':item['key'],'summary':item['fields']['summary'],'description':item['fields']['description'],'link':issues['id'],'label':item['fields']['labels']}
                 merged_issue_id.append(item['key'])
                 merged_description.append(retain_merged)
         for epic in epic_response['issues']:
             retain_epic = {'issue_id':epic['key'],'summary':epic['fields']['summary'],'description':epic['fields']['description'],'link':issues['id'],'label':epic['fields']['labels']}
             epic_issue_id.append(epic['key'])
             epic_description.append(retain_epic)
         for story in story_response['issues']:
             retain_story = {'issue_id':story['key'],'summary':story['fields']['summary'],'description':story['fields']['description'],'link':issues['id'],'label':story['field']['labels']}
             story_issue_id.append(story['key'])
             story_description.append(retain_story)
         for task in task_response['issues']:
             retain_task = {'issue_id':task['key'],'summary':task['fields']['summary'],'description':task['fields']['description'],'link':issues['id'],'label':task['fields']['labels']}
             task_issue_id.append(task['key'])
             task_description.append(retain_task)
         for bug in bug_response['issues']:
             retain_bug = {'issue_id':bug['key'],'summary':bug['fields']['summary'],'description':bug['fields']['description'],'link':issues['id'],'label':bug['fields']['labels']}
             bug_issue_id.append(bug['key'])
             bug_description.append(retain_bug)
    bug_description = [item for item in bug_description if item['issue_id'] not in merged_issue_id]
    task_description = [item for item in task_description if item['issue_id'] not in merged_issue_id]
    epic_description = [item for item in epic_description if item['issue_id'] not in merged_issue_id]
    story_description = [item for item in story_description if item['issue_id'] not in merged_issue_id]
    initiative_description = [item for item in initiative_description if item['issue_id'] not in merged_issue_id]
    return {"INITIATIVES":initiative_description,"EPICS":epic_description,"STORIES":story_description,"TASKS":task_description,"BUGS":bug_description,"MERGED_ISSUE":merged_description,"ISSUE_IDS": initiative_issue_id+epic_issue_id+story_issue_id+task_issue_id+bug_issue_id+epic_issue_id+initiative_issue_id}

# RETURNS ALL THE USER STORIES AND LINKED USER STORIES/TASKS/MERGED ISSUES ASSOCIATED WITH USER STORIES IN DONE STATE
def parse_story_response(story_response,ip,port,session_cookie,release_tag,project_name):
    story_description=[]
    task_description=[]
    bug_description=[]
    merged_description=[]
    story_issue_id = []
    task_issue_id = []
    bug_issue_id = []
    merged_issue_id = []
    for story in story_response['issues']:
        retain_story = {'issue_id':story['key'],'description':story['fields']['description'],'link':None,'label':story['fields']['labels']}
        story_issue_id.append(story['key'])
        story_description.append(retain_story)
    headers = {
           'connection': "keep-alive",
           'upgrade-insecure-requests': "1",
           'cache-control': "no-cache",
           'content-type': 'application/json',
           'cookie': 'JSESSIONID='+session_cookie
           }
    for issues in story_response['issues']:
         task_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20Yes%20AND%20fixVersion%20%3D%20'+release_tag+'%20AND%20project%20%3D%20'+project_name+'%20AND%20issuetype%20%3D%20Task%20AND%20issue%20in%20linkedIssues(%22'+issues['id']+'%22)'
         bug_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20Yes%20AND%20fixVersion%20%3D%20'+release_tag+'%20AND%20project%20%3D%20'+project_name+'%20AND%20issuetype%20%3D%20Bug%20AND%20issue%20in%20linkedIssues(%22'+issues['id']+'%22)'
         task_response = requests.get(task_url,headers=headers,verify=False).json()
         bug_response = requests.get(task_url,headers=headers,verify=False).json()
         responses = task_response['issues']+bug_response['issues']+story_response['issues']

         #CHECK IF ISSUE IS MERGED - ADD TO MERGED ISSUES INSTEAD
         for item in responses:
             if(("Merged" in item['fields']['labels']) and (item['key'] not in merged_issue_id)):
                 retain_merged = {'issue_id':item['key'],'summary':item['fields']['summary'],'description':item['fields']['description'],'link':issues['id'],'label':item['fields']['labels']}
                 merged_issue_id.append(item['key'])
                 merged_description.append(retain_merged)
         for task in task_response['issues']:
             retain_task = {'issue_id':task['key'],'summary':task['fields']['summary'],'description':task['fields']['description'],'link':issues['id'],'label':task['fields']['labels']}
             task_issue_id.append(task['key'])
             task_description.append(retain_task)
         for bug in bug_response['issues']:
             retain_bug = {'issue_id':bug['key'],'summary':bug['fields']['summary'],'description':bug['fields']['description'],'link':issues['id'],'label':bug['fields']['labels']}
             bug_issue_id.append(bug['key'])
             bug_description.append(retain_bug)
    bug_description = [item for item in bug_description if item['issue_id'] not in merged_issue_id]
    task_description = [item for item in task_description if item['issue_id'] not in merged_issue_id]
    story_description = [item for item in story_description if item['issue_id'] not in merged_issue_id]
    return {"STORIES":story_description,"TASKS":task_description,"BUGS":bug_description,"MERGED_ISSUE":merged_description,"ISSUE_IDS": story_issue_id+task_issue_id+bug_issue_id+merged_issue_id}

# RETURNS ALL THE TASKS AND LINKED ISSUES/BUGS ASSOCIATED WITH TASKS IN DONE STATE
def parse_task_response(task_response,ip,port,session_cookie,release_tag,project_name):
    task_description=[]
    bug_description=[]
    merged_description=[]
    task_issue_id=[]
    bug_issue_id=[]
    merged_issue_id=[]
    for task in task_response['issues']:
        retain_task = {'issue_id':task['key'],'summary':task['fields']['summary'],'description':task['fields']['description'],'link':None,'label':task['fields']['labels']}
        task_issue_id.append(task['key'])
        task_description.append(retain_task)
    headers = {
           'connection': "keep-alive",
           'upgrade-insecure-requests': "1",
           'cache-control': "no-cache",
           'content-type': 'application/json',
           'cookie': 'JSESSIONID='+session_cookie
           }
    for issues in task_response['issues']:
        bug_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20Yes%20AND%20fixVersion%20%3D%20'+release_tag+'%20AND%20project%20%3D%20'+project_name+'%20AND%20issuetype%20%3D%20Bug%20AND%20issue%20in%20linkedIssues(%22'+issues['id']+'%22)'
        bug_response = requests.get(bug_url,headers=headers,verify=False).json()
        responses = task_response['issues']+bug_response['issues']

        #CHECK IF ISSUE IS MERGED - ADD TO MERGED ISSUES INSTEAD
        for item in responses:
             if(("Merged" in item['fields']['labels']) and (item['key'] not in merged_issue_id)):
                 retain_merged = {'issue_id':item['key'],'summary':item['fields']['summary'],'description':item['fields']['description'],'link':issues['id'],'label':item['fields']['labels']}
                 merged_issue_id.append(item['key'])
                 merged_description.append(retain_merged)
        for bug in bug_response['issues']:
             retain_bug = {'issue_id':bug['key'],'summary':bug['fields']['summary'],'description':bug['fields']['description'],'link':issues['id'],'label':bug['fields']['labels']}
             bug_issue_id.append(bug['key'])
             bug_description.append(retain_bug)
    bug_description = [item for item in bug_description if item['issue_id'] not in merged_issue_id]
    task_description = [item for item in task_description if item['issue_id'] not in merged_issue_id]
    return {"TASKS":task_description,"BUGS":bug_description,"MERGED_ISSUE":merged_description,"ISSUE_IDS":task_issue_id+bug_issue_id+merged_issue_id}

# RETURNS ALL THE BUGS AND LINKED ISSUES/TASKS/MERGED ISSUES ASSOCIATED WITH BUGS IN DONE STATE
def parse_bug_response(bug_response,ip,port,session_cookie,release_tag,project_name):
    task_description=[]
    bug_description=[]
    merged_description = []
    task_issue_id = []
    bug_issue_id = []
    merged_issue_id = []
    for bug in bug_response['issues']:
        retain_bug = {'issue_id':bug['key'],'summary':bug['fields']['summary'],'description':bug['fields']['description'],'link':None,'label':bug['fields']['labels']}
        bug_issue_id.append(bug['key'])
        bug_description.append(retain_bug)
    headers = {
           'connection': "keep-alive",
           'upgrade-insecure-requests': "1",
           'cache-control': "no-cache",
           'content-type': 'application/json',
           'cookie': 'JSESSIONID='+session_cookie
           }
    for issues in bug_response['issues']:
        task_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20Yes%20AND%20fixVersion%20%3D%20'+release_tag+'%20AND%20project%20%3D%20'+project_name+'%20AND%20issuetype%20%3D%20Task%20AND%20issue%20in%20linkedIssues(%22'+issues['id']+'%22)'
        task_response = requests.get(task_url,headers=headers,verify=False).json()
        responses = task_response['issues']+bug_response['issues']

        #CHECK IF ISSUE IS MERGED - ADD TO MERGED ISSUES INSTEAD
        for item in responses:
             if(("Merged" in item['fields']['labels']) and (item['key'] not in merged_issue_id)):
                 retain_merged = {'issue_id':item['key'],'summary':item['fields']['summary'],'description':item['fields']['description'],'link':issues['id'],'label':item['fields']['labels']}
                 merged_issue_id.append(item['key'])
                 merged_description.append(retain_merged)
        for task in task_response['issues']:
             retain_task = {'issue_id':task['key'],'summary':task['fields']['summary'],'description':task['fields']['description'],'link':issues['id'],'label':task['fields']['labels']}
             task_issue_id.append(task['key'])
             task_description.append(retain_task)
    task_description = [item for item in task_description if item['issue_id'] not in merged_issue_id]
    bug_description = [item for item in bug_description if item['issue_id'] not in merged_issue_id]
    return {"TASKS":task_description,"BUGS":bug_description,"MERGED_ISSUE":merged_description,"ISSUE_IDS":task_issue_id+bug_issue_id}

#RETURNS ALL BUGS IN UNFINISHED STATE
def parse_bug_undone_response(bug_undone_response,ip,port,session_cookie,release_tag,project_name):
    bug_undone_copy = bug_undone_response
    task_description=[]
    bug_description=[]
    merged_description=[]
    task_issue_id = []
    bug_issue_id = []
    merged_issue_id = []
    for bug in bug_undone_copy['issues']:

        #CHECK IF ISSUE IS MERGED - ADD TO MERGED ISSUES INSTEAD OF BUGS
        if(("Merged" in bug['fields']['labels']) and (bug['key'] not in merged_issue_id)):
            #bug_undone_response['issues'].remove(bug)
            retain_merged = {'issue_id':bug['key'],'summary':bug['fields']['summary'],'description':bug['fields']['description'],'link':bug['id'],'label':bug['fields']['labels']}
            merged_issue_id.append(bug['key'])
            merged_description.append(retain_merged)

        retain_bug = {'issue_id':bug['key'],'summary':bug['fields']['summary'],'description':bug['fields']['description'],'link':bug['id'],'label':bug['fields']['labels']}
        bug_issue_id.append(bug['key'])
        bug_description.append(retain_bug)
    bug_description = [item for item in bug_description if item['issue_id'] not in merged_issue_id]
    headers = {
           'connection': "keep-alive",
           'upgrade-insecure-requests': "1",
           'cache-control': "no-cache",
           'content-type': 'application/json',
           'cookie': 'JSESSIONID='+session_cookie
           }
    return {"BUGS_UNDONE":bug_description,"MERGED_ISSUE":merged_description,"ISSUE_IDS":bug_issue_id}

# RETURNS ALL INITIATIVES/EPICS/USER STORIES/TASKS/BUGS ETC IN DONE STATE - FOR A GIVEN RELEASE
def jira_release_tag_look_up(ip,port,session_cookie,project_name,release_tag,customer_description_id,internal_flag):
     headers = {
           'connection': "keep-alive",
           'upgrade-insecure-requests': "1",
           'cache-control': "no-cache",
           'content-type': 'application/json',
           'cookie': 'JSESSIONID='+session_cookie
           }
     #JQL URLS FOR EACH TYPE OF ISSUE
     epic_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20Yes%20AND%20fixVersion%20%3D%20'+release_tag+'%20AND%20project%20%3D%20'+project_name+'%20AND%20issuetype%20%3D%20Epic'
     initiative_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20Yes%20AND%20fixVersion%20%3D%20'+release_tag+'%20AND%20project%20%3D%20'+project_name+'%20AND%20issuetype%20%3D%20Initiatives'
     story_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20Yes%20AND%20fixVersion%20%3D%20'+release_tag+'%20AND%20project%20%3D%20'+project_name+'%20AND%20issuetype%20%3D%20Story'
     task_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20Yes%20AND%20fixVersion%20%3D%20'+release_tag+'%20AND%20project%20%3D%20'+project_name+'%20AND%20issuetype%20%3D%20Task'
     bug_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20Yes%20AND%20fixVersion%20%3D%20'+release_tag+'%20AND%20project%20%3D%20'+project_name+'%20AND%20issuetype%20%3D%20Bug'
     bug_undone_url = PROTOCOL+ip+':'+str(port)+'/rest/api/2/search?jql=%22Release%20Included%22%20%3D%20No%20AND%20project%20%3D%20'+project_name+'%20AND%20issuetype%20%3D%20Bug'

     #GET RESPONSE FOR EACH ISSUE TYPE FOR A GIVEN RELEASE TAG
     epic_response = requests.get(epic_url,headers=headers,verify=False).json()
     initiative_response = requests.get(initiative_url,headers=headers,verify=False).json()
     story_response = requests.get(story_url,headers=headers,verify=False).json()
     task_response = requests.get(task_url,headers=headers,verify=False).json()
     bug_response = requests.get(bug_url,headers=headers,verify=False).json()
     bug_undone_response = requests.get(bug_undone_url,headers=headers,verify=False).json()

     #DICT FOR RETENTION - KEYS ARE ISSUE TYPE (STORY,TASK,EPIC,INITIATIVE)
     return_dict = {"INITIATIVE":parse_initiative_response(initiative_response,ip,port,session_cookie,release_tag,project_name), "EPIC":parse_epic_response(epic_response,ip,port,session_cookie,release_tag,project_name), "STORY":parse_story_response(story_response,ip,port,session_cookie,release_tag,project_name), "TASK":parse_task_response(task_response,ip,port,session_cookie,release_tag,project_name),"BUG":parse_bug_response(task_response,ip,port,session_cookie,release_tag,project_name),"BUG_UNDONE":parse_bug_undone_response(bug_undone_response,ip,port,session_cookie,release_tag,project_name)}

     #GET ALL ASSOCIATED ISSUES OF AN INITIATIVE GROUPED IN ISSUE TYPE

     #CHECK IF ANY TRACKERS UNDER THE INITIATIVE/EPIC/STORY - IS NOT DONE - THEN REMOVE INITIATIVE/EPIC/STORY
     for item in return_dict["INITIATIVE"]["INITIATIVES"]:
         if check_undone_epic_intiative(item['issue_id'],project_name,ip,port,session_cookie)==False:
            return_dict["INITIATIVE"]["INITIATIVES"].remove(item)
     for item in return_dict["INITIATIVE"]["EPICS"]:
         if check_undone_epic_intiative(item['issue_id'],project_name,ip,port,session_cookie)==False:
            return_dict["INITIATIVE"]["EPICS"].remove(item)
     for item in return_dict["EPIC"]["EPICS"]:
         if check_undone_epic_intiative(item['issue_id'],project_name,ip,port,session_cookie)==False:
            return_dict["EPIC"]["EPICS"].remove(item)
     for item in return_dict["EPIC"]["STORIES"]:
         if check_undone_epic_intiative(item['issue_id'],project_name,ip,port,session_cookie)==False:
            return_dict["EPIC"]["STORIES"].remove(item)
     for item in return_dict["STORY"]["STORIES"]:
         if check_undone_epic_intiative(item['issue_id'],project_name,ip,port,session_cookie)==False:
            return_dict["STORY"]["STORIES"].remove(item)

     #GET MERGED ISSUES PER ISSUE TYPE AND ADD TO MERGED ISSUES LIST
     return_dict["EPIC"]["MERGED_ISSUE"] = [item for item in return_dict["EPIC"]["MERGED_ISSUE"] if item['issue_id'] not in return_dict["INITIATIVE"]["ISSUE_IDS"]]
     return_dict["STORY"]["MERGED_ISSUE"] = [item for item in return_dict["STORY"]["MERGED_ISSUE"] if item['issue_id'] not in return_dict["EPIC"]["ISSUE_IDS"]]
     return_dict["TASK"]["MERGED_ISSUE"] = [item for item in return_dict["TASK"]["MERGED_ISSUE"] if item['issue_id'] not in return_dict["STORY"]["ISSUE_IDS"]]
     return_dict["BUG"]["MERGED_ISSUE"] = [item for item in return_dict["BUG"]["MERGED_ISSUE"] if item['issue_id'] not in return_dict["TASK"]["ISSUE_IDS"]]

     #REMOVE INTERNAL ITEMS IF USER GENERATING  EXTERNAL REPORT

     if internal_flag in ["external","External"]:
        return_dict["INITIATIVE"]["INITIATIVES"] = [item for item in return_dict["INITIATIVE"]["INITIATIVES"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
        return_dict["INITIATIVE"]["EPICS"] = [item for item in return_dict["INITIATIVE"]["EPICS"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
        return_dict["INITIATIVE"]["STORIES"] = [item for item in return_dict["INITIATIVE"]["STORIES"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
        return_dict["INITIATIVE"]["TASKS"] = [item for item in return_dict["INITIATIVE"]["TASKS"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
        return_dict["INITIATIVE"]["BUGS"] = [item for item in return_dict["INITIATIVE"]["BUGS"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
        return_dict["INITIATIVE"]["MERGED_ISSUE"] = [item for item in return_dict["INITIATIVE"]["MERGED_ISSUE"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
        return_dict["EPIC"]["EPICS"] = [item for item in return_dict["EPIC"]["EPICS"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
        return_dict["EPIC"]["STORIES"] = [item for item in return_dict["EPIC"]["STORIES"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
        return_dict["EPIC"]["TASKS"] = [item for item in return_dict["EPIC"]["TASKS"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
        return_dict["EPIC"]["BUGS"] = [item for item in return_dict["EPIC"]["BUGS"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
        return_dict["EPIC"]["MERGED_ISSUE"] = [item for item in return_dict["EPIC"]["MERGED_ISSUE"] if ("internal" not in item['label'] and "Internal" not in item['label'])]

        return_dict["STORY"]["STORIES"] = [item for item in return_dict["STORY"]["STORIES"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
        return_dict["STORY"]["TASKS"] = [item for item in return_dict["STORY"]["TASKS"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
        return_dict["STORY"]["BUGS"] = [item for item in return_dict["STORY"]["BUGS"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
        return_dict["STORY"]["MERGED_ISSUE"] = [item for item in return_dict["STORY"]["MERGED_ISSUE"] if ("internal" not in item['label'] and "Internal" not in item['label'])]

        return_dict["TASK"]["TASKS"] = [item for item in return_dict["TASK"]["TASKS"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
        return_dict["TASK"]["BUGS"] = [item for item in return_dict["TASK"]["BUGS"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
        return_dict["TASK"]["MERGED_ISSUE"] = [item for item in return_dict["TASK"]["MERGED_ISSUE"] if ("internal" not in item['label'] and "Internal" not in item['label'])]

        return_dict["BUG"]["TASKS"] = [item for item in return_dict["BUG"]["TASKS"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
        return_dict["BUG"]["BUGS"] = [item for item in return_dict["BUG"]["BUGS"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
        return_dict["BUG"]["MERGED_ISSUE"] = [item for item in return_dict["BUG"]["MERGED_ISSUE"] if ("internal" not in item['label'] and "Internal" not in item['label'])]
     
     #RETURN DATA
     return return_dict

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
    os.system(curl_string+' >'+root_dir()+'/curl_out')
    try:
       return open(root_dir()+'/curl_out','r').read().split('\n')[0].split()[1]
    except IndexError:
       return 404
    #filename_out = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(20))
    #os.system("cat /tmp/curl_writer | /bin/bash > /tmp/"+filename_out)
    #return open('/tmp/'+filename_out,'r').read().split('\n')[0].split()[1]

