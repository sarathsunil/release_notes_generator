#!usr/bin/python
import json
import jinja2
import os,sys
import codecs
import pdfkit
from flask import Flask, jsonify, render_template, url_for
import weasyprint
from flask import abort
from flask import make_response
from flask import request, Response, redirect, flash
import logging
import glob
import requests
from settings.credentials import JIRA_USERNAME as JIRA_USERNAME,JIRA_PASSWORD as JIRA_PASSWORD
from settings.credentials import GITLAB_TOKEN as GITLAB_ACCESS_TOKEN
from settings.urls_all import JIRA as JIRA_IP, GITLAB as GITLAB_IP, PROTOCOL as PROTOCOL
from settings.ports_all import JIRA as JIRA_PORT, GITLAB as GITLAB_PORT
from settings.jira_fields import customer_description as CUSTOMER_DESCRIPTION
from settings.jira_fields import release_tag as RELEASE_TAG
from settings.jira_fields import code_integration as CODE_INTEGRATION
from functions.authorization import get_session_cookie
from functions.html_renderer import html_parse
from functions.jira_query import jira_query_pull,jira_validate,jira_query_update,jira_field_id_mapping,jira_release_tag_look_up,jira_get_versions,jira_get_project_name_by_key, jira_get_versions_all
from functions.gitlab_query import get_commit_messages
from functions.none_checker import check_for_none
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
application = Flask(__name__)
application.secret_key = 'sjhdfvbkuydfvawadda'

#HELPER FUNCTIONS
def root_dir():
    return os.path.abspath(os.path.dirname(__file__))

def get_latest_releasenotes():
    try:

        directory = root_dir()+'/data/'
        files = os.listdir(root_dir()+'/data/')
        name_n_timestamp = dict([(x, os.stat(directory+x).st_mtime) for x in files])
        newest= max(name_n_timestamp, key=lambda k: name_n_timestamp.get(k))
        return open(root_dir()+'/data/'+newest,'r').read()
    except IOError as exc:
        return str(exc)

def get_releasenotes(release_note_name):
    filename = root_dir()+'/data/'+release_note_name
    return open(filename,'r').read()

def make_pdf_report(filepath,pdf_report_path):
        options = {
            'zoom': 0.7,
            'margin-top': '15mm',
            'margin-bottom': '20mm',
            'margin-right': '5mm',
            'margin-left': '5mm',
            'page-height':'100000mm'
        }

        if sys.platform in ('linux', 'linux2'):
            # pdfkit uses wkhtmltopdf, which doesn't work on headless servers;
            # recommended workaround is to use xvfb, as documented here:
            # https://github.com/wkhtmltopdf/wkhtmltopdf/issues/2037#issuecomment-62019521
            from xvfbwrapper import Xvfb
            logger.info('Running pdfkit inside xvfb wrapper')
            with Xvfb():
                pdfkit.from_file(filepath,pdf_report_path, options=options)


#ROUTING SERVICES AND ERROR HANDLING

@application.route('/')
def home():
    return render_template('home.html')

@application.route('/regenerate')
def regenerate():
    return render_template('generate.html')

@application.route('/regenerateCombined')
def regenerate_combined():
    return render_template('generate-combined.html')

@application.route('/generate_combined_error')
def regenerate_combined_error():
    return render_template('generate-error-combined.html')

@application.route('/lookUp')
def look_up():
    return render_template('lookup.html')

@application.route('/lookUpCombined')
def look_up_combined():
    return render_template('lookup-combined.html')

@application.route('/lookup_combined_error')
def look_up_combined_error():
    return render_template('lookup-combined-error.html')

@application.route('/getPdf')
def get_pdf():
    return render_template('get-pdf.html')

@application.route('/getPdfCombined')
def get_pdf_combined():
    return render_template('get-pdf-combined.html')

@application.route('/pdf_combined_error')
def get_pdf_combined_error():
    return render_template('pdf-combined-error.html')

#SERVICE TO UPDATE ALM ON PUSH

@application.route('/todo/api/v1.0/releasenotes/updateAlm/',methods=['POST'])
def update_alm():
    data = {}

    #GET REQUEST DATA
    if request.headers['Content-Type'] == 'application/json':
        data = json.loads(request.data)
    else:
        return make_response(jsonify({'error':'Content-type is unsupported'}),400)
    updated_issues=[]
    project_id = data['project_id']
    ref_name = data['ref_name']
    GITLAB_URL = PROTOCOL+GITLAB_IP+':'+str(GITLAB_PORT)
    JIRA_AUTHORIZATION_URL = PROTOCOL+JIRA_IP+":"+str(JIRA_PORT)+"/rest/auth/1/session/"
    commit_messages = get_commit_messages(project_id,ref_name,GITLAB_ACCESS_TOKEN,GITLAB_URL)
    logger.info(str(commit_messages))
    jsessionid = get_session_cookie(JIRA_USERNAME,JIRA_PASSWORD,JIRA_AUTHORIZATION_URL)
    if jsessionid["values"] != False:
        jsessionid = jsessionid["JSESSIONID"]
    else:
        return make_response(jsonify({'error':'JIRA Login failed'}), 403)
    code_integration_id = jira_field_id_mapping(CODE_INTEGRATION,JIRA_IP,JIRA_PORT,jsessionid)
    for item in commit_messages:
        if(jira_query_update(JIRA_USERNAME,JIRA_PASSWORD,code_integration_id,JIRA_IP,JIRA_PORT,item.split(':')[0])=='204'):
           updated_issues.append(item.split(':')[0])
    updated_issues = list(set(updated_issues))
    if len(updated_issues)!=0:
        return make_response(jsonify({'success': 'FOLLOWING TRACKERS IDs HAVE BEEN UPDATED IN ALM','trackers':updated_issues}), 200)
    else:
        return make_response(jsonify({'failed': 'NO TRACKER IDs FOUND IN COMMIT MESSAGES','trackers':updated_issues}),404)

#USER FACING SERVICE TO GENERATE RELEASE NOTES
@application.route('/generate/generate_notes/',methods=['GET'])
def generate_notes():
    JIRA_AUTHORIZATION_URL = PROTOCOL+JIRA_IP+":"+str(JIRA_PORT)+"/rest/auth/1/session/"

    # GET REQUEST DATA
    project_id = request.args.get('project_id')
    release_tag = request.args.get('release_tag')
    internal_flag = request.args.get('internal_flag')

    #GET JIRA AUTHORIZATION SESSION COOKIE
    jsessionid = get_session_cookie(JIRA_USERNAME,JIRA_PASSWORD,JIRA_AUTHORIZATION_URL)
    if jsessionid['values'] == True:
          jsessionid = jsessionid["JSESSIONID"]
    else:
          print jsessionid['values']
          return make_response(jsonify({'error': 'JIRA AUTHORIZATION FAILED'}), 404)

    #CHECK AND VALIDATE INPUTS - INTERNAL/EXTERNAL
    if internal_flag not in ["Internal","internal","External","external","INTERNAL","EXTERNAL"]:
          return make_response(jsonify({'error': 'INVALID INTERNAL FLAG'}), 404)

    #GET JIRA FIELD ID FOR DESCRIPTION FIELD - THIS FIELD IS CONFIGURABLE
    customer_description_id = jira_field_id_mapping(CUSTOMER_DESCRIPTION,JIRA_IP,JIRA_PORT,jsessionid)

    #GET VERSIONS AND CHECK IF THIS VERSION EXISTS

    if release_tag not in jira_get_versions_all(JIRA_IP,JIRA_PORT,project_id,jsessionid):
       return make_response(jsonify({"errorMessages":["No project could be found with key and Release specified."],"errors":{}}),400)

    #REFER functions/jira_query.py:jira_release_tag_look_up
    description = jira_release_tag_look_up(JIRA_IP,JIRA_PORT,jsessionid,project_id,release_tag,customer_description_id,internal_flag)

    #GET REQUIRED DATA FROM FUNCTION RESPONSE
    closed_issues = description["BUG"]["BUGS"]
    open_issues = description["BUG_UNDONE"]["BUGS_UNDONE"]
    cr_delivered = description["INITIATIVE"]["INITIATIVES"]+description["EPIC"]["EPICS"]
    merged_issues = description["INITIATIVE"]["MERGED_ISSUE"]+description["EPIC"]["MERGED_ISSUE"]+description["STORY"]["MERGED_ISSUE"]+description["TASK"]["MERGED_ISSUE"]+description["BUG"]["MERGED_ISSUE"]

    output = render_template('template.html', epics=cr_delivered,open_defects=open_issues,closed_defects=closed_issues,merged_issues=merged_issues)
    release_note_name = 'Release_Notes_'+project_id+'_'+release_tag+'_'+internal_flag+'.html'

    #WRITE TO FILE
    writer = codecs.open(root_dir()+'/data/'+release_note_name,'w','utf-8')
    writer.write(output)
    writer.close()

    #RETURN FILE CONTENT
    content = get_releasenotes(release_note_name)
    return Response(content, mimetype="text/html")
#SERVICE TO COMBINE RELEASE NOTES
@application.route('/generate/combine_notes/',methods=['GET'])
def combine_notes():
    JIRA_AUTHORIZATION_URL = PROTOCOL+JIRA_IP+":"+str(JIRA_PORT)+"/rest/auth/1/session/"

    #GET REQUEST DATA
    project_id = request.args.get('project_id')
    from_release_tag = request.args.get('from_release_tag')
    to_release_tag = request.args.get('to_release_tag')
    internal_flag = request.args.get('internal_flag')

    #GET JIRA AUTHORIZATION SESSION COOKIE
    jsessionid = get_session_cookie(JIRA_USERNAME,JIRA_PASSWORD,JIRA_AUTHORIZATION_URL)
    if jsessionid['values'] == True:
          jsessionid = jsessionid["JSESSIONID"]
    else:
          print jsessionid['values']
          return make_response(jsonify({'error': 'JIRA AUTHORIZATION FAILED'}), 404)

    #CHECK AND VALIDATE RELEASE TAGS
    if from_release_tag not in jira_get_versions_all(JIRA_IP,JIRA_PORT,project_id,jsessionid):
       return make_response(jsonify({"errorMessages":["No project could be found with key and Release specified."],"errors":{}}),400)
    if to_release_tag not in jira_get_versions_all(JIRA_IP,JIRA_PORT,project_id,jsessionid):
       return make_response(jsonify({"errorMessages":["No project could be found with key and Release specified."],"errors":{}}),400)

    #GET FIELD ID FOR DESCRIPTION FIELD
    customer_description_id = jira_field_id_mapping(CUSTOMER_DESCRIPTION,JIRA_IP,JIRA_PORT,jsessionid)

    #GET ALL RELEASES FOR THE PROJECT STARTING AFTER START RELEASE:START DATE AND ENDING ON OR BEFORE END RELEASE:START DATE
    #REFER TO functions/jira_query.py:jira_get_versions
    release_tags = jira_get_versions(JIRA_IP,JIRA_PORT,project_id,from_release_tag,to_release_tag,jsessionid)

    if release_tags == []:
       return make_response(jsonify({'error':'NO RELEASES FOUND BETWEEN START AND END RELEASES SPECIFIED'}),400)

    closed_issues = []
    open_issues = []
    cr_delivered = []
    merged_issues = []
    #GET RELEASE INFORMATION FOR EACH RELEASE IN release_tags if not empty
    for release_tag in release_tags:
       description = jira_release_tag_look_up(JIRA_IP,JIRA_PORT,jsessionid,project_id,release_tag,customer_description_id,internal_flag)
       logger.info(release_tag+" - "+internal_flag+" : "+str(description))
       closed_issues += description["BUG"]["BUGS"]
       open_issues += description["BUG_UNDONE"]["BUGS_UNDONE"]
       cr_delivered += description["INITIATIVE"]["INITIATIVES"]+description["EPIC"]["EPICS"]
       merged_issues += description["INITIATIVE"]["MERGED_ISSUE"]+description["EPIC"]["MERGED_ISSUE"]+description["STORY"]["MERGED_ISSUE"]+description["TASK"]["MERGED_ISSUE"]+description["BUG"]["MERGED_ISSUE"]
    open_issue_ids = []

    #REMOVE DUPLICATES
    unique_open_issues = []
    for item in open_issues:
        if item['issue_id'] not in open_issue_ids:
           open_issue_ids.append(item['issue_id'])
           unique_open_issues.append(item)
        else:
           pass
    logger.info("CLOSED ISSUES : "+str(closed_issues))
    logger.info("OPEN ISSUES : "+str(open_issues))
    logger.info("CR DELIVERED : "+str(cr_delivered))
    logger.info("MERGED ISSUES : "+str(merged_issues))

    #WRITE TO HTML FILE
    output = render_template('template.html', epics=cr_delivered,open_defects=unique_open_issues,closed_defects=closed_issues,merged_issues=merged_issues)
    release_note_name = 'Release_Notes_'+project_id+'_'+from_release_tag+'_'+to_release_tag+'_'+internal_flag+'.html'
    writer = codecs.open(root_dir()+'/data/'+release_note_name,'w','utf-8')
    writer.write(output)
    writer.close()

    #RETURN FILE CONTENT
    content = get_releasenotes(release_note_name)
    return Response(content, mimetype="text/html")

@application.route('/generate_error/', methods=['GET'])
def generate_error():
    return render_template('generate-error.html')

@application.route('/lookup_error/', methods=['GET'])
def lookup_error():
    return render_template('lookup-error.html')
@application.route('/pdf_error/', methods=['GET'])
def pdf_error():
    return render_template('pdf-error.html')

@application.route('/commits/api/v1.0/releasenotes/latest/', methods=['GET'])
def metrics():  # pragma: no cover
    content = get_latest_releasenotes()
    return Response(content, mimetype="text/html")
@application.route('/todo/api/v1.0/releasenotes/generate/', methods=['POST'])
def get_tasks():
    #writer = open('cache-writer.txt','w')
    #writer.write(tasks)
    #print request.headers
    data = {}
    if request.headers['Content-Type'] == 'application/json':
        print(request.data)
        data = json.loads(request.data)
    else:
        return make_response(jsonify({'error':'Content-type is unsupported'}),400)
    if 'commit_message' in data.keys():
        logger.info("COMMIT MESSAGE:"+"\n"+data['commit_message'])
        ISSUE_ID = data['commit_message'].split(":")[0]
        JIRA_AUTHORIZATION_URL = PROTOCOL+JIRA_IP+":"+str(JIRA_PORT)+"/rest/auth/1/session/"
        JIRA_ISSUES_URL = PROTOCOL+JIRA_IP+":"+str(JIRA_PORT)+"/rest/api/latest/issue/"+ISSUE_ID+"?expand=names"
        JIRA_ISSUES_URL_BASE = PROTOCOL+JIRA_IP+":"+str(JIRA_PORT)+"/rest/api/2/issue/"+ISSUE_ID+"/"
        jsessionid = get_session_cookie(JIRA_USERNAME,JIRA_PASSWORD,JIRA_AUTHORIZATION_URL)
        logger.info("SESSION COOKIE :"+str(jsessionid))
        if jsessionid["values"] != False:
            jsessionid = jsessionid["JSESSIONID"]
            HEADERS = {
             'connection': "keep-alive",
             'upgrade-insecure-requests': "1",
             'cache-control': "no-cache",
             'content-type': 'application/json',
             'cookie': 'JSESSIONID='+jsessionid
            }

            wi_status = jira_validate(JIRA_ISSUES_URL,jsessionid)
            logger.info("WI STATUS : "+wi_status)
            if wi_status == 'Done' or wi_status == 'done':
               return jsonify({'errorMessages':["Work item is already in done state, please revise work item Id in the commit message"]})
            response = requests.get(JIRA_ISSUES_URL, headers=HEADERS, verify=False).json()
            customer_description_id = jira_field_id_mapping(CUSTOMER_DESCRIPTION,JIRA_IP,JIRA_PORT,jsessionid)
            logger.info("CUSTOMER DESC ID : "+str(customer_description_id))
            release_tag_id = jira_field_id_mapping(RELEASE_TAG,JIRA_IP,JIRA_PORT,jsessionid)
            logger.info("RELEASE TAG ID : "+str(release_tag_id))
            code_integration_id = jira_field_id_mapping(CODE_INTEGRATION,JIRA_IP,JIRA_PORT,jsessionid)
            if(jira_query_update(JIRA_USERNAME,JIRA_PASSWORD,code_integration_id,JIRA_IP,JIRA_PORT,ISSUE_ID)!='204'):
                logger.info("COULD NOT UPDATE WORK ITEM CODE INTEGRATION ID--CODE RECEIVED : "+str(jira_query_update(JIRA_USERNAME,JIRA_PASSWORD,code_integration_id,JIRA_IP,JIRA_PORT,ISSUE_ID)))
            logger.info("CODE INT ID : "+str(code_integration_id))
            project_id = check_for_none(response['fields']['project']['id'])
            logger.info("PROJECT ID : "+str(project_id))
            jira_project_name = check_for_none(response['fields']['project']['name'])
            logger.info("PROJECT NAME : "+str(jira_project_name))
            release_tag = check_for_none(response['fields'][release_tag_id])
            logger.info("RELEASE TAG : "+str(release_tag))
            #jira_query_update(JIRA_USERNAME,JIRA_PASSWORD,code_integration_id,JIRA_IP,JIRA_PORT,ISSUE_ID)
            description = jira_release_tag_look_up(JIRA_IP,JIRA_PORT,jsessionid,jira_project_name,release_tag,customer_description_id)
            logger.info("DESCRIPTION : "+"\n"+description)
            title = check_for_none(response['fields']['summary'])
            issue_id = ISSUE_ID
            release_note_name = "Release-Notes-"+jira_project_name+"-"+release_tag+".html"
            html_parse(root_dir()+'/templates/template.html',root_dir()+'/data/'+release_note_name,description,jira_project_name,release_tag)
            content = open(root_dir()+'/data/'+release_note_name,'r').read()
            return Response(content, mimetype="text/html")
        else:
            return make_response(jsonify({'error':'JIRA Login failed'}), 403)
    else:
        return make_response(jsonify({'error':'parameter commit_message is missing from request body'}),400)

@application.route('/commits/api/v1.0/releasenotes/', methods=['GET','POST'])
def release_lookup():
  JIRA_AUTHORIZATION_URL = PROTOCOL+JIRA_IP+":"+str(JIRA_PORT)+"/rest/auth/1/session/"
  jsessionid = get_session_cookie(JIRA_USERNAME,JIRA_PASSWORD,JIRA_AUTHORIZATION_URL)
  logger.info("SESSION COOKIE :"+str(jsessionid))
  if jsessionid["values"] != False:
         jsessionid = jsessionid["JSESSIONID"]
  else:
         return make_response(jsonify({'error':'JIRA AUTH FAILED'}), 404)
  if request.method=='GET':
    logger.info("PROJECT NAME FOR LOOKUP : "+str(request.args.get('project_name')))
    logger.info("RELEASE TAG ID FOR LOOKUP : "+str(request.args.get('release_tag')))
    logger.info("RELEASE NOTES FILENAME : "+root_dir()+"/data/Release_Notes_"+str(request.args.get('project_name'))+"_"+str(request.args.get('release_tag'))+"_"+str(request.args.get('internal_flag'))+".html")
    project_name = str(request.args.get('project_name'))
    if os.path.isfile(root_dir()+'/data/Release_Notes_'+project_name+'_'+str(request.args.get('release_tag'))+'_'+str(request.args.get('internal_flag'))+'.html'):
       content = open(root_dir()+'/data/Release_Notes_'+project_name+'_'+str(request.args.get('release_tag'))+'_'+str(request.args.get('internal_flag'))+'.html','r').read()
       return Response(content, mimetype="text/html")
    else:
        return make_response(jsonify({'error':'Not Found'}), 400)
  elif request.method=='POST':
    logger.info("PROJECT NAME FOR LOOKUP : "+request.form['project_name'])
    logger.info("RELEASE TAG ID FOR LOOKUP : "+request.form['release_tag'])
    logger.info("RELEASE NOTES FILENAME : "+root_dir()+"/data/Release_Notes_"+request.form['project_name']+"_"+request.form['release_tag']+".html")

    if os.path.exists(root_dir()+'/data/Release_Notes_'+request.form['project_name']+'_'+request.form['release_tag']+'_'+request.form['internal_flag']+'.html'):
       content = open(root_dir()+'/data/Release_Notes_'+request.form['project_name']+'_'+request.form['release_tag']+'.html','r').read()
       return Response(content, mimetype="text/html")
    else:
        return make_response(jsonify({'error':'Not Found'}), 400)
@application.route('/commits/api/v1.0/releasenotes-combined/', methods=['GET','POST'])
def release_lookup_combined():
  JIRA_AUTHORIZATION_URL = PROTOCOL+JIRA_IP+":"+str(JIRA_PORT)+"/rest/auth/1/session/"
  jsessionid = get_session_cookie(JIRA_USERNAME,JIRA_PASSWORD,JIRA_AUTHORIZATION_URL)
  logger.info("SESSION COOKIE :"+str(jsessionid))
  if jsessionid["values"] != False:
         jsessionid = jsessionid["JSESSIONID"]
  else:
         return make_response(jsonify({'error':'JIRA AUTH FAILED'}), 404)
  if request.method=='GET':
    logger.info("PROJECT NAME FOR LOOKUP : "+str(request.args.get('project_name')))
    project_name = str(request.args.get('project_name'))
    logger.info("FROM RELEASE TAG ID FOR LOOKUP : "+str(request.args.get('from_release_tag')))
    from_release_tag = str(request.args.get('from_release_tag'))
    logger.info("TO RELEASE TAG ID FOR LOOKUP : "+str(request.args.get('to_release_tag')))
    to_release_tag = str(request.args.get('to_release_tag'))
    internal_flag = str(request.args.get('internal_flag'))
    logger.info("RELEASE NOTES FILENAME : "+root_dir()+"/data/Release_Notes_"+str(request.args.get('project_name'))+"_"+str(request.args.get('from_release_tag'))+"_"+str(request.args.get('to_release_tag'))+".html")
    #project_name = jira_get_project_name_by_key(JIRA_IP,JIRA_PORT,project_name,jsessionid)
    release_note_name = 'Release_Notes_'+project_name+'_'+from_release_tag+'_'+to_release_tag+'_'+internal_flag+'.html'
    if os.path.isfile(root_dir()+'/data/'+release_note_name):
       content = open(root_dir()+'/data/'+release_note_name,'r').read()
       return Response(content, mimetype="text/html")
    else:
        return make_response(jsonify({'error':'Not Found'}), 400)
  elif request.method=='POST':
    logger.info("PROJECT NAME FOR LOOKUP : "+request.form['project_name'])
    logger.info("RELEASE TAG ID FOR LOOKUP : "+request.form['release_tag'])
    logger.info("RELEASE NOTES FILENAME : "+root_dir()+"/data/Release-Notes-"+request.form['project_name']+"-"+request.form['release_tag']+".html")
    if os.path.exists(root_dir()+'/data/Release-Notes-'+request.form['project_name']+'-'+request.form['release_tag']+'.html'):
       content = open(root_dir()+'/data/Release-Notes-'+request.form['project_name']+'-'+request.form['release_tag']+'.html','r').read()
       return Response(content, mimetype="text/html")
    else:
        return make_response(jsonify({'error':'Not Found'}), 400)
@application.route('/commits/api/v1.0/releasenotes/pdf/', methods=['GET'])
def release_pdf_lookup():
  JIRA_AUTHORIZATION_URL = PROTOCOL+JIRA_IP+":"+str(JIRA_PORT)+"/rest/auth/1/session/"
  jsessionid = get_session_cookie(JIRA_USERNAME,JIRA_PASSWORD,JIRA_AUTHORIZATION_URL)
  logger.info("SESSION COOKIE :"+str(jsessionid))
  if jsessionid["values"] != False:
         jsessionid = jsessionid["JSESSIONID"]
  else:
         return make_response(jsonify({'error':'JIRA AUTH FAILED'}), 404)
  if request.method=='GET':
    project_name = request.args.get('project_name')
    release_tag = request.args.get('release_tag')
    internal_flag = request.args.get('internal_flag')
    #html_path = root_dir()+"/data/Release_Notes_"+str(project_name)+"_"+str(release_tag)+"_"+str(internal_flag)+".html"
    #pdf_path = root_dir()+'/pdf_reports/Release_Notes_'+str(project_name)+'_'+str(release_tag)+'_'+str(internal_flag)+'.pdf'
    logger.info("PROJECT NAME FOR LOOKUP : "+str(project_name))
    logger.info("RELEASE TAG ID FOR LOOKUP : "+str(release_tag))
    logger.info("INTERNAL FLAG ID FOR LOOKUP : "+str(internal_flag))
    #logger.info("RELEASE NOTES FILENAME : "+str(html_path))
    #project_name = jira_get_project_name_by_key(JIRA_IP,JIRA_PORT,project_name,jsessionid)
    html_path = root_dir()+"/data/Release_Notes_"+str(project_name)+"_"+str(release_tag)+"_"+str(internal_flag)+".html"
    pdf_path = root_dir()+'/pdf_reports/Release_Notes_'+str(project_name)+'_'+str(release_tag)+'_'+str(internal_flag)+'.pdf'
    if os.path.exists(html_path):
       make_pdf_report(html_path,pdf_path)
    if os.path.exists(pdf_path):
       content = open(pdf_path,'r').read()
       return Response(content, mimetype="application/pdf")
    else:
       return make_response(jsonify({'error':'Not Found'}), 400)
  #elif request.method=='POST':
  # logger.info("PROJECT NAME FOR LOOKUP : "+request.form['project_name'])
  # logger.info("RELEASE TAG ID FOR LOOKUP : "+request.form['release_tag'])
  # logger.info("RELEASE NOTES FILENAME : "+root_dir()+"/data/Release-Notes-"+request.form['project_name']+"-"+request.form['release_tag']+".html")
  # if os.path.exists(root_dir()+'/data/Release-Notes-'+request.form['project_name']+'-'+request.form['release_tag']+'.html'):
  #    content = open(root_dir()+'/data/Release-Notes-'+request.form['project_name']+'-'+request.form['release_tag']+'.html','r').read()
  #    return Response(content, mimetype="text/html")
  #else:
  #     return make_response(jsonify({'error':'Not Found'}), 400)

@application.route('/commits/api/v1.0/releasenotes/pdf_combined/', methods=['GET'])
def release_combined_pdf_lookup():
  JIRA_AUTHORIZATION_URL = PROTOCOL+JIRA_IP+":"+str(JIRA_PORT)+"/rest/auth/1/session/"
  jsessionid = get_session_cookie(JIRA_USERNAME,JIRA_PASSWORD,JIRA_AUTHORIZATION_URL)
  logger.info("SESSION COOKIE :"+str(jsessionid))
  if jsessionid["values"] != False:
         jsessionid = jsessionid["JSESSIONID"]
  else:
         return make_response(jsonify({'error':'JIRA AUTH FAILED'}), 404)
  if request.method=='GET':
    project_name = request.args.get('project_name')
    from_release_tag = request.args.get('from_release_tag')
    to_release_tag =  request.args.get('to_release_tag')
    internal_flag = request.args.get('internal_flag')
    #html_path = root_dir()+"/data/Release_Notes_"+str(project_name)+"_"+str(from_release_tag)+"_"+str(to_release_tag)+"_"+str(internal_flag)+".html"
    #pdf_path = root_dir()+'/pdf_reports/Release_Notes_'+str(project_name)+'_'+str(from_release_tag)+'_'+str(to_release_tag)+'_'+str(internal_flag)+'.pdf'
    logger.info("PROJECT NAME FOR LOOKUP : "+str(project_name))
    logger.info("FROM RELEASE ID FOR LOOKUP : "+str(from_release_tag))
    logger.info("TO RELEASE ID FOR LOOKUP : "+str(to_release_tag))
    logger.info("INTERNAL FLAG ID FOR LOOKUP : "+str(internal_flag))
    #logger.info("RELEASE NOTES FILENAME : "+str(html_path))
    #project_name = jira_get_project_name_by_key(JIRA_IP,JIRA_PORT,project_name,jsessionid)
    html_path = root_dir()+"/data/Release_Notes_"+str(project_name)+"_"+str(from_release_tag)+"_"+str(to_release_tag)+"_"+str(internal_flag)+".html"
    pdf_path = root_dir()+'/pdf_reports/Release_Notes_'+str(project_name)+'_'+str(from_release_tag)+'_'+str(to_release_tag)+'_'+str(internal_flag)+'.pdf'

    if os.path.exists(html_path):
       make_pdf_report(html_path,pdf_path)
    else:
       return make_response(jsonify({'error':'Not Found'}), 400)
    if os.path.exists(pdf_path):
       content = open(pdf_path,'r').read()
       return Response(content, mimetype="application/pdf")
    else:
       return make_response(jsonify({'error':'Not Found'}), 400)

@application.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

if __name__ == '__main__':
    application.config['SECRET_KEY'] = 'sjhdfvbkuydfvawadda'
    application.jinja_env.auto_reload = True
    application.config['TEMPLATES_AUTO_RELOAD'] = True
    application.run(debug=True,extra_files = [root_dir()+'/data/Release-Notes-*'])

