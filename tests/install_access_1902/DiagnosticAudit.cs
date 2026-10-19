using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using KoreanAIR;

public static class DiagnosticAudit1902 {
 static readonly List<object> Checks=new List<object>();
 static void Check(string name,bool passed){Checks.Add(new{name=name,passed=passed});if(!passed)throw new Exception(name);}
 static object Field(object value,string name){var field=value.GetType().GetField(name,BindingFlags.Public|BindingFlags.Instance);Check("field_"+name+"_readonly",field!=null&&field.IsInitOnly);return field.GetValue(value);}
 static string Text(object value,string name){return Convert.ToString(Field(value,name));}
 static PackWriteException Failure(string target,byte[] bytes){try{Core.Atomic(target,bytes);}catch(PackWriteException ex){return ex;}throw new Exception("Expected write failure: "+target);}
 sealed class SyntheticIOException:IOException {public SyntheticIOException(int hr):base("Synthetic diagnostic cause"){HResult=hr;}}
 static Exception Thrown(Exception ex){try{throw ex;}catch(Exception caught){return caught;}}
 public static int Execute(string reportPath){
  Checks.Clear();string directory=Path.GetDirectoryName(Path.GetFullPath(reportPath));Directory.CreateDirectory(directory);
  string root=Path.Combine(directory,"diagnostic_fixture_"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(root);
  string priorTemp=Environment.GetEnvironmentVariable("TEMP"),priorTmp=Environment.GetEnvironmentVariable("TMP");
  bool passed=false;string error=null;byte[] old={1,2},next={3,4,5};
  try{
   // Restrict the production error log to this process's isolated fixture.
   Environment.SetEnvironmentVariable("TEMP",root);Environment.SetEnvironmentVariable("TMP",root);
   Check("error_log_isolated",Path.GetFullPath(Path.GetTempPath()).TrimEnd('\\')==Path.GetFullPath(root).TrimEnd('\\'));
   string target=Path.Combine(root,"owned.ini");Core.Atomic(target,old);File.SetAttributes(target,FileAttributes.ReadOnly);
   PackWriteException readOnly=Failure(target,next);string evidence=Text(readOnly,"FailureEvidence"),temporary=Text(readOnly,"Temporary");
   Check("readonly_commit_replace",readOnly.Stage=="commit"&&Text(readOnly,"Operation")=="replace");
   Check("readonly_cause_hresult",(int)Field(readOnly,"CauseHResult")==unchecked((int)0x80070005)&&(int?)Field(readOnly,"Win32Error")==5);
   Check("readonly_snapshot_before_cleanup",evidence.Contains("ReadOnly")&&evidence.Contains("Staged metadata: file;")&&!File.Exists(temporary));
   File.SetAttributes(target,FileAttributes.Normal);Check("snapshot_survives_attribute_change",Text(readOnly,"FailureEvidence")==evidence);
   Check("readonly_original_preserved",File.ReadAllBytes(target).SequenceEqual(old));
   string collision=Path.Combine(root,"directory_target.dll");Directory.CreateDirectory(collision);var create=Failure(collision,next);
   Check("directory_collision_create_move",create.Stage=="commit"&&Text(create,"Operation")=="create-move"&&Text(create,"FailureEvidence").Contains("Target metadata: directory;"));
   Check("directory_collision_unchanged",Directory.Exists(collision)&&Directory.GetFileSystemEntries(collision).Length==0);
   string parentFile=Path.Combine(root,"parent_file");File.WriteAllBytes(parentFile,old);var prepare=Failure(Path.Combine(parentFile,"target.dll"),next);
   Check("prepare_is_wrapped",prepare.Stage=="prepare"&&Text(prepare,"Operation")=="prepare"&&Text(prepare,"Temporary")==""&&Text(prepare,"FailureEvidence").Contains("Parent metadata: file;"));
   Check("prepare_parent_preserved",File.ReadAllBytes(parentFile).SequenceEqual(old));
   using(var held=File.Open(target,FileMode.Open,FileAccess.Read,FileShare.None)){
    var locked=Failure(target,next);Check("sharing_failure_exact_hresult",locked.Stage=="commit"&&Text(locked,"Operation")=="replace"&&(int?)Field(locked,"Win32Error")==32);
   }
   Core.AtomicBeforeCommit=(p,tmp)=>File.Delete(tmp);var lost=Failure(target,next);Core.AtomicBeforeCommit=null;
   Check("missing_staged_snapshot",lost.Stage=="commit"&&Text(lost,"Operation")=="replace"&&Text(lost,"FailureEvidence").Contains("Staged metadata: missing file;")&&File.ReadAllBytes(target).SequenceEqual(old));
   var plain=new PackWriteException(target,"commit",Thrown(new SyntheticIOException(unchecked((int)0x800700E1))));
   Check("legacy_constructor_kept",plain.Target==target&&plain.Stage=="commit"&&(int?)Field(plain,"Win32Error")==225);
   var managed=new PackWriteException(target,"write",new SyntheticIOException(unchecked((int)0x80131620)));
   Check("managed_hresult_not_mislabelled_win32",Field(managed,"Win32Error")==null);
   var rollback=typeof(Core).GetMethod("Rollback",BindingFlags.Static|BindingFlags.NonPublic);var initiating=Thrown(new IOException("initiating diagnostic failure"));
   File.WriteAllBytes(target,next);rollback.Invoke(null,new object[]{root,new[]{new KeyValuePair<string,byte[]>("owned.ini",old)},initiating});
   Check("rollback_complete_recorded",Convert.ToString(initiating.Data["Pack.RollbackStatus"])=="completed"&&Convert.ToInt32(initiating.Data["Pack.RollbackChecked"])==1&&Convert.ToInt32(initiating.Data["Pack.RollbackCompleted"])==1&&File.ReadAllBytes(target).SequenceEqual(old));
   AggregateException aggregate=null;
   try{rollback.Invoke(null,new object[]{root,new[]{new KeyValuePair<string,byte[]>("directory_target.dll",old)},initiating});}catch(TargetInvocationException ex){aggregate=ex.InnerException as AggregateException;}
   Check("rollback_incomplete_preserves_all_errors",aggregate!=null&&aggregate.InnerExceptions.Count==2&&Object.ReferenceEquals(aggregate.InnerExceptions[0],initiating)&&Convert.ToString(aggregate.Data["Pack.RollbackStatus"])=="incomplete"&&Convert.ToString(aggregate.Data["Pack.RollbackFailures"])=="directory_target.dll");
   var outer=new AggregateException("Diagnostic aggregate",readOnly,plain,managed,aggregate);string log=Core.RecordInstallError(outer);
   Check("production_error_file_created",log!=null&&Path.GetDirectoryName(log)==root);string body=File.ReadAllText(log);
   Check("log_environment",body.Contains("Pack: "+Core.Brand+"; build="+Core.ReleaseBuild)&&body.Contains(".NET CLR:")&&body.Contains("OS 64-bit=")&&body.Contains("process 64-bit=")&&body.Contains("administrator token="));
   Check("log_preserves_original_stack",body.Contains(outer.ToString())&&body.Contains("DiagnosticAudit1902.Thrown"));
   Check("log_captured_evidence",body.Contains("operation=replace")&&body.Contains("operation=create-move")&&body.Contains("Staged metadata: file;")&&body.Contains("ReadOnly"));
   Check("log_all_inner_hresult",body.Contains("0x80070005")&&body.Contains("Win32=5")&&body.Contains("0x800700E1")&&body.Contains("Win32=225")&&body.Contains("0x80131620")&&body.Contains("not a Win32 HRESULT"));
   Check("log_rollback_result",body.Contains("Pack.RollbackStatus=incomplete")&&body.Contains("Pack.RollbackPath=directory_target.dll"));
   var uiType=typeof(Core).Assembly.GetType("UiLanguage");var ui=Activator.CreateInstance(uiType,true);var change=uiType.GetMethod("Change");var format=uiType.GetMethod("Error");
   change.Invoke(ui,new object[]{"en",false});string en=Convert.ToString(format.Invoke(ui,new object[]{readOnly}));
   Check("english_access_guidance",en.Contains(target)&&en.Contains("protection history")&&en.Contains("administrator does not resolve every file restriction"));
   Check("english_prepare_guidance",Convert.ToString(format.Invoke(ui,new object[]{prepare})).Contains("Preparing the folder"));
   change.Invoke(ui,new object[]{"ko",false});string ko=Convert.ToString(format.Invoke(ui,new object[]{readOnly}));
   Check("korean_access_guidance",ko.Contains(target)&&ko.Contains("보호 기록")&&ko.Contains("관리자 실행으로도 해결되지 않는"));
   Check("korean_prepare_guidance",Convert.ToString(format.Invoke(ui,new object[]{prepare})).Contains("폴더 준비"));
   var preflight=typeof(Core).GetMethod("PreflightWrites",BindingFlags.NonPublic|BindingFlags.Static);
   preflight.Invoke(null,new object[]{root,new Dictionary<string,byte[]>{{"new/folders/target.dll",next},{"other/new/target.dll",next}}});
   Check("preflight_creates_no_package_directories",!Directory.Exists(Path.Combine(root,"new"))&&!Directory.Exists(Path.Combine(root,"other")));
   File.SetAttributes(target,FileAttributes.ReadOnly);PackWriteException beforeChanges=null;
   try{preflight.Invoke(null,new object[]{root,new Dictionary<string,byte[]>{{"owned.ini",next}}});}catch(TargetInvocationException ex){beforeChanges=ex.InnerException as PackWriteException;}
   finally{File.SetAttributes(target,FileAttributes.Normal);}
   Check("preflight_readonly_exact_and_preserved",beforeChanges!=null&&beforeChanges.Stage=="prepare"&&Text(beforeChanges,"Operation")=="preflight-inspect"&&File.ReadAllBytes(target).SequenceEqual(old));
   Check("preflight_scope_not_global_claim",beforeChanges.Data.Contains("Pack.PreflightPackageChangesStarted")&&!(bool)beforeChanges.Data["Pack.PreflightPackageChangesStarted"]&&Convert.ToString(beforeChanges.Data["Pack.PreflightScope"]).Contains("Earlier update preparation or resume is outside this check"));
   string preflightLog=Core.RecordInstallError(beforeChanges);string preflightText=File.ReadAllText(preflightLog);
   Check("preflight_metadata_in_error_log",preflightText.Contains("Stage=prepare; operation=preflight-inspect")&&preflightText.Contains("Pack.PreflightPackageChangesStarted=False"));
   // Atomic's 37-character stage fits below MAX_PATH here, whereas the old
   // verbose preflight filename exceeded it and rejected a valid game folder.
   int parentLength=220;Check("deep_fixture_has_room",root.Length+2<parentLength);
   string deepName=new string('d',parentLength-root.Length-1),deepParent=Path.Combine(root,deepName);Directory.CreateDirectory(deepParent);
   string deepTarget=Path.Combine(deepParent,"owned.ini"),id=new string('a',32);
   Check("deep_boundary_distinguishes_old_probe",Path.Combine(deepParent,"."+id+".tmp").Length<260&&Path.Combine(deepParent,"_"+id+".tmp").Length<260&&Path.Combine(deepParent,".kair-preflight-"+id+"-source.tmp").Length>=260);
   Core.Atomic(deepTarget,old);Core.Atomic(deepTarget,next);Check("deep_atomic_create_replace_works",File.ReadAllBytes(deepTarget).SequenceEqual(next));
   preflight.Invoke(null,new object[]{root,new Dictionary<string,byte[]>{{deepName+"/owned.ini",old}}});
   Check("deep_preflight_accepts_atomic_compatible_path",File.ReadAllBytes(deepTarget).SequenceEqual(next)&&Directory.GetFiles(deepParent,"*.tmp").Length==0);
   Check("acl_summary_is_bounded_non_effective",evidence.Contains("matching current user/group rules; NOT effective access determination")&&evidence.Contains("; rights=")&&evidence.Contains("; inherited="));
   Check("acl_does_not_expose_account_identifiers",!evidence.Contains("S-1-5-")&&!evidence.Contains(Environment.UserName)&&!evidence.Contains(Environment.MachineName));
   Check("no_staged_files_remain",Directory.GetFiles(root,"*.tmp").Length==0);passed=true;
  }catch(Exception ex){error=ex.ToString();}
  finally{Core.AtomicBeforeCommit=null;Environment.SetEnvironmentVariable("TEMP",priorTemp);Environment.SetEnvironmentVariable("TMP",priorTmp);}
  File.WriteAllText(reportPath,new JavaScriptSerializer().Serialize(new{passed=passed,checks=Checks,error=error,fixture=root,coreSha256=Core.HashFile(Path.Combine(directory,"../../src/PackCore.cs"))}));
  Console.WriteLine("Install diagnostic checks: "+Checks.Count+"; passed: "+passed+(error==null?"":"; "+error));return passed?0:1;
 }
}
