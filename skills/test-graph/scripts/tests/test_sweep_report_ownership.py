"""The real Gradle init ledger records only its task's allocation authority."""
import json
import os
from pathlib import Path
import pytest
SKILL_ROOT=Path(__file__).resolve().parents[2]
UNIT=SKILL_ROOT.parents[1]
@pytest.mark.parametrize('foreign,owned',[(False,True),(True,True),(True,False)])
def test_sweep_records_only_its_owned_report(tmp_path,monkeypatch,foreign,owned):
    import os
    import subprocess
    unit=UNIT
    project=tmp_path/'ledger-fixture';project.mkdir()
    (project/'settings.gradle').write_text("rootProject.name='ownership-fixture'\n")
    (project/'build.gradle').write_text('''
import org.gradle.api.tasks.Internal
class RunTestGraphTask extends DefaultTask {
    @Internal final reportRoot = project.objects.directoryProperty()
    @Internal File executedReportDirectory
    @TaskAction void run() {
        def root=reportRoot.get().asFile
        root.mkdirs()
        if (System.getenv('FIXTURE_OWNED') == 'true') {
            executedReportDirectory=new File(root,'owned')
            executedReportDirectory.mkdirs()
        }
        if (System.getenv('FIXTURE_FOREIGN') == 'true') new File(root,'foreign').mkdirs()
    }
}
tasks.register('fixture',RunTestGraphTask) { reportRoot.set(layout.buildDirectory.dir('reports')) }
''')
    ledger=project/'ledger.jsonl'
    env=os.environ.copy();env.update(TEST_GRAPH_SWEEP_LEDGER=str(ledger),FIXTURE_FOREIGN=str(foreign).lower(),FIXTURE_OWNED=str(owned).lower())
    command=[str(SKILL_ROOT/'project_sdk_sources/gradlew'),'-p',str(project),'--no-daemon','--max-workers=1','--console=plain','-Dorg.gradle.jvmargs=-Xmx256m -XX:MaxMetaspaceSize=256m','--init-script',str(unit/'skills/test-graph/scripts/sweep-ledger.init.gradle'),'fixture']
    process=subprocess.run(command,env=env,capture_output=True,text=True,timeout=90)
    (project/'gradle.stdout').write_text(process.stdout);(project/'gradle.stderr').write_text(process.stderr)
    assert process.returncode==0,process.stdout[-1500:]+process.stderr[-1500:]
    finished=[json.loads(line) for line in ledger.read_text().splitlines() if json.loads(line)['event']=='finished']
    graph=[row for row in finished if row['task']=='fixture']
    assert len(graph)==1
    assert graph[0]['runDirs']==([str(project/'build/reports/owned')] if owned else [])
