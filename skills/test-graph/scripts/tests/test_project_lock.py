"""Actual canonical commands contend using tiny fake gradlew children, never Java."""
from __future__ import annotations
import json,os,signal,subprocess,sys,tempfile,time,unittest
from pathlib import Path
SCRIPTS=Path(__file__).resolve().parents[1]
FAKE='''#!PYTHON
import json,os,sys,time
from pathlib import Path
phase=PHASE
with open(os.environ['LOCK_MARKERS'],'a')as f:f.write(json.dumps({'phase':phase,'pid':os.getpid(),'argv':sys.argv[1:]})+'\\n')
gate=json.loads(os.environ.get('LOCK_GATES','{}')).get(phase)
if gate:
 deadline=time.monotonic()+10
 while not Path(gate).exists():
  if time.monotonic()>deadline:raise SystemExit('test gate deadline')
  time.sleep(.01)
if phase=='dot':print('digraph fixture { a -> b; }')
if phase=='render':Path(sys.argv[sys.argv.index('-o')+1]).write_bytes(b'controlled fake PNG, not native rendering')
raise SystemExit(int(os.environ.get('LOCK_EXIT','0')))
'''

@unittest.skipUnless(os.name=='posix','POSIX flock target; unsupported platform fails explicitly at execution')
class CanonicalProjectLock(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name);self.children=[];self.root=self.fixture('project')
 def tearDown(self):
  for proc in self.children:
   try:os.killpg(proc.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   proc.communicate(timeout=3)
  self.temp.cleanup()
 def fixture(self,name):
  root=self.base/name;root.mkdir();(root/'settings.gradle.kts').write_text('rootProject.name="fixture"\n');(root/'build.gradle.kts').write_text('validationGraph { }\n');bin=root/'bin';bin.mkdir()
  for path,phase in [(root/'gradlew',"'dot' if 'validationGraphDot' in sys.argv else 'plan' if 'validationPlanGraph' in sys.argv else 'run'"),(bin/'dot',"'render'")]:
   path.write_text(FAKE.replace('PYTHON',sys.executable).replace('PHASE',phase));path.chmod(0o700)
  return root
 def environment(self,root,gates=None,exitcode=0):
  env=dict(os.environ,PATH=str(root/'bin'),PYTHONDONTWRITEBYTECODE='1',LOCK_MARKERS=str(root/'markers'),LOCK_GATES=json.dumps(gates or {}),LOCK_EXIT=str(exitcode))
  # These controls do not exercise caller-supplied JVM overrides; existing guard tests do.
  for key in ['GRADLE_OPTS','JAVA_OPTS','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','JDK_JAVA_OPTIONS']:env.pop(key,None)
  return env
 def command(self,script,root=None):return [sys.executable,str(SCRIPTS/script),'fixture','--test-graph-root',str(root or self.root)]
 def launch(self,script,root=None,gates=None):
  root=root or self.root;p=subprocess.Popen(self.command(script,root),env=self.environment(root,gates),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True);self.children.append(p);return p
 def wait_phase(self,phase,root=None):
  root=root or self.root;deadline=time.monotonic()+5
  while time.monotonic()<deadline:
   rows=self.markers(root)
   if any(x['phase']==phase for x in rows):return
   time.sleep(.01)
  self.fail('fake child did not reach '+phase)
 def markers(self,root=None):
  p=(root or self.root)/'markers';return [json.loads(s)for s in p.read_text().splitlines()]if p.exists()else[]
 def call(self,script,root=None,**kwargs):
  root=root or self.root;return subprocess.run(self.command(script,root),env=self.environment(root,**kwargs),capture_output=True,text=True,timeout=5)
 def assert_busy(self,result):self.assertNotEqual(result.returncode,0);self.assertIn('busy',result.stderr.lower())
 def test_run_contends_with_alias_without_launching_child(self):
  gate=self.base/'release';owner=self.launch('run.py',gates={'run':str(gate)});self.wait_phase('run');alias=self.base/'alias';alias.symlink_to(self.root,target_is_directory=True)
  manifest=self.root/'provider-bindings.json';manifest.write_text('deliberately invalid provider input')
  try:
   self.assert_busy(self.call('run.py',alias));self.assertEqual(len(self.markers()),1);self.assertEqual(manifest.read_text(),'deliberately invalid provider input')
  finally:manifest.unlink();gate.touch()
  out,err=owner.communicate(timeout=5);self.assertEqual(owner.returncode,0,err)
 def test_discover_holds_both_calls_and_final_render(self):
  gates={p:str(self.base/('release-'+p))for p in ['plan','dot','render']};owner=self.launch('discover.py',gates=gates)
  for phase in ['plan','dot','render']:
   self.wait_phase(phase);before=len(self.markers());self.assert_busy(self.call('run.py'));self.assertEqual(len(self.markers()),before);Path(gates[phase]).touch()
  out,err=owner.communicate(timeout=5);self.assertEqual(owner.returncode,0,err);self.assertIn('digraph fixture',(self.root/'docs/fixture.dot').read_text());self.assertTrue((self.root/'docs/fixture.png').is_file())
 def test_run_blocks_discover_and_separate_project_proceeds(self):
  gate=self.base/'release';owner=self.launch('run.py',gates={'run':str(gate)});self.wait_phase('run');self.assert_busy(self.call('discover.py'));other=self.fixture('other');self.assertEqual(self.call('run.py',other).returncode,0);self.assertEqual(len(self.markers()),1);gate.touch();owner.communicate(timeout=5)
 def test_nonzero_and_error_release(self):
  failed=self.call('run.py',exitcode=7);self.assertEqual(failed.returncode,7);self.assertEqual(self.call('run.py').returncode,0)
  wrapper=self.root/'gradlew';wrapper.chmod(0o600)
  try:self.assertNotEqual(self.call('run.py').returncode,0)
  finally:wrapper.chmod(0o700)
  self.assertEqual(self.call('run.py').returncode,0)
 def test_stable_inode_and_stale_text_not_authority(self):
  self.assertEqual(self.call('run.py').returncode,0);lock=self.root/'build/.test-graph-execution.lock';inode=lock.stat().st_ino;lock.write_text('{"pid":999999999,"command":"stale"}')
  self.assertEqual(self.call('discover.py').returncode,0);self.assertEqual(lock.stat().st_ino,inode)
 def test_help_and_invalid_cli_create_no_build_or_child(self):
  for script,args in [('run.py',['--help']),('run.py',[]),('discover.py',['--unknown'])]:
   result=subprocess.run([sys.executable,str(SCRIPTS/script),*args,'--test-graph-root',str(self.root)],env=self.environment(self.root),capture_output=True,text=True,timeout=5)
   self.assertEqual(result.returncode==0,args==['--help'])
  self.assertFalse((self.root/'build').exists());self.assertEqual(self.markers(),[])
 def test_parent_death_releases_os_lock_not_child_cleanup_proof(self):
  gate=self.base/'release';owner=self.launch('run.py',gates={'run':str(gate)});self.wait_phase('run');owner.kill();owner.wait(timeout=3)
  try:self.assertEqual(self.call('run.py').returncode,0)
  finally:gate.touch()
  owner.communicate(timeout=5)
if __name__=='__main__':unittest.main()
