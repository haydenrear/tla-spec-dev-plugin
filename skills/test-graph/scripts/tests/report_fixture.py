"""Observed report fixtures for schedule tests (not live SDK execution proof)."""
import atexit
import json
from pathlib import Path
import tempfile


def observed_report(directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    node={'nodeId':'fixture.observed','status':'passed','assertions':[{'name':'fixture observation','status':'passed'}],
          'artifacts':[],'processes':[],'metrics':{},'logs':[],'published':{}}
    (directory/'envelope').mkdir(exist_ok=True)
    (directory/'envelope/fixture.observed.json').write_text(json.dumps(node))
    (directory/'execution-scope.json').write_text(json.dumps({'expectedNodeIds':[node['nodeId']]}))
    (directory/'summary.json').write_text(json.dumps({'status':'passed',
        'execution':{'complete':True,'expectedNodeIds':[node['nodeId']],'observedNodeIds':[node['nodeId']]},'nodes':[node]}))
    return str(directory)


def temporary_observed_report():
    holder=tempfile.TemporaryDirectory(prefix='testgraph-observed-fixture-')
    atexit.register(holder.cleanup)
    return observed_report(holder.name)
