///usr/bin/env jbang "$0" "$@" ; exit $?
//SOURCES /Users/hayde/IdeaProjects/skill-manager/test_graph/sources/onboarding/OnboardingDocsAndScriptsStatic.java
//SOURCES /Users/hayde/IdeaProjects/skill-manager/test_graph/sdk/java/src/main/java/com/hayden/testgraphsdk/sdk/*.java
import java.nio.file.*; import java.util.*; import java.util.regex.*;
// Calls the node's real SCRIPT_REF and claimsOwnScriptsDir on every markdown doc it scans.
public class TraceWt {
  public static void main(String[] a) throws Exception {
    Path root=Path.of(a[0]); String own=root.getFileName().toString();
    List<Path> docs=new ArrayList<>(); try(var s=Files.list(root.resolve("references"))){s.filter(p->p.toString().endsWith(".md")).sorted().forEach(docs::add);} docs.add(root.resolve("SKILL.md"));
    for(Path d:docs){String t=Files.readString(d);Matcher m=OnboardingDocsAndScriptsStatic.SCRIPT_REF.matcher(t);
      while(m.find()){ if(!m.group(1).equals("wt"))continue;
        int line=t.substring(0,m.start()).split("\n",-1).length;
        boolean c=OnboardingDocsAndScriptsStatic.claimsOwnScriptsDir(t,m.start(),own);
        String before=t.substring(Math.max(0,m.start()-14),m.start()).replace("\n"," ");
        System.out.println(root.relativize(d)+":"+line+" before=["+before+"] claimedAsOwn="+c);}}
  }
}
