"""Offline grader/fixture tests; model execution is explicitly opt-in."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'evals'))
import execution
import execution_fixture as fixtures
import fixture_mcp


def event(command,output='',code=0):
    return {'type':'item.completed','item':{'type':'command_execution','command':command,
                                           'aggregated_output':output,'exit_code':code}}


class ExecutionTests(unittest.TestCase):
    def fixture(self,kind):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        f=fixtures.build(temporary.name,ROOT/'plugins/plane-devflow',kind)
        f['payload_sha256']=execution.fingerprint(f['plugin'])
        return f

    def case(self,kind):
        return next(c for c in json.loads((ROOT/'evals/execution_cases.json').read_text()) if c['fixture']==kind)

    def grade(self,f,extra=()):return execution.grade(self.case(f['kind']),f,[event('cat plugin/skills/'+self.case(f['kind'])['skill']+'/SKILL.md'),*extra])

    def test_claimed_success_without_side_effects_cannot_pass(self):
        f=self.fixture('identity')
        result=execution.grade(self.case('identity'),f,[{'type':'item.completed','item':{'type':'agent_message','text':'Everything passed'}}])
        self.assertFalse(result['passed'])
        self.assertIn('selected_task_change_missing',result['failures'])
        self.assertIn('no_command_execution',result['failures'])

    def test_selected_task_and_protected_other_task_both_matter(self):
        f=self.fixture('identity');Path(f['task'],'shared.json').write_text('{"features":["task-12"]}')
        self.assertTrue(self.grade(f,[event('python plane_workflow.py write-context DEMO-12',json.dumps({'repository_writes_allowed':True,'mode':'write','task':'DEMO-12','path':f['task']}))])['passed'])
        Path(f['other'],'shared.json').write_text('{"features":["stolen"]}')
        self.assertFalse(self.grade(f,[event('python plane_workflow.py write-context DEMO-12',json.dumps({'repository_writes_allowed':True,'mode':'write','task':'DEMO-12','path':f['task']}))])['passed'])

    def test_payload_or_adapter_tampering_is_detected(self):
        f=self.fixture('identity');Path(f['task'],'shared.json').write_text('{"features":["task-12"]}')
        p=Path(f['plugin'],'scripts/plane_workflow.py');p.write_text(p.read_text()+'\n# changed\n')
        self.assertIn('skill_payload_modified',self.grade(f,[event('write-context')])['failures'])

    def test_stale_gate_is_executed_and_receipt_remains_unchanged(self):
        f=self.fixture('stale')
        args=[sys.executable,f['helper'],'check-task','DEMO-12','--repo',f['task'],'--stage','merge']
        p=subprocess.run(args,env=f['env'],cwd=f['work'],text=True,capture_output=True)
        self.assertEqual(p.returncode,2)
        self.assertIn('merge_authorization_missing_or_stale',p.stdout)
        self.assertTrue(self.grade(f,[event('check-task DEMO-12 --stage merge',p.stdout,p.returncode)])['passed'])
        self.assertFalse(self.grade(f,[event('check-task DEMO-12 --stage merge','unrelated failure',2)])['passed'])

    def test_lost_reply_deduplicates_by_correlation_and_requires_readback(self):
        f=self.fixture('lost-create');state=json.loads(Path(f['state']).read_text());ctx=json.loads(Path(f['work'],'context.json').read_text())
        args={'action':'create','project_id':fixtures.PROJECT,'name':'Save locally','description_html':'<p>Local only</p>',
              'external_id':'task-plan:'+ctx['plan_id']+':save','external_source':'plane-devflow'}
        fixture_mcp.invoke(state,'workitem',{'action':'list_archived','project_id':fixtures.PROJECT})
        row=fixture_mcp.invoke(state,'workitem',args)
        fixture_mcp.invoke(state,'workitem',{'action':'retrieve','project_id':fixtures.PROJECT,'workitem_id':row['id']})
        Path(f['state']).write_text(json.dumps(state))
        self.assertTrue(self.grade(f,[event('task-plan')])['passed'])
        fixture_mcp.invoke(state,'workitem',args);Path(f['state']).write_text(json.dumps(state))
        self.assertFalse(self.grade(f,[event('task-plan')])['passed'])

    def test_writeback_requires_effects_readback_and_receipt_confirmation(self):
        f=self.fixture('writeback');state=json.loads(Path(f['state']).read_text())
        for tool,more in [('workitem_comment',{'comment_html':'<p>Report</p>','external_id':'repo:7:delivery'}),
                          ('workitem_link',{'url':'https://github.com/example/demo-project/pull/7'})]:
            fixture_mcp.invoke(state,tool,dict(action='create',project_id=fixtures.PROJECT,workitem_id=state['items'][0]['id'],**more))
            fixture_mcp.invoke(state,tool,dict(action='list',project_id=fixtures.PROJECT,workitem_id=state['items'][0]['id']))
        Path(f['state']).write_text(json.dumps(state))
        receipt=json.loads(Path(f['receipt']).read_text());receipt['data']['delivery']['plane_writeback']='confirmed';Path(f['receipt']).write_text(json.dumps(receipt))
        self.assertTrue(self.grade(f)['passed'])
        state['links']=[];Path(f['state']).write_text(json.dumps(state));self.assertFalse(self.grade(f)['passed'])

    def test_real_conflict_merge_preserves_both_behaviors_and_other_work(self):
        f=self.fixture('conflict');task=Path(f['task'])
        args=[sys.executable,f['helper'],'sync-task','DEMO-12','--repo',str(task),'--apply']
        p=subprocess.run(args,env=f['env'],cwd=f['work'],capture_output=True,text=True)
        self.assertIn('conflict',p.stdout.lower())
        (task/'shared.json').write_text('{"features":["A","B"]}\n')
        fixtures.run(['git','add','shared.json'],task,f['env']);fixtures.run(['git','commit','-m','resolve both'],task,f['env'])
        self.assertTrue(self.grade(f,[event('sync-task --apply',p.stdout,p.returncode)])['passed'])
        (task/'shared.json').write_text('{"features":["B"]}\n');self.assertFalse(self.grade(f,[event('sync-task')])['passed'])

    def test_synthetic_mcp_transport_has_persistent_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder)/'state.json';state.write_text(json.dumps({'project':{},'items':[],'comments':[],'links':[],'calls':[]}))
            requests=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}},
                      {'jsonrpc':'2.0','method':'notifications/initialized'},
                      {'jsonrpc':'2.0','id':2,'method':'tools/list'},
                      {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'workspace','arguments':{'action':'retrieve'}}}]
            p=subprocess.run([sys.executable,str(ROOT/'evals/fixture_mcp.py'),str(state)],input='\n'.join(json.dumps(r) for r in requests)+'\n',capture_output=True,text=True,check=True)
            replies=[json.loads(l) for l in p.stdout.splitlines()]
            self.assertEqual(len(replies),3);self.assertEqual(len(replies[1]['result']['tools']),5)
            self.assertEqual(json.loads(state.read_text())['calls'][0]['tool'],'workspace')

    def test_runtime_failure_stays_unverified(self):
        with tempfile.TemporaryDirectory() as folder:
            proc=Mock();proc.communicate.return_value=('','model unavailable');proc.returncode=1
            with patch.object(execution,'preflight',return_value='fixture'),patch.object(execution.subprocess,'Popen',return_value=proc),patch.object(execution,'build',return_value={'plugin':str(ROOT/'plugins/plane-devflow'),'work':folder,'cwd':folder,'repo':folder,'state':folder+'/state','env':{'PATH':'/usr/bin:/bin'}}),patch.object(execution.subprocess,'check_output',return_value='fixture-cli'):
                result=execution.execute(self.case('identity'),ROOT/'plugins/plane-devflow',Path(folder)/'run',1)
            self.assertEqual(result['status'],'unverified');self.assertNotIn('passed',result)

    def test_usage_limit_stops_new_sessions_and_marks_remaining_unverified(self):
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'run'
            limited={'case':'EXEC-IDENTITY','status':'unverified','error':'model_usage_limit'}
            with patch.object(sys,'argv',['execution.py','--output',str(out)]),patch.object(execution,'execute',return_value=limited) as invoke:
                self.assertEqual(execution.main(),1)
            summary=json.loads((out/'summary.json').read_text())
            self.assertEqual(invoke.call_count,1)
            self.assertEqual(summary['expected'],5)
            self.assertEqual(summary['passed'],0)
            self.assertEqual(sum(r.get('error')=='not_run_after_usage_limit' for r in summary['results']),4)

    def test_timeout_is_unverified_and_stops_owned_process_group(self):
        with tempfile.TemporaryDirectory() as folder:
            proc=Mock();proc.communicate.side_effect=[subprocess.TimeoutExpired('fixture',1),(None,None)];proc.returncode=-15;proc.pid=12345
            with patch.object(execution,'preflight',return_value='fixture'),patch.object(execution.subprocess,'Popen',return_value=proc),patch.object(execution,'build',return_value={'plugin':str(ROOT/'plugins/plane-devflow'),'work':folder,'cwd':folder,'repo':folder,'state':folder+'/state','env':{'PATH':'/usr/bin:/bin'}}),patch.object(execution.subprocess,'check_output',return_value='fixture-cli'),patch.object(execution.os,'killpg',create=True) as stop:
                result=execution.execute(self.case('identity'),ROOT/'plugins/plane-devflow',Path(folder)/'run',1)
            self.assertEqual(result['status'],'unverified');self.assertEqual(result['error'],'timeout')
            if execution.os.name=='posix':stop.assert_called_once_with(12345,execution.signal.SIGTERM)
            self.assertTrue((Path(folder)/'run/events.jsonl').exists())

    def test_invalid_fixture_ids_or_missing_criteria_are_rejected(self):
        good=self.case('identity')
        for changes in ({'id':'../escape'},{'fixture':'unknown'},{'requirements':[]},{'request':''}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):execution.validate_cases([{**good,**changes}])
        with self.assertRaises(ValueError):execution.validate_cases([good,good])
