using System;
using System.IO;
using System.Collections.Generic;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Security.Cryptography;
using System.Web.Script.Serialization;

public static class AccessAudit1902 {
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr LoadLibraryEx(string path, IntPtr file, uint flags);
 [DllImport("kernel32.dll", SetLastError=true)] static extern bool FreeLibrary(IntPtr value);
 static List<object> cases=new List<object>();
 static MethodInfo atomic;
 static byte[] next={7,8,9};
 static string CasePath(string root,string name) { string directory=Path.Combine(root,name); Directory.CreateDirectory(directory); return Path.Combine(directory,"ac8_mouse_aim_010.dll"); }
 static void Run(string name,string path) {
  bool existed=File.Exists(path),wasDirectory=Directory.Exists(path); byte[] before=existed?File.ReadAllBytes(path):null;
  try { atomic.Invoke(null,new object[]{path,next}); cases.Add(new{name=name,success=true,targetExisted=existed,targetWasDirectory=wasDirectory,exception=(object)null}); }
  catch(TargetInvocationException wrap) {
   Exception failure=wrap.InnerException, inner=failure.InnerException??failure;
   bool? unchanged=before==null?(bool?)null:Convert.ToBase64String(before)==Convert.ToBase64String(File.ReadAllBytes(path));
   string stage=null; var field=failure.GetType().GetField("Stage");if(field!=null)stage=(string)field.GetValue(failure);
   cases.Add(new{name=name,success=false,targetExisted=existed,targetWasDirectory=wasDirectory,targetPreserved=unchanged,stage=stage,
    operation=failure.GetType().GetField("Operation")==null?null:Convert.ToString(failure.GetType().GetField("Operation").GetValue(failure)),
    evidence=failure.GetType().GetField("FailureEvidence")==null?null:Convert.ToString(failure.GetType().GetField("FailureEvidence").GetValue(failure)),
    exception=new{wrapper=failure.GetType().FullName,type=inner.GetType().FullName,hresult="0x"+inner.HResult.ToString("X8"),message=inner.Message,stack=inner.StackTrace}});
  }
 }
 public static void Execute(string setup,string root,string result) {
  Directory.CreateDirectory(root);
  atomic=Assembly.LoadFile(Path.GetFullPath(setup)).GetType("KoreanAIR.Core").GetMethod("Atomic",BindingFlags.Public|BindingFlags.Static);
  string p=CasePath(root,"new_target");Run("new_target",p);
  p=CasePath(root,"ordinary_existing");File.WriteAllBytes(p,new byte[]{1,2});Run("ordinary_existing",p);
  p=CasePath(root,"existing_readonly");File.WriteAllBytes(p,new byte[]{1,2});File.SetAttributes(p,FileAttributes.ReadOnly);try{Run("existing_readonly",p);}finally{File.SetAttributes(p,FileAttributes.Normal);}
  p=CasePath(root,"existing_hidden");File.WriteAllBytes(p,new byte[]{1,2});File.SetAttributes(p,FileAttributes.Hidden);try{Run("existing_hidden",p);}finally{File.SetAttributes(p,FileAttributes.Normal);}
  p=CasePath(root,"target_is_directory");Directory.CreateDirectory(p);Run("target_is_directory",p);
  p=CasePath(root,"existing_share_none");File.WriteAllBytes(p,new byte[]{1,2});using(var handle=File.Open(p,FileMode.Open,FileAccess.Read,FileShare.None)) {
   try{atomic.Invoke(null,new object[]{p,next});cases.Add(new{name="existing_share_none",success=true});}
   catch(TargetInvocationException wrap){Exception failure=wrap.InnerException,inner=failure.InnerException??failure;cases.Add(new{name="existing_share_none",success=false,stage=(string)failure.GetType().GetField("Stage").GetValue(failure),exception=new{type=inner.GetType().FullName,hresult="0x"+inner.HResult.ToString("X8"),message=inner.Message,stack=inner.StackTrace}});}
  }
  p=CasePath(root,"existing_mapped_pe");File.Copy(setup,p,true);IntPtr image=LoadLibraryEx(p,IntPtr.Zero,1);
  if(image==IntPtr.Zero)throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error(),"Fixture PE image mapping failed");
  try {Run("existing_mapped_pe",p);}finally{FreeLibrary(image);}
  p=CasePath(root,"parent_directory_readonly");string dir=Path.GetDirectoryName(p);File.SetAttributes(dir,FileAttributes.ReadOnly);try{Run("parent_directory_readonly",p);}finally{File.SetAttributes(dir,FileAttributes.Directory);}
  var sid=WindowsIdentity.GetCurrent().User;
  p=CasePath(root,"parent_deny_create");dir=Path.GetDirectoryName(p);var original=Directory.GetAccessControl(dir);var changed=Directory.GetAccessControl(dir);
  changed.AddAccessRule(new FileSystemAccessRule(sid,FileSystemRights.CreateFiles,InheritanceFlags.None,PropagationFlags.None,AccessControlType.Deny));Directory.SetAccessControl(dir,changed);
  try{Run("parent_deny_create",p);}finally{Directory.SetAccessControl(dir,original);}
  p=CasePath(root,"new_target_inherited_deny_delete");dir=Path.GetDirectoryName(p);original=Directory.GetAccessControl(dir);changed=Directory.GetAccessControl(dir);
  changed.AddAccessRule(new FileSystemAccessRule(sid,FileSystemRights.Delete,InheritanceFlags.ObjectInherit,PropagationFlags.InheritOnly,AccessControlType.Deny));Directory.SetAccessControl(dir,changed);
  try{Run("new_target_inherited_deny_delete",p);}finally{Directory.SetAccessControl(dir,original);foreach(var f in Directory.GetFiles(dir)){var fs=File.GetAccessControl(f);fs.SetAccessRuleProtection(false,false);File.SetAccessControl(f,fs);}}
  p=CasePath(root,"existing_deny_delete");File.WriteAllBytes(p,new byte[]{1,2});var fileOriginal=File.GetAccessControl(p);var fileChanged=File.GetAccessControl(p);fileChanged.AddAccessRule(new FileSystemAccessRule(sid,FileSystemRights.Delete,AccessControlType.Deny));File.SetAccessControl(p,fileChanged);
  try{Run("existing_deny_delete",p);}finally{if(File.Exists(p))File.SetAccessControl(p,fileOriginal);}
  p=CasePath(root,"new_target_no_delete_rights");dir=Path.GetDirectoryName(p);original=Directory.GetAccessControl(dir);changed=Directory.GetAccessControl(dir);
  changed.AddAccessRule(new FileSystemAccessRule(sid,FileSystemRights.DeleteSubdirectoriesAndFiles,InheritanceFlags.None,PropagationFlags.None,AccessControlType.Deny));
  changed.AddAccessRule(new FileSystemAccessRule(sid,FileSystemRights.Delete,InheritanceFlags.ObjectInherit,PropagationFlags.InheritOnly,AccessControlType.Deny));Directory.SetAccessControl(dir,changed);
  try{Run("new_target_no_delete_rights",p);}finally{Directory.SetAccessControl(dir,original);foreach(var f in Directory.GetFiles(dir)){var fs=File.GetAccessControl(f);fs.SetAccessRuleProtection(false,false);File.SetAccessControl(f,fs);}}
  p=CasePath(root,"existing_no_delete_rights");File.WriteAllBytes(p,new byte[]{1,2});dir=Path.GetDirectoryName(p);original=Directory.GetAccessControl(dir);changed=Directory.GetAccessControl(dir);
  changed.AddAccessRule(new FileSystemAccessRule(sid,FileSystemRights.DeleteSubdirectoriesAndFiles,InheritanceFlags.None,PropagationFlags.None,AccessControlType.Deny));
  changed.AddAccessRule(new FileSystemAccessRule(sid,FileSystemRights.Delete,InheritanceFlags.ObjectInherit,PropagationFlags.InheritOnly,AccessControlType.Deny));Directory.SetAccessControl(dir,changed);
  try{Run("existing_no_delete_rights",p);}finally{Directory.SetAccessControl(dir,original);foreach(var f in Directory.GetFiles(dir)){var fs=File.GetAccessControl(f);fs.SetAccessRuleProtection(false,false);File.SetAccessControl(f,fs);}}
  string assemblySha;using(var algorithm=SHA256.Create())using(var input=File.OpenRead(setup))assemblySha=BitConverter.ToString(algorithm.ComputeHash(input)).Replace("-","").ToLowerInvariant();
  File.WriteAllText(result,new JavaScriptSerializer().Serialize(new{productionAssembly=setup,productionAssemblySha256=assemblySha,fixtureRoot=root,caseCount=cases.Count,elevated=new WindowsPrincipal(WindowsIdentity.GetCurrent()).IsInRole(WindowsBuiltInRole.Administrator),cases=cases}));
 }
}
