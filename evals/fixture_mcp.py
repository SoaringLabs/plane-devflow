#!/usr/bin/env python3
"""Synthetic stdio MCP service. State/audit are outside the evaluated workspace."""
import json
import sys
import uuid
from pathlib import Path

TOOLS = ('workspace', 'project', 'workitem', 'workitem_comment', 'workitem_link')
ACTIONS = {'workspace':['retrieve'],'project':['retrieve'],'workitem':['list','list_archived','retrieve','retrieve_by_identifier','create','update'],
           'workitem_comment':['list','retrieve','create','update'],'workitem_link':['list','retrieve','create','update']}
FIELDS = ('action','project_id','workitem_id','workitem_identifier','name','description_html',
          'external_id','external_source','comment_id','comment_html','link_id','url','title',
          'cursor','fields','expand','query','pql')


def invoke(state, tool, args):
    action=args.get('action','retrieve')
    state['calls'].append({'tool':tool,'arguments':args})
    if args.get('project_id',state['project'].get('id'))!=state['project'].get('id'):raise ValueError('Wrong fixture project')
    if tool=='workspace':return {'slug':'synthetic-workspace','connected_via':'fixture'}
    if tool=='project':return state['project']
    collection={'workitem':'items','workitem_comment':'comments','workitem_link':'links'}[tool]
    rows=state[collection]
    if action in ('list','list_archived','search'):
        found=[] if action=='list_archived' else list(rows)
        if tool!='workitem':found=[r for r in found if r['workitem_id']==args['workitem_id']]
        return {'results':found,'next_page_results':False,'count':len(found)}
    if action in ('retrieve','retrieve_by_identifier'):
        key={'workitem':'workitem_id','workitem_comment':'comment_id','workitem_link':'link_id'}[tool]
        return next(r for r in rows if r['id']==args.get(key) or
                    (tool=='workitem' and r['identifier']==args.get('workitem_identifier')))
    if action=='create':
        row=dict(args,id=str(uuid.uuid4()))
        if tool=='workitem':
            n=max([r['sequence_id'] for r in rows]+[0])+1
            row.update(sequence_id=n,identifier='DEMO-'+str(n),labels=[],state={'name':'Backlog','group':'backlog'})
        rows.append(row)
        return row
    if action=='update':
        key={'workitem':'workitem_id','workitem_comment':'comment_id','workitem_link':'link_id'}[tool]
        row=next(r for r in rows if r['id']==args[key]);row.update(args);return row
    raise ValueError('Unsupported fixture operation')


def serve(path):
    for line in sys.stdin:
        request=json.loads(line)
        if 'id' not in request:continue
        method=request.get('method')
        if method=='initialize':
            result={'protocolVersion':request['params']['protocolVersion'],'capabilities':{'tools':{}},
                    'serverInfo':{'name':'synthetic-plane','version':'1'}}
        elif method=='tools/list':
            result={'tools':[{'name':name,'description':'Synthetic Plane '+name+' operations: '+', '.join(ACTIONS[name])+'. list returns active work items; list_archived returns archived work items. No real service access.',
                    'inputSchema':{'type':'object','properties':{k:({'type':'string','enum':ACTIONS[name]} if k=='action' else {'type':'string'}) for k in FIELDS},
                                   'required':['action'],'additionalProperties':False}} for name in TOOLS]}
        elif method=='tools/call':
            state=json.loads(path.read_text())
            try:
                value=invoke(state,request['params']['name'],request['params'].get('arguments',{}))
                result={'content':[{'type':'text','text':json.dumps(value)}],'isError':False}
            except (ValueError,KeyError,StopIteration):
                result={'content':[{'type':'text','text':'Unsupported fixture operation or missing record.'}],'isError':True}
            path.write_text(json.dumps(state))
        else:result={}
        print(json.dumps({'jsonrpc':'2.0','id':request['id'],'result':result}),flush=True)


if __name__=='__main__':serve(Path(sys.argv[1]))
