"""Disposable real Git repositories plus synthetic GitHub/Plane contracts."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT='11111111-1111-4111-8111-111111111111'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args, cwd, env, allowed=(0,)):
    p=subprocess.run([str(a) for a in args],cwd=cwd,env=env,text=True,capture_output=True,timeout=40)
    if p.returncode not in allowed:raise RuntimeError('Fixture operation failed: '+str(args[:2])+'\n'+p.stderr[-1500:])
    return p.stdout.strip()


def build(directory, plugin, kind):
    directory=Path(directory).resolve();work=directory/'workspace';work.mkdir(parents=True)
    private=directory/'service';private.mkdir()
    payload=work/'plugin';shutil.copytree(plugin,payload,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    harness=work/'harness';harness.mkdir();bin_dir=harness/'bin';bin_dir.mkdir()
    repo=work/'repo';repo.mkdir();bare=work/'origin.git'
    real_git=shutil.which('git')
    if sys.platform=='darwin' and real_git=='/usr/bin/git':
        resolved=subprocess.run(['xcrun','--find','git'],capture_output=True,text=True,timeout=15)
        if resolved.returncode==0:real_git=resolved.stdout.strip()
    git=bin_dir/'git'
    git.write_text('#!'+sys.executable+'\nimport os,sys\na=sys.argv[1:]\n'
        +f'if a[:2]==["fetch","origin"]:a=["fetch",{str(bare)!r},"+refs/heads/main:refs/remotes/origin/main"]\n'
        +f'os.execv({real_git!r},[{real_git!r}]+a)\n')
    git.chmod(0o755)
    gh=bin_dir/'gh';pr_file=harness/'pr.json';gh_log=harness/'gh-calls.jsonl'
    gh.write_text('#!'+sys.executable+'\nimport json,sys\nfrom pathlib import Path\na=sys.argv[1:]\n'
        +f'with Path({str(gh_log)!r}).open("a") as f:f.write(json.dumps(a)+"\\n")\n'
        +f'p=json.loads(Path({str(pr_file)!r}).read_text())\n'
        +'if a[:2]==["pr","view"]:print(json.dumps(p))\n'
        +'elif a[:2]==["pr","checks"]:print("[]")\n'
        +'elif a[:2]==["pr","list"]:print(json.dumps([dict(p,number=7)]))\n'
        +'elif a[:2]==["auth","status"]:sys.exit(0)\n'
        +'else:print("Synthetic GitHub: operation not available",file=sys.stderr);sys.exit(1)\n')
    gh.chmod(0o755)
    env={k:v for k,v in os.environ.items() if k in {'PATH','SYSTEMROOT','WINDIR','TMPDIR','TEMP','TMP','LANG','LC_ALL'}}
    home=work/'home';home.mkdir()
    temporary=work/'tmp';temporary.mkdir()
    env.update(HOME=str(home),PATH=os.pathsep.join(dict.fromkeys([str(bin_dir),str(Path(sys.executable).parent),str(Path(real_git).parent),*os.defpath.split(os.pathsep)])),GIT_TERMINAL_PROMPT='0',
               GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,TMPDIR=str(temporary),TMP=str(temporary),TEMP=str(temporary))
    def g(*args,cwd=repo):return run(['git',*args],cwd,env)
    g('init','-b','main');g('config','user.name','Fixture');g('config','user.email','fixture@example.invalid')
    cfg={'version':2,'plane':{'api_url':'https://api.plane.so','app_url':'https://app.plane.so',
        'workspace':'synthetic-workspace','project_id':PROJECT,'project_identifier':'DEMO'},
        'github':{'repository':'example/demo-project','base_branch':'main','branch_prefix':'codex'},
        'states':{},'status_sync':{'enabled':False},'completion':{'policy':'manual','manual_label':'manual-acceptance'},
        'sync':{'provider':'native'}}
    (repo/'.plane-devflow.json').write_text(json.dumps(cfg));(repo/'shared.json').write_text('{"features":[]}\n')
    g('add','.');g('commit','-m','fixture base');base=g('rev-parse','HEAD')
    g('init','--bare',str(bare));g('push',str(bare),'main');g('remote','add','origin','https://github.com/example/demo-project.git')
    g('config','remote.origin.pushurl',str(bare));g('fetch','origin','main')
    helper=payload/'scripts/plane_workflow.py'
    def cli(*args,root=repo):return json.loads(run([sys.executable,helper,*args,'--repo',root],work,env,allowed=(0,2) if args[0] in ('task-context','check-task','write-context') else (0,)))
    a=Path(cli('prepare','DEMO-12','--apply')['execution_path'])
    b=Path(cli('prepare','DEMO-13','--apply')['execution_path'])
    for task,target in [('DEMO-12',a),('DEMO-13',b)]:
        plan=cli('task-context',task,root=target)
        scope=work/(task+'-scope.json');scope.write_text('["shared.json"]')
        cli('task-context',task,'--scope-file',scope,'--expected-context-sha256',plan['context_sha256'],'--apply',root=target)
    (b/'shared.json').write_text('{"features":["other-task-dirty"]}\n')
    # Seed a completed local change before delivery / stale-evidence checks.
    if kind in ('writeback','stale','conflict'):
        (a/'shared.json').write_text('{"features":["B"]}\n')
        g('add','shared.json',cwd=a);g('commit','-m','task change',cwd=a)
    head=g('rev-parse','HEAD',cwd=a)
    brief={'goal':'Update selected task features','scope':['shared.json'],'out_of_scope':['Other tasks'],
        'scenarios':['Read features','Preserve other tasks'],
        'criteria':[{'id':'behavior','description':'Selected task features are correct','required':True,'stage':'review'}]}
    digest=hashlib.sha256(json.dumps(brief,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    evidence={'head':head,'brief_sha256':digest,'evidence':'Synthetic fixture baseline verification'}
    data={'brief':brief,'design':{'required':False,'status':'not_required','brief_sha256':digest,'evidence':'Logic-only fixture'},
          'checks':[dict(evidence,id='features',criteria=['behavior'],kind='test',status='passed')],
          'self_review':evidence}
    pr_url='https://github.com/example/demo-project/pull/7'
    if kind in ('writeback','stale'):
        data['delivery']={'pr_url':pr_url,'head':head,'plane_writeback':'pending' if kind=='writeback' else 'confirmed',
                          'evidence':'Synthetic PR already created'}
    if kind=='stale':
        source={'kind':'user_message','reference':'synthetic-message-1','quote':'Accept and merge this exact old commit only.'}
        data['acceptance']=dict(evidence,source=source,criteria=['behavior'])
        data['merge_authorization']=dict(evidence,source=source)
    record=work/'record.json';record.write_text(json.dumps(data))
    plan=cli('task-progress','DEMO-12','--record-file',record,root=a)
    saved=cli('task-progress','DEMO-12','--record-file',record,'--expected-record-sha256',plan['expected_record_sha256'],'--apply',root=a)
    receipt=Path(saved['record_path'])
    if kind=='stale':
        (a/'shared.json').write_text('{"features":["new-unaccepted"]}\n');g('add','shared.json',cwd=a);g('commit','-m','new head',cwd=a)
        head=g('rev-parse','HEAD',cwd=a)
    required_base=base
    if kind=='conflict':
        writer=work/'writer';g('clone','--branch','main',str(bare),str(writer))
        g('config','user.name','Fixture',cwd=writer);g('config','user.email','fixture@example.invalid',cwd=writer)
        (writer/'shared.json').write_text('{"features":["A"]}\n')
        g('add','shared.json',cwd=writer);g('commit','-m','accepted feature A',cwd=writer);g('push','origin','main',cwd=writer)
        required_base=g('rev-parse','HEAD',cwd=writer)
    binding={'version':1,'workspace':cfg['plane']['workspace'],'project_id':PROJECT,'task':'DEMO-12'}
    pr={'url':pr_url,'html_url':pr_url,'number':7,'state':'OPEN','isDraft':False,'headRefOid':head,
        'baseRefName':'main','baseRefOid':base,'mergeCommit':None,'title':'[DEMO-12] Fixture',
        'body':'<!-- plane-devflow '+json.dumps(binding)+' -->','isCrossRepository':False,
        'mergeable':'MERGEABLE','mergeStateStatus':'CLEAN'}
    pr_file.write_text(json.dumps(pr))
    items=[{'id':'22222222-2222-4222-8222-222222222222','identifier':'DEMO-12','sequence_id':12,
        'project_id':PROJECT,'project':PROJECT,'name':'Fixture task','description_html':'<p>Change only shared.json for this task.</p>',
        'labels':[],'state':{'name':'In Progress','group':'started'},'external_id':None,'external_source':None}]
    context={'task_directory':str(a),'other_directory':str(b),'pr_url':pr_url,'old_head':data['self_review']['head']}
    if kind=='lost-create':
        draft={'version':1,'goal':'Two synthetic tasks','tasks':[
            {'key':'page','name':'Build page','description':'Empty list only. No login.','criteria':['Empty list opens'],'depends_on':[]},
            {'key':'save','name':'Save locally','description':'Local storage only. No cloud.','criteria':['Refresh retains data'],'depends_on':['page']}]}
        draft_file=work/'draft.json';draft_file.write_text(json.dumps(draft))
        planned=cli('task-plan','--plan-file',draft_file)
        cli('task-plan','--plan-file',draft_file,'--expected-plan-sha256',planned['plan_id'],'--apply')
        existing=planned['operations'][0]
        items=[dict(existing,id='33333333-3333-4333-8333-333333333333',identifier='DEMO-1',sequence_id=1,
                    project_id=PROJECT,project=PROJECT,labels=[],state={'name':'Backlog','group':'backlog'})]
        context.update(plan_id=planned['plan_id'],draft=draft)
    state={'project':{'id':PROJECT,'identifier':'DEMO','name':'Synthetic project'},'items':items,'comments':[],
           'links':[],'calls':[],'pr_count':1}
    state_file=private/'state.json';state_file.write_text(json.dumps(state))
    (work/'context.json').write_text(json.dumps(context,indent=2))
    protected={str(p):sha(p) for p in (git,gh,pr_file,b/'shared.json',repo/'shared.json',repo/'.plane-devflow.json')}
    if kind=='stale':protected[str(receipt)]=sha(receipt);protected[str(a/'shared.json')]=sha(a/'shared.json')
    return {'work':str(work),'cwd':str(b if kind=='identity' else repo if kind=='lost-create' else a),
            'plugin':str(payload),'helper':str(helper),'task':str(a),'other':str(b),'repo':str(repo),
            'state':str(state_file),'receipt':str(receipt),'gh_log':str(gh_log),'protected':protected,
            'env':env,'head':head,'base':base,'kind':kind,'initial_item_count':len(items),
            'bare':str(bare),'required_base':required_base,
            'remote_refs':g('--git-dir',str(bare),'for-each-ref','--format=%(refname) %(objectname)')}
