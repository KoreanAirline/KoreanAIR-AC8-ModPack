using System;
using System.IO;
using System.Collections.Generic;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Web.Script.Serialization;

public static class PreflightAudit1902 {
 static List<object> cases=new List<object>();
 static string root;
 static SecurityIdentifier sid=WindowsIdentity.GetCurrent().User;
 static string DirectoryFor(string name){string dir=Path.Combine(root,name);Directory.CreateDirectory(dir);return dir;}
 static object Error(Exception ex){return new{type=ex.GetType().FullName,hresult="0x"+ex.HResult.ToString("X8"),message=ex.Message,stack=ex.StackTrace};}
 // Test-only proposal. Never creates/opens an installed package target.
 static void Probe(string dir,bool replace){
  string token=".kair-preflight-"+Guid.NewGuid().ToString("N");
  string source=Path.Combine(dir,token+"-source.tmp"),moved=Path.Combine(dir,token+"-moved.tmp"),destination=Path.Combine(dir,token+"-destination.tmp");
  using(var first=new FileStream(source,FileMode.CreateNew,FileAccess.Write,FileShare.ReadWrite|FileShare.Delete,4096,FileOptions.DeleteOnClose)){
   first.WriteByte(1);first.Flush();File.Move(source,moved);
   if(replace)using(var second=new FileStream(destination,FileMode.CreateNew,FileAccess.Write,FileShare.ReadWrite|FileShare.Delete,4096,FileOptions.DeleteOnClose)){
    second.WriteByte(2);second.Flush();File.Replace(moved,destination,null);
   }
  }
 }
 static void Run(string name,string dir,bool replace){string[] before=Directory.GetFileSystemEntries(dir);object error=null;try{Probe(dir,replace);}catch(Exception ex){error=Error(ex);}string[] after=Directory.GetFileSystemEntries(dir);cases.Add(new{name=name,probeIncludesReplace=replace,passed=error==null,entriesBefore=before.Length,entriesAfter=after.Length,error=error});}
 static void WithAcl(string name,FileSystemAccessRule[] rules,bool replace){string dir=DirectoryFor(name);DirectorySecurity original=Directory.GetAccessControl(dir),changed=Directory.GetAccessControl(dir);foreach(var rule in rules)changed.AddAccessRule(rule);Directory.SetAccessControl(dir,changed);try{Run(name,dir,replace);}finally{Directory.SetAccessControl(dir,original);foreach(var f in Directory.GetFiles(dir)){var fs=File.GetAccessControl(f);fs.SetAccessRuleProtection(false,false);File.SetAccessControl(f,fs);}}}
 public static void Execute(string fixtureRoot,string result){
  root=fixtureRoot;Directory.CreateDirectory(root);
  Run("ordinary_rename_only",DirectoryFor("ordinary_rename_only"),false);
  Run("ordinary_rename_replace",DirectoryFor("ordinary_rename_replace"),true);
  string plainReadonly=DirectoryFor("directory_readonly_rename_only");File.SetAttributes(plainReadonly,FileAttributes.ReadOnly);try{Run("directory_readonly_rename_only",plainReadonly,false);}finally{File.SetAttributes(plainReadonly,FileAttributes.Directory);}
  string dir=DirectoryFor("directory_readonly");File.SetAttributes(dir,FileAttributes.ReadOnly);try{Run("directory_readonly",dir,true);}finally{File.SetAttributes(dir,FileAttributes.Directory);}
  WithAcl("deny_create",new[]{new FileSystemAccessRule(sid,FileSystemRights.CreateFiles,AccessControlType.Deny)},true);
  WithAcl("deny_create_rename_only",new[]{new FileSystemAccessRule(sid,FileSystemRights.CreateFiles,AccessControlType.Deny)},false);
  WithAcl("deny_delete_both_rename_only",new[]{new FileSystemAccessRule(sid,FileSystemRights.DeleteSubdirectoriesAndFiles,AccessControlType.Deny),new FileSystemAccessRule(sid,FileSystemRights.Delete,InheritanceFlags.ObjectInherit,PropagationFlags.InheritOnly,AccessControlType.Deny)},false);
  WithAcl("deny_delete_both_rename_replace",new[]{new FileSystemAccessRule(sid,FileSystemRights.DeleteSubdirectoriesAndFiles,AccessControlType.Deny),new FileSystemAccessRule(sid,FileSystemRights.Delete,InheritanceFlags.ObjectInherit,PropagationFlags.InheritOnly,AccessControlType.Deny)},true);
  WithAcl("deny_file_delete_only",new[]{new FileSystemAccessRule(sid,FileSystemRights.Delete,InheritanceFlags.ObjectInherit,PropagationFlags.InheritOnly,AccessControlType.Deny)},true);
  WithAcl("deny_parent_delete_child_only",new[]{new FileSystemAccessRule(sid,FileSystemRights.DeleteSubdirectoriesAndFiles,AccessControlType.Deny)},true);
  WithAcl("deny_file_read_rename_only",new[]{new FileSystemAccessRule(sid,FileSystemRights.ReadData,InheritanceFlags.ObjectInherit,PropagationFlags.InheritOnly,AccessControlType.Deny)},false);
  WithAcl("deny_file_read_rename_replace",new[]{new FileSystemAccessRule(sid,FileSystemRights.ReadData,InheritanceFlags.ObjectInherit,PropagationFlags.InheritOnly,AccessControlType.Deny)},true);
  dir=DirectoryFor("readonly_package_target_blind_spot");string target=Path.Combine(dir,"ac8_mouse_aim_010.dll");File.WriteAllBytes(target,new byte[]{1,2});File.SetAttributes(target,FileAttributes.ReadOnly);try{Run("readonly_package_target_blind_spot",dir,false);}finally{File.SetAttributes(target,FileAttributes.Normal);}
  dir=DirectoryFor("locked_package_target_blind_spot");target=Path.Combine(dir,"ac8_mouse_aim_010.dll");File.WriteAllBytes(target,new byte[]{1,2});using(var handle=File.Open(target,FileMode.Open,FileAccess.Read,FileShare.None))Run("locked_package_target_blind_spot",dir,false);
  WithAcl("deny_file_delete_only_rename",new[]{new FileSystemAccessRule(sid,FileSystemRights.Delete,InheritanceFlags.ObjectInherit,PropagationFlags.InheritOnly,AccessControlType.Deny)},false);
  WithAcl("deny_parent_delete_child_only_rename",new[]{new FileSystemAccessRule(sid,FileSystemRights.DeleteSubdirectoriesAndFiles,AccessControlType.Deny)},false);
  File.WriteAllText(result,new JavaScriptSerializer().Serialize(new{caseCount=cases.Count,cases=cases}));
 }
}
