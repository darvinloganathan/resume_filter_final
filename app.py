from flask import Flask, flash, request, redirect, render_template,send_from_directory
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from pdfminer.high_level import extract_text
import os
from os import listdir
from os.path import isfile, join
from io import StringIO
import pandas as pd
import numpy as np
from collections import Counter
import spacy
nlp = spacy.load("en_core_web_sm")
from spacy.matcher import PhraseMatcher
import re
from datetime import datetime
from datetime import date
import docx2txt
from pyresparser import ResumeParser
def pdfextract(file):
    text = extract_text(file)
    return text
def wordextract(file):
    text=docx2txt.process(file)
    return text
def text_extract(file):
    filename,file_extension=os.path.splitext(file)
    if file_extension=='.pdf':
        text=pdfextract(file)
    else:
        text=wordextract(file)
    return text
email=[]
exp_year=[]
exp_no_of_years=[]

def create_profile(file):
    #text cleaning
    text = text_extract(file) 
    text = str(text)
    text = text.replace("\\n", "")
    text = text.lower()
    x=re.compile(r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|...|Dec(?:ember)?) (?:19[7-9]\d|2\d{3})(?=\D|$)')
    exp=x.findall(text)
    if exp==[]:
        exp_no_of_years.append(0)
    else:
        for i in range(len(exp)):
            x=str(exp[i])
            dt=datetime.strptime(x,'%b %Y')
            exp_year.append(dt.year)
        if 'present' in text:
            exp_no_of_years.append(date.today().year-min(exp_year))
        else:
            exp_no_of_years.append(max(exp_year)-min(exp_year))
    # create matchers pattern
    keyword_dict = pd.read_csv('template.csv')
    stats_words = [nlp(text) for text in keyword_dict['Statistics'].dropna(axis = 0)]
    NLP_words = [nlp(text) for text in keyword_dict['NLP'].dropna(axis = 0)]
    ML_words = [nlp(text) for text in keyword_dict['Machine Learning'].dropna(axis = 0)]
    DL_words = [nlp(text) for text in keyword_dict['Deep Learning'].dropna(axis = 0)]
    R_words = [nlp(text) for text in keyword_dict['R Language'].dropna(axis = 0)]
    python_words = [nlp(text) for text in keyword_dict['Python Language'].dropna(axis = 0)]
    Data_Engineering_words = [nlp(text) for text in keyword_dict['Data Engineering'].dropna(axis = 0)]
    no_skill_words=[nlp(text) for text in keyword_dict['no skill'].dropna(axis=0)]
    matcher = PhraseMatcher(nlp.vocab)
    matcher.add('Stats', None, *stats_words)
    matcher.add('NLP', None, *NLP_words)
    matcher.add('ML', None, *ML_words)
    matcher.add('DL', None, *DL_words)
    matcher.add('R', None, *R_words)
    matcher.add('Python', None, *python_words)
    matcher.add('DE', None, *Data_Engineering_words)
    matcher.add('NS',None,*no_skill_words)
    doc = nlp(text)
    
    d = []  
    matches = matcher(doc)
    for match_id, start, end in matches:
        rule_id = nlp.vocab.strings[match_id]  # get the unicode ID, i.e. 'COLOR'
        span = doc[start : end]  # get the matched slice of the doc
        d.append((rule_id, span.text))      
        keywords = "\n".join(f'{i[0]} {i[1]} ({j})' for i,j in Counter(d).items())
    #email.append(re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", text))
    ## convertimg string of keywords to dataframe
    df = pd.read_csv(StringIO(keywords),names = ['Keywords_List'])
    df1 = pd.DataFrame(df.Keywords_List.str.split(' ',1).tolist(),columns = ['Subject','Keyword'])
    df2 = pd.DataFrame(df1.Keyword.str.split('(',1).tolist(),columns = ['Keyword', 'Count'])
    df3 = pd.concat([df1['Subject'],df2['Keyword'], df2['Count']], axis =1) 
    df3['Count'] = df3['Count'].apply(lambda x: x.rstrip(")"))
    #Candidte name
    base = os.path.basename(file)
    name3 = pd.read_csv(StringIO(base),names = ['Candidate Name'])
    
    dataf = pd.concat([name3['Candidate Name'], df3['Subject'], df3['Keyword'], df3['Count']], axis = 1)
    dataf['Candidate Name'].fillna(dataf['Candidate Name'].iloc[0], inplace = True)
    #email.append(re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", text))
    x=re.findall(r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+", text)
    if x==[]:
        email.append('no mail')
    else:
        email.append(x)
    exp.clear()
    exp_year.clear()
    return(dataf)

output = []
def remove_nestings(l):
    
    for i in l:
        if type(i) == list:
            remove_nestings(i)
        else:
            output.append(i)
    return output

def remove_empty_pdf(file):
    text = text_extract(file)
    text = str(text)
    text = text.replace("\n",'')
    text = text.lower()
    text=text.strip()
    if text=='':
        os.remove(file)
    return
def remove_empty_docx(file):
    if os.stat(file).st_size==0:
        os.remove(file)
    return
app=Flask(__name__)
# Get current path
path = os.getcwd()
path
# file Upload
UPLOAD_FOLDER = os.path.join(path, 'uploads')
RESUME_FOLDER = os.path.join(path, 'resume')
# Make directory if uploads is not exists
if not os.path.isdir(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)
if not os.path.isdir(RESUME_FOLDER):
    os.mkdir(RESUME_FOLDER)


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Allowed extension you can set your own
ALLOWED_EXTENSIONS = set(['pdf','docx'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def upload_form():
    return render_template('upload1.html')


@app.route('/', methods=['POST'])
def upload_file():
    if request.method == 'POST':

        if 'files[]' not in request.files:
            flash('No file part')
            return redirect(request.url)

        files = request.files.getlist('files[]')

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    path = 'E:/darvin/project/resume_project2/uploads/'
    for file in os.listdir(path):
        os.rename(path + file, path + file.lower())
    #Function to read resumes from the folder one by one
    mypath=UPLOAD_FOLDER #enter your path here where you saved the resumes
    
    onlyfiles = [os.path.join(mypath, f) for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]
    final_database=pd.DataFrame()
    i = 0 
    while i < len(onlyfiles):
        file = onlyfiles[i]
        remove_empty_docx(file)    
        i +=1
    onlyfiles = [os.path.join(mypath, f) for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]
    j=0
    while j < len(onlyfiles):
        file = onlyfiles[j]
        remove_empty_pdf(file)    
        j +=1
    onlyfiles= [os.path.join(mypath, f) for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]
    k = 0 
    while k < len(onlyfiles):
        file = onlyfiles[k]
        dat= create_profile(file)
        final_database = final_database.append(dat)
        k +=1
    final_database2 = final_database['Keyword'].groupby([final_database['Candidate Name'], final_database['Subject']]).count().unstack()
    final_database2.reset_index(inplace = True)
    final_database2.fillna(0,inplace=True)
    mail=remove_nestings(email)
    final_database2=final_database2.drop(['NS'],axis=1)
    final_database2['Score']=final_database2.sum(axis = 1, skipna = True)
    final_database2['mail']=mail
    final_database2['Experience']=exp_no_of_years
    result=final_database2.sort_values(by='Score',ascending=False)
    base=list(result['Candidate Name'])
    user_mail_id=list(result['mail'])
    y=[]
    for i in range(len(result)):
        y.append(result['Candidate Name'][i].split('.'))
    y=pd.DataFrame(y)
    result['Candidate Name']=y[0]
    email.clear()
    mail.clear()
    exp_no_of_years.clear()
    return render_template ("t2.html",
                           column_names=result.columns.values,
                           row_data=list(result.values.tolist()),
                           zip=zip,item=base,mail=user_mail_id)
@app.route('/download/<path:filename>', methods=['GET', 'POST'])
def download(filename):
    uploads = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    return send_from_directory(directory=uploads, filename=filename)
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'darvinlogann1@gmail.com'
app.config['MAIL_PASSWORD'] = 'Dar247'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)
@app.route('/send_mail/<path:mail_id>', methods=['GET', 'POST'])
def send_mail(mail_id):
    msg = Message('interview invite', sender = 'darvinloganathan1@gmail.com', recipients = [mail_id])
    msg.body = "you are selected for 1st level of interview discussion"
    mail.send(msg)
    return "mail has been sent"

if __name__ == "__main__":
    app.run()
    
