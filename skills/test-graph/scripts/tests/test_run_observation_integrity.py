"""A Gradle success flag cannot substitute for observed graph/node evidence."""
import json
from pathlib import Path
import sys
import pytest
SCRIPTS=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(SCRIPTS))
import run

@pytest.mark.parametrize('shape',['no_owned_report','missing_report','empty_nodes','incomplete','red_node','own_failed','own_errored','healthy','healthy_reordered'])
def test_graph_green_requires_own_complete_nonempty_report(tmp_path,shape):
    directory=tmp_path/'own';directory.mkdir()
    nodes=[] if shape=='empty_nodes' else [{'nodeId':'observed','status':'failed' if shape in ('red_node','own_failed') else 'errored' if shape=='own_errored' else 'passed'}]
    if shape=='healthy_reordered':nodes=[{'nodeId':'second','status':'passed'},{'nodeId':'first','status':'passed'}]
    summary={'status':'failed' if shape=='own_failed' else 'errored' if shape=='own_errored' else 'passed','execution':{'complete':shape!='incomplete','expectedNodeIds':['observed'],'observedNodeIds':['observed']},'nodes':nodes}
    (directory/'envelope').mkdir()
    for node in nodes:(directory/'envelope'/(node['nodeId']+'.json')).write_text(json.dumps(node))
    if shape=='healthy_reordered':summary['execution'].update(expectedNodeIds=['first','second'],observedNodeIds=['second','first'])
    if shape!='missing_report':(directory/'summary.json').write_text(json.dumps(summary))
    records=[{'event':'scheduled','task':'fixture','graph':True},{'event':'started','task':'fixture','graph':True},
             {'event':'finished','task':'fixture','graph':True,'outcome':'passed','seconds':1,'runDirs':[] if shape=='no_owned_report' else [str(directory)]}]
    result=run.summarize_sweep(['fixture'],records,False)
    assert result['results'][0]['status']==('passed' if shape in ('healthy','healthy_reordered') else 'failed' if shape=='own_failed' else 'errored')

@pytest.mark.parametrize('node_status',[None,'failed','errored','passed'])
def test_machine_outcome_cannot_admit_unobserved_or_nonpassing_nodes(tmp_path,node_status):
    directory=tmp_path/'own';directory.mkdir()
    if node_status is not None:
        (directory/'envelope').mkdir()
        (directory/'envelope/observed.json').write_text(json.dumps({'nodeId':'observed','status':node_status}))
    summary={'mode':'graphs','selection_known':True,'results':[{'graph':'fixture','status':'passed','seconds':1,'run_dirs':[str(directory)],'reason':None,'report_status':'passed'}]}
    outcome=run.build_outcome(summary,None,started=1,ended=2,gradle_rc=0,exit_code=0,argv=['fixture'],continue_after_failure=False,record_dir=tmp_path)
    assert outcome['graphs'][0]['status']==('passed' if node_status=='passed' else 'errored')
    assert outcome['status']==('passed' if node_status=='passed' else 'errored')
    assert outcome['exit_code']==(0 if node_status=='passed' else run.SWEEP_EXIT_ERRORED)
