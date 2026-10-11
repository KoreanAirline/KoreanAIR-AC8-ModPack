using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Diagnostics;
using System.Reflection;
using System.Collections.Generic;
using KoreanAIR;

class InstallerAudit {
 static string basePath;
 static int failures;
 static string Case(string name) { string p=Path.Combine(basePath,name,"game");Directory.CreateDirectory(p);return p; }
 static void Put(string root,string relative,string text) { string p=Core.Safe(root,relative);Directory.CreateDirectory(Path.GetDirectoryName(p));File.WriteAllText(p,text,new UTF8Encoding(false)); }
 static State StateFor(string root) { string backup=Path.Combine(Path.GetDirectoryName(root),"backups");Directory.CreateDirectory(backup);return new State{root=Path.GetFullPath(root),backup=backup}; }
 static void Save(State s) { Put(s.root,Core.Folder+"/installed.json",Core.Json.Serialize(s)); }
 static FileState Owned(string root,string path,bool mutable=false,string original=null) { return new FileState{path=path,hash=Core.HashFile(Core.Safe(root,path)),mutable=mutable,original=original}; }
 static void Result(string name,bool pass,string detail) { Console.WriteLine((pass?"PASS ":"FAIL ")+name+": "+detail);if(!pass)failures++; }
 static void Junction(string link,string target) {
  if(!Path.GetFullPath(link).StartsWith(basePath+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)||!Path.GetFullPath(target).StartsWith(basePath+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new Exception("Unsafe fixture junction path.");
  Directory.CreateDirectory(Path.GetDirectoryName(link));Directory.CreateDirectory(target);
  var info=new ProcessStartInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System),"cmd.exe"),"/c mklink /J \""+link+"\" \""+target+"\""){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true};
  using(var p=Process.Start(info)){p.StandardOutput.ReadToEnd();string error=p.StandardError.ReadToEnd();p.WaitForExit();if(p.ExitCode!=0)throw new Exception("Junction fixture failed: "+error);}
  if((File.GetAttributes(link)&FileAttributes.ReparsePoint)==0)throw new Exception("Fixture is not a junction.");
 }
 static void RemoveJunction(string p) { if(Directory.Exists(p)&&(File.GetAttributes(p)&FileAttributes.ReparsePoint)!=0)Directory.Delete(p,false); }
 static void ModList() {
  string root=Case("mod-list");string rel="Game/Binaries/Win64/UE4SS/Mods/mods.txt";
  Put(root,rel,"AC8MouseAim : 1\r\nOtherMod : 1\r\n");State s=StateFor(root);s.files.Add(Owned(root,rel,true));Save(s);Core.Uninstall(root);
  bool pass=File.Exists(Core.Safe(root,rel))&&File.ReadAllText(Core.Safe(root,rel)).Contains("OtherMod : 1")&&!File.ReadAllText(Core.Safe(root,rel)).Contains("AC8MouseAim");
  Result("uninstall-preserves-other-mod-rows",pass,pass?"Unrelated row retained":"The shared mod list or unrelated row was removed");
 }
 static void MissingBackup() {
  string root=Case("missing-backup");string first="Game/Binaries/Win64/owned-one.bin",second="Game/Binaries/Win64/owned-two.bin";
  Put(root,first,"first installed file");Put(root,second,"second installed file");State s=StateFor(root);s.files.Add(Owned(root,first));s.files.Add(Owned(root,second,false,"original/missing.bin"));Save(s);
  bool threw=false;try{Core.Uninstall(root);}catch{threw=true;}
  bool intact=File.Exists(Core.Safe(root,first))&&File.Exists(Core.Safe(root,second))&&File.Exists(Core.Safe(root,Core.Folder+"/installed.json"));
  Result("missing-backup-leaves-installation-intact",threw&&intact,intact?"Installation intact after refusal":"Earlier owned files were removed before the missing backup was detected");
 }
 static void PruneLink() {
  string root=Case("prune-link");string target=Path.Combine(Path.GetDirectoryName(root),"outside-game");string empty=Path.Combine(target,"must-survive");Directory.CreateDirectory(empty);
  string link=Path.Combine(root,Core.Folder,"unknown-link");Junction(link,target);
  try{typeof(Core).GetMethod("Prune",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{root});Result("prune-does-not-follow-junction",Directory.Exists(empty),Directory.Exists(empty)?"Sibling folder preserved":"An empty sibling folder outside the selected game was deleted through a junction");}finally{RemoveJunction(link);}
 }
 static void RootLink() {
  string root=Case("root-link");string target=Path.Combine(Path.GetDirectoryName(root),"redirect-target");string link=Path.Combine(Path.GetDirectoryName(root),"linked-game");Junction(link,target);
  try{bool refused=false;try{Core.Safe(link,"some-file.bin");}catch{refused=true;}Result("redirected-root-refused",refused,refused?"Root junction refused":"Root junction passed containment checks");}finally{RemoveJunction(link);}
 }
 static void SuspendRollback() {
  string root=Case("suspend-rollback");string first="Game/Binaries/Win64/dinput8.dll",second="Game/Binaries/Win64/dwmapi.dll";
  Put(root,first,"loader one");Put(root,second,"loader two");State s=StateFor(root);s.files.Add(Owned(root,first));s.files.Add(Owned(root,second));Save(s);Put(root,second,"changed externally");
  bool refused=false;try{Core.Suspend(root,true);}catch{refused=true;}
  bool intact=File.ReadAllText(Core.Safe(root,first))=="loader one"&&File.ReadAllText(Core.Safe(root,second))=="changed externally"&&!Core.ReadState(root).suspended;
  Result("suspend-rollback-preserves-files",refused&&intact,intact?"Moved files restored after failure":"Partial suspension remained after failure");
 }
 static int Main(string[] args) {
  if(args.Length!=1)throw new Exception("Pass the isolated fixture output directory.");basePath=Path.GetFullPath(args[0]).TrimEnd(Path.DirectorySeparatorChar);
  if(!basePath.Contains(Path.DirectorySeparatorChar+"tests"+Path.DirectorySeparatorChar))throw new Exception("Fixtures must remain under the tests directory.");
  if(Directory.Exists(basePath))throw new Exception("Use a new fixture directory to preserve previous evidence.");Directory.CreateDirectory(basePath);
  ModList();MissingBackup();PruneLink();RootLink();SuspendRollback();Console.WriteLine("Failures: "+failures);return failures==0?0:1;
 }
}
