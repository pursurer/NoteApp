#!/usr/bin/env python3
"""Minimal Session 02 diagram input; finish and export in the Excalidraw website."""
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OBS = json.loads((HERE / 'observations.json').read_text())
FLOWS = [
 (1,'Student','Flask','POST /login (username, password)','TB1'),
 (2,'Student','Flask','Request grades (session / Bearer JWT)','TB1'),
 (3,'Flask','Student','Session / grades','TB1'),
 (4,'Teacher','Flask','Login / read or edit grades','TB1'),
 (5,'Flask','Teacher','Session / classes / grades','TB1'),
 (6,'Admin','Flask','Login / manage users','TB1'),
 (7,'Flask','Admin','Session / users / classes','TB1'),
 (8,'Flask','PostgreSQL','SQL read / write','TB2'),
 (9,'PostgreSQL','Flask','Query results / command completion','TB2'),
]
RISKS = [
 ['Guess another user login','Login fields alter concatenated SQL','Mutable login log','Credentials travel over HTTP','Repeated login requests','Login bypass could grant a higher role'],
 ['Use a forged/stolen token','Change requested grade id','API reads not individually logged','API lacks grade owner filter','Repeated grade queries','Record-access flaw; higher-role access untested'],
 ['Impersonate the HTTP server','Alter response or active grade comments','No protected disclosure audit','Session, token or grades exposed over HTTP','Large responses','Student data grants no higher role; active content impact untested'],
 ['Use a forged/stolen teacher session','CSRF or unauthorized grade/class changes','Grade log lacks protected before/after values','Login and grade input travel over HTTP','Repeated reads/writes','Class ownership not checked; higher-role access untested'],
 ['Impersonate the HTTP server','Alter response or active comments','No protected disclosure audit','Teacher page exposes all classes/grades','Large tables/exports','Active content could use a teacher session (untested)'],
 ['Use a forged/stolen admin session','CSRF or changed action/user/role','User changes not explicitly logged','New user password travels over HTTP','Unbounded user creation/errors','Stolen admin session / CSRF may enable admin creation (untested)'],
 ['Impersonate the HTTP server','Alter returned user/class data','No protected disclosure audit','User identities and sessions exposed over HTTP','Large user lists','N/A for metadata; admin actions are in flow 6'],
 ['Impersonate DB peer','Unsafe login SQL; unauthorized writes','Shared DB login hides end-user attribution','DB TLS is off; new passwords stored plaintext','Exhaust DB connections/resources','Application DB privilege scope needs verification'],
 ['Accept fabricated DB results','Alter returned data or command result','Completion alone is not an audit record','Sensitive identity/grade results exposed','Large result sets/timeouts','Fake role results could affect authorization (untested)'],
]


def tables():
    for filename,header,rows in [
      ('flows.csv',['ID','Sender','Receiver','Data','Boundary'],FLOWS),
      ('STRIDE.csv',['ID','Sender -> receiver','Data','Boundary','S','T','R','I','D','E'],
       [[f[0],f'{f[1]} -> {f[2]}',f[3],f[4],*RISKS[i]] for i,f in enumerate(FLOWS)])]:
        with (HERE/filename).open('w',encoding='utf-8-sig',newline='') as file:
            writer=csv.writer(file);writer.writerow(header);writer.writerows(rows)
    lines=['# NotesApp - Session 02 lab','', 'Group members: fill in before submission.','',
      f'Fork: {OBS["fork"]}. Baseline: `{OBS["source_commit"]}`.',
      '', '## Numbered data-flow diagram','',
      'The diagram follows course slide 34: three browsers, a larger Flask block, PostgreSQL, TB1/TB2 and a short flow list. Each of its nine numbered arrows maps to one STRIDE row.',
      'Teacher/Admin traffic and DB operations are grouped to keep the diagram readable. Auxiliary health, static assets, audit storage, CSV details and Admin Ping subprocess flows are outside this compact drawing.',
      '', 'Open NotesApp-data-flow.excalidraw in https://excalidraw.com/. It includes the original diagram, six STRIDE questions and the complete table below it. PNGs are exported from that website.',
      '', '## Flow list','', '| ID | Sender -> receiver | Data | Boundary |','|---|---|---|---|']
    lines += [f'| {n} | {s} -> {r} | {data} | {tb} |' for n,s,r,data,tb in FLOWS]
    lines += ['', '## First STRIDE table','',
      'STRIDE.csv contains nine rows. S: Spoofing; T: Tampering; R: Repudiation; I: Information disclosure; D: Denial of service; E: Elevation of privilege. Entries are potential threats supported by inspected source, not successful exploit results.',
      'The D column lists availability scenarios to assess; no load tests or resource-impact measurements were performed. Flow 8 database grants still need verification. Legitimate admin user creation alone is not privilege escalation.',
      'The table has the requested ten columns: ID, Sender -> receiver, Data, Boundary, S, T, R, I, D, E. NotesApp-STRIDE.excalidraw and NotesApp-STRIDE-table.png are exports of the STRIDE section; EXPLANATION.zh-CN.md explains the complete diagram in Chinese.',
      'STRIDE definitions: https://learn.microsoft.com/en-us/biztalk/core/identifying-potential-threats .',
      '', '## Observation and source','',
      f'{len(OBS["events"])} normal HTTP requests covered anonymous, student, teacher and admin states. The student read their own seeded grade, the teacher page showed grade IDs, and the database digest was unchanged.',
      'The grade, user-management and Ping POST forms were inspected but not submitted. No attack payloads or load tests were used. DB flows were reconstructed from code, not packet capture.',
      '', 'Evidence: observations.json, web/app.py, web/templates, db/init.sql, docker-compose.yml. PostgreSQL SHOW ssl returned off. The local compose.lab.yml binds localhost:8080, hides the DB host port and removes web host mounts.',
      '', 'Before submission: add group members and review the nine flow/STRIDE pairs as a group. Keep both for Project 1.', '']
    (HERE/'REPORT.md').write_text('\n'.join(lines))


ELEMENTS=[]
NOW=int(datetime.fromisoformat(OBS['observed_at']).timestamp()*1000)


def base(kind,x,y,w,h,**extra):
    ident=f'min-{len(ELEMENTS):03d}'
    seed=int(hashlib.sha256(ident.encode()).hexdigest()[:7],16)
    e=dict(id=ident,type=kind,x=x,y=y,width=w,height=h,angle=0,
      strokeColor='#00a6d6',backgroundColor='transparent',fillStyle='solid',strokeWidth=2,
      strokeStyle='solid',roughness=0,opacity=100,groupIds=[],frameId=None,
      roundness=None,seed=seed,version=1,versionNonce=seed,index=None,
      isDeleted=False,boundElements=None,updated=NOW,created=NOW,link=None,locked=False)
    e.update(extra);ELEMENTS.append(e);return e


def text(x,y,value,size=24,color='#102637',group=None):
    lines=value.splitlines()
    e=base('text',x,y,max(len(s) for s in lines)*size*.61,len(lines)*size*1.25,
      strokeColor=color,fontSize=size,fontFamily=2,baseFontSize=None,text=value,originalText=value,
      textAlign='left',verticalAlign='top',containerId=None,autoResize=True,lineHeight=1.25)
    if group:e['groupIds']=[group]
    return e


def rect(x,y,w,h,fill,group):
    return base('rectangle',x,y,w,h,backgroundColor=fill,strokeColor='#bdd5e6',roundness={'type':3,'value':10},groupIds=[group])


def edge(x1,y1,x2,y2,number=None,dashed=False):
    # Normalize right-to-left arrows so export bounds remain correct.
    x=min(x1,x2);y=min(y1,y2)
    e=base('line' if dashed else 'arrow',x,y,abs(x2-x1),abs(y2-y1),
      points=[[x1-x,y1-y],[x2-x,y2-y]],startBinding=None,endBinding=None,
      startArrowhead=None,endArrowhead=None if dashed else 'arrow',elbowed=False,polygon=False,
      strokeStyle='dashed' if dashed else 'solid',
      strokeColor='#087498' if dashed else '#00a6d6',strokeWidth=2.5 if dashed else 2)
    if number:
        text((x1+x2)/2-13,y1-42,str(number),28,'#9b650b')
        e['customData']={'flowId':number}
    return e


def scene():
    text(45,32,'Your numbered flow diagram',42)
    base('line',45,105,112,0,points=[[0,0],[112,0]],startBinding=None,endBinding=None,
         startArrowhead=None,endArrowhead=None,polygon=False,strokeWidth=3)
    base('line',163,105,24,0,points=[[0,0],[24,0]],startBinding=None,endBinding=None,
         startArrowhead=None,endArrowhead=None,polygon=False,strokeWidth=3,strokeColor='#a35e00')
    for name,y in [('Student',215),('Teacher',470),('Admin',725)]:
        rect(60,y,220,140,'#ffffff',name)
        text(80,y+24,name,30,group=name)
        text(80,y+68,'browser',21,'#476a85',group=name)
    # The enlarged middle block is the only process in the course template.
    rect(620,185,470,710,'#e5f0f7','Flask')
    text(648,217,'Flask app',42,group='Flask')
    text(648,275,'server · Docker',24,'#476a85',group='Flask')
    rect(1250,360,280,360,'#e3f5fc','PostgreSQL')['strokeColor']='#00a6d6'
    text(1275,389,'PostgreSQL',32,group='PostgreSQL')
    text(1275,435,'database',24,'#476a85',group='PostgreSQL')
    for x,name in [(450,'TB1'),(1160,'TB2')]:
        edge(x,175,x,915,dashed=True)
        text(x-28,937,name,24,'#00749b')
    for args in [(280,245,620,245,1),(280,288,620,288,2),(620,332,280,332,3),
                 (280,500,620,500,4),(620,570,280,570,5),
                 (280,755,620,755,6),(620,825,280,825,7),
                 (1090,465,1250,465,8),(1250,580,1090,580,9)]:
        edge(*args)
    text(1670,175,'YOUR FLOW LIST',27,'#17677f')
    display=[
       'Student → Flask: POST /login\n(username, password)',
       'Student → Flask: request grades',
       'Flask → Student: session / grades',
       'Teacher → Flask: login / edit grades',
       'Flask → Teacher: classes / grades',
       'Admin → Flask: login / manage users',
       'Flask → Admin: users / classes',
       'Flask → PostgreSQL: SQL read / write',
       'PostgreSQL → Flask: results',
    ]
    y=240
    for n,value in enumerate(display,1):
        text(1670,y,str(n),27,'#9b650b')
        text(1710,y,value,23)
        y+=102 if n==1 else 76
    data=dict(type='excalidraw',version=2,source='https://excalidraw.com',elements=ELEMENTS,
      appState={'viewBackgroundColor':'#ffffff','gridSize':None,'theme':'light'},files={})
    (HERE/'NotesApp-data-flow.excalidraw').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':
    tables();scene()
    print(f'Prepared 9 numbered flows, 9 STRIDE rows and {len(ELEMENTS)} native elements')
