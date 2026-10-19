using System;
using System.IO;
using System.Collections.Generic;
using System.Reflection;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Security.Cryptography;
using System.Threading;
using System.Web.Script.Serialization;

public static class ProductPreflightAudit1902 {
 static MethodInfo method;
 static List<object> checks=new List<object>();
 static List<object> outcomes=new List<object>();
 static string root;
 static SecurityIdentifier sid=WindowsIdentity.GetCurrent().User;
 static int failed;
 static string Sha(string path){using(var a=SHA256.Create())using(var f=File.OpenRead(path))return BitConverter.ToString(a.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
 static void Check(string name,bool passed){checks.Add(new{name=name,passed=passed});if(!passed)failed++;}
 static string NewCase(string name){string path=Path.Combine(root,name);Directory.CreateDirectory(path);return path;}
 static Dictionary<string,byte[]> Wanted(string path){return new Dictionary<string,byte[]>(StringComparer.OrdinalIgnoreCase){{path,new byte[]{7,8,9}}};}
 static Exception Invoke(string dir,Dictionary<string,byte[]> wanted){try{method.Invoke(null,new object[]{dir,wanted});return null;}catch(TargetInvocationException ex){return ex.InnerException;}}
 static string Field(Exception error,string field){return error==null?null:Convert.ToString(error.GetType().GetField(field).GetValue(error));}
 static void Record(string name,Exception error){outcomes.Add(new{name=name,success=error==null,type=error==null?null:error.GetType().FullName,stage=Field(error,"Stage"),operation=Field(error,"Operation"),causeHResult=error==null||error.InnerException==null?null:"0x"+error.InnerException.HResult.ToString("X8"),evidence=Field(error,"FailureEvidence")});}
 static void WithAcl(string name,FileSystemAccessRule[] rules,string expectedOperation){
  string dir=NewCase(name);DirectorySecurity original=Directory.GetAccessControl(dir),changed=Directory.GetAccessControl(dir);foreach(var rule in rules)changed.AddAccessRule(rule);Directory.SetAccessControl(dir,changed);
  try{Exception error=Invoke(dir,Wanted("ac8_mouse_aim_010.dll"));Record(name,error);Check(name+"_result",expectedOperation==null?error==null:error!=null&&Field(error,"Stage")=="prepare"&&Field(error,"Operation")==expectedOperation);Check(name+"_no_artifacts_before_acl_restore",Directory.GetFileSystemEntries(dir).Length==0);if(expectedOperation=="preflight-rename")Check(name+"_evidence_captured_before_delete_on_close",Field(error,"FailureEvidence").Contains("Staged metadata: file"));}
  finally{Directory.SetAccessControl(dir,original);foreach(var f in Directory.GetFiles(dir)){var fs=File.GetAccessControl(f);fs.SetAccessRuleProtection(false,false);File.SetAccessControl(f,fs);}}
 }
 public static void Execute(string assembly,string fixtureRoot,string result,string source){
  root=fixtureRoot;Directory.CreateDirectory(root);method=Assembly.LoadFile(Path.GetFullPath(assembly)).GetType("KoreanAIR.Core").GetMethod("PreflightWrites",BindingFlags.Static|BindingFlags.NonPublic);if(method==null)throw new Exception("Actual product PreflightWrites method not found");
  string dir=NewCase("ordinary_new");Exception error=Invoke(dir,Wanted("ac8_mouse_aim_010.dll"));Record("ordinary_new",error);Check("ordinary_new_passes_without_artifacts",error==null&&Directory.GetFileSystemEntries(dir).Length==0);
  dir=NewCase("existing_changed");string target=Path.Combine(dir,"ac8_mouse_aim_010.dll");File.WriteAllBytes(target,new byte[]{1,2});error=Invoke(dir,Wanted("ac8_mouse_aim_010.dll"));Record("existing_changed",error);Check("existing_changed_preflight_preserves_original",error==null&&Convert.ToBase64String(File.ReadAllBytes(target))=="AQI="&&Directory.GetFileSystemEntries(dir).Length==1);
  dir=NewCase("existing_readonly_changed");target=Path.Combine(dir,"ac8_mouse_aim_010.dll");File.WriteAllBytes(target,new byte[]{1,2});File.SetAttributes(target,FileAttributes.ReadOnly);try{error=Invoke(dir,Wanted("ac8_mouse_aim_010.dll"));Record("existing_readonly_changed",error);Check("existing_readonly_changed_refused_before_mutation",error!=null&&Field(error,"Stage")=="prepare"&&Field(error,"Operation")=="preflight-inspect"&&Convert.ToBase64String(File.ReadAllBytes(target))=="AQI="&&Directory.GetFileSystemEntries(dir).Length==1);}finally{File.SetAttributes(target,FileAttributes.Normal);}
  dir=NewCase("existing_readonly_unchanged");target=Path.Combine(dir,"ac8_mouse_aim_010.dll");File.WriteAllBytes(target,new byte[]{7,8,9});File.SetAttributes(target,FileAttributes.ReadOnly);try{error=Invoke(dir,Wanted("ac8_mouse_aim_010.dll"));Record("existing_readonly_unchanged",error);Check("unchanged_readonly_not_unnecessarily_tested",error==null&&Directory.GetFileSystemEntries(dir).Length==1);}finally{File.SetAttributes(target,FileAttributes.Normal);}
  dir=NewCase("target_directory");Directory.CreateDirectory(Path.Combine(dir,"ac8_mouse_aim_010.dll"));error=Invoke(dir,Wanted("ac8_mouse_aim_010.dll"));Record("target_directory",error);Check("target_directory_refused_before_mutation",error!=null&&Field(error,"Operation")=="preflight-inspect"&&Directory.GetFileSystemEntries(dir).Length==1);
  dir=NewCase("new_parent_not_created");error=Invoke(dir,Wanted("missing/nested/ac8_mouse_aim_010.dll"));Record("new_parent_not_created",error);Check("missing_parents_not_speculatively_created",error==null&&Directory.GetFileSystemEntries(dir).Length==0);
  dir=NewCase("parent_occupied_by_file");File.WriteAllBytes(Path.Combine(dir,"occupied"),new byte[]{1,2});error=Invoke(dir,Wanted("occupied/ac8_mouse_aim_010.dll"));Record("parent_occupied_by_file",error);Check("file_parent_refused_without_mutation",error!=null&&Field(error,"Operation")=="preflight-inspect"&&Directory.GetFileSystemEntries(dir).Length==1);
  dir=NewCase("directory_readonly");File.SetAttributes(dir,FileAttributes.ReadOnly);try{error=Invoke(dir,Wanted("ac8_mouse_aim_010.dll"));Record("directory_readonly",error);Check("directory_readonly_is_not_false_failure",error==null&&Directory.GetFileSystemEntries(dir).Length==0);}finally{File.SetAttributes(dir,FileAttributes.Directory);}
  WithAcl("deny_create",new[]{new FileSystemAccessRule(sid,FileSystemRights.CreateFiles,AccessControlType.Deny)},"preflight-create");
  WithAcl("deny_delete_both",new[]{new FileSystemAccessRule(sid,FileSystemRights.DeleteSubdirectoriesAndFiles,AccessControlType.Deny),new FileSystemAccessRule(sid,FileSystemRights.Delete,InheritanceFlags.ObjectInherit,PropagationFlags.InheritOnly,AccessControlType.Deny)},"preflight-rename");
  WithAcl("deny_file_delete_only",new[]{new FileSystemAccessRule(sid,FileSystemRights.Delete,InheritanceFlags.ObjectInherit,PropagationFlags.InheritOnly,AccessControlType.Deny)},null);
  WithAcl("deny_parent_delete_child_only",new[]{new FileSystemAccessRule(sid,FileSystemRights.DeleteSubdirectoriesAndFiles,AccessControlType.Deny)},null);
  dir=NewCase("same_parent_deduplicated");int creates=0,moves=0;using(var watcher=new FileSystemWatcher(dir,"*.tmp")){watcher.NotifyFilter=NotifyFilters.FileName;watcher.Created+=(sender,args)=>{if(args.Name.Length==37&&args.Name[0]=='.')Interlocked.Increment(ref creates);};watcher.Renamed+=(sender,args)=>Interlocked.Increment(ref moves);watcher.EnableRaisingEvents=true;var wanted=Wanted("first.dll");wanted.Add("second.dll",new byte[]{4,5});error=Invoke(dir,wanted);Thread.Sleep(200);watcher.EnableRaisingEvents=false;}Record("same_parent_deduplicated",error);Check("same_parent_deduplicated_passes_no_artifacts",error==null&&Directory.GetFileSystemEntries(dir).Length==0);Check("same_parent_only_one_probe_create",creates==1);Check("same_parent_only_one_probe_rename",moves==1);
  File.WriteAllText(result,new JavaScriptSerializer().Serialize(new{passed=failed==0,checkCount=checks.Count,failedChecks=failed,testedAssembly=assembly,assemblySha256=Sha(assembly),productionSourceSha256=Sha(source),execution=Path.GetExtension(assembly).Equals(".exe",StringComparison.OrdinalIgnoreCase)?"Actual supplied packaged Setup assembly invoked through reflection. Isolated fixtures only; no real game or Setup UI.":"Exact current production PackCore.cs compiled as a library, invoked through reflection. Isolated fixtures only; not real game or packaged Setup.",checks=checks,outcomes=outcomes}));
 }
}
