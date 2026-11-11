"""Observation contracts at assertion construction and actual node termination."""
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest
from testgraphsdk import NodeResult,NodeSpec
from testgraphsdk.result import NodeStatus
import testgraphsdk.runner as runner

@pytest.mark.parametrize('value',[[],{},None,'','unmeasured',['unmeasured'],{'missing':True},1])
def test_assertion_requires_true_boolean(value):
    assert NodeResult.pass_('fixture').assertion('observed',value).status==NodeStatus.FAILED

@pytest.mark.parametrize('observed,expected',[(False,'failed'),(True,'passed')])
def test_assertion_terminal_requires_observation(tmp_path,monkeypatch,observed,expected):
    spec=NodeSpec('fixture').kind('assertion')
    monkeypatch.setattr(runner.NodeContext,'parse',lambda:SimpleNamespace(node_id=spec.id))
    monkeypatch.setattr(runner,'_configure_node_observability',lambda spec:(None,{}))
    monkeypatch.setattr(runner,'_record_node_event',lambda *a,**kw:None)
    monkeypatch.setattr(runner,'_flush_observability_before_exit',lambda **kw:True)
    monkeypatch.setattr(runner,'_exit_process',lambda code:None)
    out=tmp_path/'result.json';calls=[]
    monkeypatch.setattr(sys,'argv',['fixture','--result-out='+str(out)])
    def body(ctx):
        calls.append(ctx.node_id)
        result=NodeResult.pass_(spec.id)
        return result.assertion('actual observation',True) if observed else result
    runner.node(spec)(body)()
    result=json.loads(out.read_text())
    assert calls==[spec.id] and result['nodeId']==spec.id
    assert result['status']==expected

@pytest.mark.parametrize('status',[NodeStatus.FAILED,NodeStatus.ERRORED,NodeStatus.SKIPPED])
def test_nonpassing_status_is_preserved_without_observations(status):
    result=NodeResult('fixture',status=status).assertion('unobserved',None)
    assert result.status==status

def test_fluent_builder_still_starts_green_before_termination():
    assert NodeResult.pass_('fixture').status==NodeStatus.PASSED
