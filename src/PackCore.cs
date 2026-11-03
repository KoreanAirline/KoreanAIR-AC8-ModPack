using System;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Collections.Generic;
using System.Diagnostics;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;

[assembly:System.Reflection.AssemblyVersion("2.4.0.0")]
[assembly:System.Reflection.AssemblyFileVersion("2.4.0.0")]
[assembly:System.Reflection.AssemblyInformationalVersion("2.4+b2026110401")]
[assembly:System.Reflection.AssemblyProduct("KoreanAIR AC8 Mod Pack")]

namespace KoreanAIR {
public sealed class Item { public string path; public string source; public string hash; public string group; public bool mutable; }
public sealed class FileState { public string path; public string hash; public string original; public bool mutable; }
public sealed class FrameGenerationLease { public bool enabled,live,originalExists,originalReadOnly; public string encoding,newline,prefix,previousSection; }
public sealed class State { public string version="2.4"; public long build; public string previousVersion; public long previousBuild; public string root; public bool campaign; public bool mouse; public bool display; public bool suspended; public bool sharedRuntime; public string campaignProvider; public string campaignFingerprint; public string campaignStatus; public string backup; public string campaignLoaderHash; public string legacyCampaignLoaderHash; public FrameGenerationLease frameGeneration; public List<FileState> files=new List<FileState>(); }
public sealed class Manifest { public List<Item> files; public Dictionary<string,string> legacy; }
public sealed class LoaderCompatibility { public bool ForeignLoader; public string Path; public string Hash; public string Kind; }
public sealed class HotasCompatibility { public bool Present,InputEnabled,KnownSharedRuntime,HotasEnabled,AnalogYawEnabled; }
public sealed class PackWriteException : IOException {
 public readonly string Target,Stage,Operation,Temporary,FailureEvidence;
 public readonly int CauseHResult;
 public readonly int? Win32Error;
 public PackWriteException(string target,string stage,Exception cause):this(target,stage,stage,null,cause){}
 public PackWriteException(string target,string stage,string operation,string temporary,Exception cause):base("Unable to write installed file: "+target+"\n"+cause.Message,cause){
  Target=target;Stage=stage;Operation=operation;Temporary=temporary;CauseHResult=cause.HResult;
  if(((uint)CauseHResult>>16&0x1fff)==7)Win32Error=CauseHResult&0xffff;
  // Capture before Atomic's cleanup and the install transaction's rollback.
  // In particular, File.Exists(false) must not be treated as proof of absence.
  var evidence=new StringBuilder();evidence.AppendLine("Captured UTC: "+DateTime.UtcNow.ToString("o"));
  evidence.AppendLine("Target metadata: "+Describe(target));evidence.AppendLine("Staged metadata: "+Describe(temporary));
  try{evidence.AppendLine("Parent metadata: "+Describe(Path.GetDirectoryName(target)));}catch(Exception ex){evidence.AppendLine("Parent metadata: unavailable; "+ex.GetType().Name+" HRESULT=0x"+ex.HResult.ToString("X8"));}
  evidence.AppendLine("ACL summaries: matching current user/group rules; NOT effective access determination.");
  evidence.AppendLine("Target ACL: "+DescribeAccess(target));evidence.AppendLine("Staged ACL: "+DescribeAccess(temporary));
  try{evidence.AppendLine("Parent ACL: "+DescribeAccess(Path.GetDirectoryName(target)));}catch(Exception ex){evidence.AppendLine("Parent ACL: unavailable; "+ex.GetType().Name+" HRESULT=0x"+ex.HResult.ToString("X8"));}
  FailureEvidence=evidence.ToString();
 }
 static string Describe(string path){
  if(String.IsNullOrEmpty(path))return "not assigned";
  try{var attributes=File.GetAttributes(path);return ((attributes&FileAttributes.Directory)!=0?"directory":"file")+"; attributes="+attributes+" (0x"+((int)attributes).ToString("X8")+")";}
  catch(FileNotFoundException ex){return "missing file; HRESULT=0x"+ex.HResult.ToString("X8");}
  catch(DirectoryNotFoundException ex){return "missing parent/path; HRESULT=0x"+ex.HResult.ToString("X8");}
  catch(Exception ex){return "unavailable; "+ex.GetType().Name+" HRESULT=0x"+ex.HResult.ToString("X8");}
 }
 static string DescribeAccess(string path){
  if(String.IsNullOrEmpty(path))return "not assigned";
  try{
   using(var identity=System.Security.Principal.WindowsIdentity.GetCurrent()){
    var current=identity.User;var ids=new HashSet<string>(StringComparer.OrdinalIgnoreCase);if(current!=null)ids.Add(current.Value);
    bool groupsLimited=false;if(identity.Groups!=null)foreach(System.Security.Principal.IdentityReference group in identity.Groups){if(ids.Count>=64){groupsLimited=true;break;}ids.Add(group.Value);}
    var attributes=File.GetAttributes(path);
    System.Security.AccessControl.FileSystemSecurity security=(attributes&FileAttributes.Directory)!=0?(System.Security.AccessControl.FileSystemSecurity)Directory.GetAccessControl(path,System.Security.AccessControl.AccessControlSections.Access):File.GetAccessControl(path,System.Security.AccessControl.AccessControlSections.Access);
    var rules=security.GetAccessRules(true,true,typeof(System.Security.Principal.SecurityIdentifier));var text=new StringBuilder();int inspected=0,matched=0;
    foreach(System.Security.AccessControl.FileSystemAccessRule rule in rules){
     if(++inspected>256){text.Append(" [Rule inspection limited to 256.]");break;}
     if(!ids.Contains(rule.IdentityReference.Value))continue;
     if(matched>=64){text.Append(" [Matching rule output limited to 64.]");break;}
     text.Append("\n  principal=").Append(current!=null&&rule.IdentityReference.Value==current.Value?"current user":"current token group").Append("; type=").Append(rule.AccessControlType).Append("; rights=").Append(rule.FileSystemRights).Append("; inherited=").Append(rule.IsInherited).Append("; inheritance=").Append(rule.InheritanceFlags).Append("; propagation=").Append(rule.PropagationFlags);matched++;
    }
    if(matched==0)text.Append("No matching rules among those inspected.");if(groupsLimited)text.Append(" [Token identity matching limited to 64.]");return text.ToString();
   }
  }catch(Exception ex){return "unavailable; "+ex.GetType().Name+" HRESULT=0x"+ex.HResult.ToString("X8");}
 }
}
public static class Core {
 public const string Brand="KoreanAIR_AC8_ModPack_2.4";
 public const long ReleaseBuild=2026110401;
 public const string Folder="KoreanAIR_AC8_ModPack";
 public const string Mod="Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/";
 public const string CampaignLoader="Game/Binaries/Win64/dinput8.dll";
 public const string CampaignPatch=Folder+"/Translation/campaign-dialogue.json.gz";
 public const string CampaignPak="Game/Content/Paks/pakchunk0-Windows_999_P.pak";
 public static Action<string> SubtitleFallbackNotice;
 public static JavaScriptSerializer Json=new JavaScriptSerializer{MaxJsonLength=32*1024*1024};
 public static string Hash(byte[] b) { using(var s=SHA256.Create()) return BitConverter.ToString(s.ComputeHash(b)).Replace("-","").ToLowerInvariant(); }
 public static string HashFile(string p) { using(var s=SHA256.Create()) using(var f=File.OpenRead(p)) return BitConverter.ToString(s.ComputeHash(f)).Replace("-","").ToLowerInvariant(); }
 public static string Safe(string root,string relative) {
  root=Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar;
  string rootDirectory=root.TrimEnd(Path.DirectorySeparatorChar); if(Directory.Exists(rootDirectory)&&(File.GetAttributes(rootDirectory)&FileAttributes.ReparsePoint)!=0) throw new Exception("The selected folder is a redirected link.");
  if(String.IsNullOrEmpty(relative)||Path.IsPathRooted(relative)||relative.IndexOf(':')>=0) throw new Exception("Invalid package path.");
  string full=Path.GetFullPath(Path.Combine(root,relative.Replace('/',Path.DirectorySeparatorChar)));
  if(!full.StartsWith(root,StringComparison.OrdinalIgnoreCase)) throw new Exception("Package path leaves the selected folder.");
  for(string p=Path.GetDirectoryName(full);p!=null&&p.StartsWith(root,StringComparison.OrdinalIgnoreCase);p=Path.GetDirectoryName(p)) if(Directory.Exists(p)&&(File.GetAttributes(p)&FileAttributes.ReparsePoint)!=0) throw new Exception("A package folder is a redirected link: "+p);
  if(File.Exists(full)&&(File.GetAttributes(full)&FileAttributes.ReparsePoint)!=0) throw new Exception("A package file is a redirected link.");
  return full;
 }
 public static void Atomic(string path,byte[] bytes) {
  string tmp=null,stage="prepare",operation="prepare";
  try {
   string parent=Path.GetDirectoryName(path);Directory.CreateDirectory(parent);tmp=Path.Combine(parent,"."+Guid.NewGuid().ToString("N")+".tmp");
   stage="write";operation="write";File.WriteAllBytes(tmp,bytes);stage="commit";
   if(File.Exists(path)) {
#if ATOMIC_TEST
    if(AtomicBeforeCommit!=null)AtomicBeforeCommit(path,tmp);
#endif
    operation="replace";try {File.Replace(tmp,path,null);}
    catch(FileNotFoundException){
     // Recover only a destination-removal race. Never recreate a missing staged file.
     if(File.Exists(tmp)&&!File.Exists(path)){operation="recovery-move";File.Move(tmp,path);}else throw;
    }
   } else {operation="create-move";File.Move(tmp,path);}
  } catch(IOException ex){throw new PackWriteException(path,stage,operation,tmp,ex);}
    catch(UnauthorizedAccessException ex){throw new PackWriteException(path,stage,operation,tmp,ex);}
  finally {try{if(File.Exists(tmp))File.Delete(tmp);}catch{}}
 }
#if ATOMIC_TEST
 public static Action<string,string> AtomicBeforeCommit;
#endif
 public static string RecordInstallError(Exception ex) {
  string log=Path.Combine(Path.GetTempPath(),"KoreanAIR_AC8_Setup_error.txt");
  try{
   var text=new StringBuilder();text.AppendLine(DateTime.UtcNow.ToString("o"));text.AppendLine("Pack: "+Brand+"; build="+ReleaseBuild);
   text.AppendLine("OS: "+Environment.OSVersion.VersionString+"; OS 64-bit="+Environment.Is64BitOperatingSystem+"; process 64-bit="+Environment.Is64BitProcess);
   text.AppendLine(".NET CLR: "+Environment.Version+"; framework release="+FrameworkRelease()+"; administrator token="+AdministratorToken());
   text.AppendLine("\nException and original stack:");text.AppendLine(ex.ToString());text.AppendLine("\nFailure diagnostics (captured before temporary cleanup/rollback where available):");
   AppendFailure(text,ex,"0",new HashSet<Exception>(),0);File.WriteAllText(log,text.ToString(),new UTF8Encoding(false));return log;
  }catch{return null;}
 }
 static string FrameworkRelease(){try{using(var key=Microsoft.Win32.Registry.LocalMachine.OpenSubKey(@"SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full")){return key==null?"unavailable":Convert.ToString(key.GetValue("Release","unavailable"));}}catch{return "unavailable";}}
 static string AdministratorToken(){try{using(var identity=System.Security.Principal.WindowsIdentity.GetCurrent()){return new System.Security.Principal.WindowsPrincipal(identity).IsInRole(System.Security.Principal.WindowsBuiltInRole.Administrator).ToString();}}catch{return "unavailable";}}
 static void AppendFailure(StringBuilder text,Exception ex,string index,HashSet<Exception> seen,int depth){
  if(ex==null||depth>16||seen.Count>=64||!seen.Add(ex))return;
  int hr=ex.HResult;text.AppendLine("Exception "+index+": "+ex.GetType().FullName+"; HRESULT=0x"+hr.ToString("X8")+"; Win32="+((((uint)hr>>16&0x1fff)==7)?(hr&0xffff).ToString():"not a Win32 HRESULT"));
  var write=ex as PackWriteException;if(write!=null){text.AppendLine("Stage="+write.Stage+"; operation="+write.Operation+"; cause HRESULT=0x"+write.CauseHResult.ToString("X8")+"; cause Win32="+(write.Win32Error.HasValue?write.Win32Error.Value.ToString():"not a Win32 HRESULT"));text.AppendLine("Target="+write.Target);text.AppendLine("Staged="+(write.Temporary??"not assigned"));text.Append(write.FailureEvidence);}
  foreach(string key in new[]{"Pack.RollbackStatus","Pack.RollbackChecked","Pack.RollbackCompleted","Pack.RollbackFailures","Pack.RollbackPath","Pack.PreflightScope","Pack.PreflightPackageChangesStarted"})try{if(ex.Data.Contains(key))text.AppendLine(key+"="+Convert.ToString(ex.Data[key]));}catch{}
  var aggregate=ex as AggregateException;
  if(aggregate!=null){for(int i=0;i<aggregate.InnerExceptions.Count&&i<64;i++)AppendFailure(text,aggregate.InnerExceptions[i],index+"."+i,seen,depth+1);}
  else AppendFailure(text,ex.InnerException,index+".0",seen,depth+1);
 }
 static void MarkRollback(Exception ex,int checkedCount,int completed,List<string> failures){try{ex.Data["Pack.RollbackStatus"]=failures.Count==0?"completed":"incomplete";ex.Data["Pack.RollbackChecked"]=checkedCount;ex.Data["Pack.RollbackCompleted"]=completed;ex.Data["Pack.RollbackFailures"]=String.Join("\n",failures);}catch{}}
 static void Rollback(string root,IEnumerable<KeyValuePair<string,byte[]>> journal,Exception initiating) {
  var errors=new List<Exception>{initiating};var failures=new List<string>();int checkedCount=0,completed=0;
  foreach(var entry in journal) {
   checkedCount++;
   try {
    string path=Safe(root,entry.Key);
    if(entry.Value==null){if(File.Exists(path))File.Delete(path);}
    else if(!File.Exists(path)||!File.ReadAllBytes(path).SequenceEqual(entry.Value))Atomic(path,entry.Value);
    completed++;
   }catch(Exception ex){errors.Add(ex);failures.Add(entry.Key);try{ex.Data["Pack.RollbackPath"]=entry.Key;}catch{}}
  }
  MarkRollback(initiating,checkedCount,completed,failures);
  if(errors.Count>1){var error=new AggregateException("Rollback could not restore every file.",errors);MarkRollback(error,checkedCount,completed,failures);throw error;}
 }
 static PackWriteException PreflightFailure(string target,string operation,string temporary,Exception cause){
  var error=new PackWriteException(target,"prepare",operation,temporary,cause);
  error.Data["Pack.PreflightPackageChangesStarted"]=false;
  error.Data["Pack.PreflightScope"]="InstallCore package replacements/removals have not started. Earlier update preparation or resume is outside this check.";return error;
 }
 static void PreflightWrites(string root,Dictionary<string,byte[]> wanted){
  var checkedParents=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
  foreach(var pair in wanted){
   string target=Safe(root,pair.Key);if(File.Exists(target)&&HashFile(target)==Hash(pair.Value))continue;
   string parent=Path.GetDirectoryName(target),operation="preflight-inspect",temporary=null;FileStream probe=null;
   try{
    // This is an early check, not a promise that a later file replacement or
    // a security product will permit the payload. Never alter ACLs/attributes.
    try{var attributes=File.GetAttributes(target);
     if((attributes&FileAttributes.Directory)!=0)throw new IOException("A directory occupies the required installed-file path.");
     if((attributes&FileAttributes.ReadOnly)!=0)throw new UnauthorizedAccessException("The installed file has the read-only attribute.");
    }catch(FileNotFoundException){}catch(DirectoryNotFoundException){}
    // New package folders need no speculative creation: test their nearest
    // existing parent and let the ordinary transaction create them later.
    for(;;){
     try{var attributes=File.GetAttributes(parent);if((attributes&FileAttributes.Directory)==0)throw new IOException("A file occupies a required installation folder.");if((attributes&FileAttributes.ReparsePoint)!=0)throw new IOException("A required installation folder is a redirected link.");break;}
     catch(FileNotFoundException){}catch(DirectoryNotFoundException){}
     if(String.Equals(parent,root,StringComparison.OrdinalIgnoreCase))throw new DirectoryNotFoundException("The game folder is unavailable.");
     parent=Path.GetDirectoryName(parent);if(String.IsNullOrEmpty(parent))throw new DirectoryNotFoundException("The installation parent is unavailable.");
    }
    if(!checkedParents.Add(parent))continue;
    // Keep both probe names no longer than Atomic's .{GUID}.tmp staging name.
    // A longer diagnostic name would reject otherwise valid deep game paths.
    string id=Guid.NewGuid().ToString("N");temporary=Path.Combine(parent,"."+id+".tmp");string moved=Path.Combine(parent,"_"+id+".tmp");
    operation="preflight-create";probe=new FileStream(temporary,FileMode.CreateNew,FileAccess.Write,FileShare.ReadWrite|FileShare.Delete,4096,FileOptions.DeleteOnClose);
    operation="preflight-write";probe.WriteByte(1);probe.Flush();
    operation="preflight-rename";File.Move(temporary,moved);
   }catch(IOException ex){throw PreflightFailure(target,operation,temporary,ex);}
    catch(UnauthorizedAccessException ex){throw PreflightFailure(target,operation,temporary,ex);}
   finally{if(probe!=null)try{probe.Dispose();}catch{}}
  }
 }
 public static void Text(string path,string text) { Atomic(path,new UTF8Encoding(false).GetBytes(text)); }
 public static State ReadState(string root) { string p=Safe(root,Folder+"/installed.json"); if(!File.Exists(p)) return null; var s=Json.Deserialize<State>(File.ReadAllText(p)); if(s==null||!String.Equals(Path.GetFullPath(s.root).TrimEnd(Path.DirectorySeparatorChar),Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar),StringComparison.OrdinalIgnoreCase)) throw new Exception("Installation record belongs to another game folder."); foreach(var f in s.files) { Safe(root,f.path); if(f.original!=null) Safe(s.backup,f.original); } return s; }
 public static bool Running(string root) { foreach(var p in Process.GetProcessesByName("AceCombat8")) { try { if(String.Equals(p.MainModule.FileName,Safe(root,"Game/Binaries/Win64/AceCombat8.exe"),StringComparison.OrdinalIgnoreCase)) return true; } catch { return true; } } return false; }
 public static void VerifyGame(string root) {
  string exe=Safe(root,"Game/Binaries/Win64/AceCombat8.exe"); if(!File.Exists(exe)||!File.Exists(Safe(root,"start_protected_game.exe"))) throw new Exception("Select the ACE COMBAT 8 game folder containing start_protected_game.exe.");
  using(var b=new BinaryReader(File.OpenRead(exe))) { if(b.ReadUInt16()!=0x5A4D) throw new Exception("Invalid game executable."); b.BaseStream.Position=0x3C; int pe=b.ReadInt32(); if(pe<64||pe>b.BaseStream.Length-120) throw new Exception("Invalid executable header."); b.BaseStream.Position=pe; if(b.ReadUInt32()!=0x4550||b.ReadUInt16()!=0x8664) throw new Exception("The 64-bit game is required."); b.BaseStream.Position=pe+24;if(b.ReadUInt16()!=0x20B)throw new Exception("The 64-bit game is required.");b.BaseStream.Position=pe+24+56;if(b.ReadUInt32()<0x1000)throw new Exception("Invalid executable header."); }
 }
 public static bool IsTestedGame(string root) {
  try{VerifyGame(root);using(var b=new BinaryReader(File.OpenRead(Safe(root,"Game/Binaries/Win64/AceCombat8.exe")))){b.BaseStream.Position=0x3C;int pe=b.ReadInt32();b.BaseStream.Position=pe+8;uint timestamp=b.ReadUInt32();b.BaseStream.Position=pe+24+56;uint size=b.ReadUInt32();return timestamp==0x6AD2D0A7&&size==0x215A2000;}}catch{return false;}
 }
 public static string DetectGame() { string[] roots={@"E:\SteamLibrary\steamapps\common\ACE COMBAT 8",Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),@"Steam\steamapps\common\ACE COMBAT 8")}; foreach(var p in roots) if(File.Exists(Path.Combine(p,"start_protected_game.exe"))) return p; try { var k=Microsoft.Win32.Registry.CurrentUser.OpenSubKey(@"Software\Valve\Steam"); string steam=k==null?null:k.GetValue("SteamPath") as string; if(steam!=null) { string vdf=Path.Combine(steam,"steamapps","libraryfolders.vdf"); if(File.Exists(vdf)) foreach(System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(File.ReadAllText(vdf),"\"path\"\\s+\"([^\"]+)\"")) { string p=Path.Combine(m.Groups[1].Value.Replace("\\\\","\\"),@"steamapps\common\ACE COMBAT 8"); if(File.Exists(Path.Combine(p,"start_protected_game.exe"))) return p; } } } catch {} return ""; }
 static byte[] Entry(ZipArchive z,string name) { var e=z.GetEntry(name); if(e==null) throw new Exception("Missing payload file: "+name); using(var m=new MemoryStream()) { using(var f=e.Open()) f.CopyTo(m); return m.ToArray(); } }
 static bool Selected(string group,bool cp,bool mouse,bool display) { return group=="common" || (group=="campaign"&&cp) || (group=="runtime"&&(cp||mouse||display)); }
 static Manifest ReadManifest(ZipArchive zip) { var manifest=Json.Deserialize<Manifest>(Encoding.UTF8.GetString(Entry(zip,"manifest.json"))); if(manifest==null||manifest.files==null)throw new Exception("Missing payload file: manifest.json");if(manifest.legacy==null)manifest.legacy=new Dictionary<string,string>();return manifest; }
 static string CampaignHash(Manifest manifest) { var item=manifest.files.FirstOrDefault(f=>String.Equals(f.path,CampaignLoader,StringComparison.OrdinalIgnoreCase));return item==null?null:item.hash; }
 static string LegacyCampaignHash(Manifest manifest) { return manifest.legacy.FirstOrDefault(f=>String.Equals(f.Key,CampaignLoader,StringComparison.OrdinalIgnoreCase)).Value; }
 static LoaderCompatibility InspectCampaignLoader(string root,State state,string expected,string legacy) {
  var result=new LoaderCompatibility{Path=CampaignLoader,Kind="absent"};string target=Safe(root,CampaignLoader);if(!File.Exists(target))return result;
  result.Hash=HashFile(target);var owned=state==null?null:state.files.FirstOrDefault(f=>String.Equals(f.path,CampaignLoader,StringComparison.OrdinalIgnoreCase));
  if(owned!=null&&String.Equals(result.Hash,owned.hash,StringComparison.OrdinalIgnoreCase))result.Kind="owned";
  else if(!String.IsNullOrEmpty(expected)&&String.Equals(result.Hash,expected,StringComparison.OrdinalIgnoreCase))result.Kind="current";
  else if(!String.IsNullOrEmpty(legacy)&&String.Equals(result.Hash,legacy,StringComparison.OrdinalIgnoreCase))result.Kind="legacy";
  else { result.Kind="foreign";result.ForeignLoader=true; }return result;
 }
 public static LoaderCompatibility InspectCampaignLoader(string root) { var state=ReadState(root);return InspectCampaignLoader(root,state,state==null?null:state.campaignLoaderHash,state==null?null:state.legacyCampaignLoaderHash); }
 public static LoaderCompatibility InspectCampaignLoader(string root,Stream payload) { using(var zip=new ZipArchive(payload,ZipArchiveMode.Read,true)){var manifest=ReadManifest(zip);return InspectCampaignLoader(root,ReadState(root),CampaignHash(manifest),LegacyCampaignHash(manifest));} }
 public static SharedLoaderCompatibility InspectSharedLoader(string root) { return SharedLoader.Inspect(root,ExternalModEnabled(root,"IoStoreLoaderMod")); }
 // Only this owner-supplied full HOTAS package is eligible for a shared-runtime
 // migration. Its native Lua API is not adopted: Setup installs our tested pair.
 static readonly Dictionary<string,string> HotasRuntimeHashes=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase){
  {"Game/Binaries/Win64/dwmapi.dll","c5d2ab9f9b89bd94460b0a283eefb113085105014011cac961f36787376db744"},
  {"Game/Binaries/Win64/UE4SS/UE4SS.dll","3fc1cd877007499e8c4f2152e12f76098aba8e267b7ee65846edc17cf7a0d1a4"}};
 static readonly Dictionary<string,string> PackRuntimeHashes=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase){
  {"Game/Binaries/Win64/dwmapi.dll","cf440b9eb8643bb7c434acfda696aee57fd981d185dca5e57fb8dbb18f8fc1cd"},
  {"Game/Binaries/Win64/UE4SS/UE4SS.dll","680a026890abb4d0df2211251f8defc1681a584275f1521dcc0fe30af480006f"}};
 static bool ExternalModEnabled(string root,string name) {
  const string prefix="Game/Binaries/Win64/UE4SS/Mods/";bool enabled=File.Exists(Safe(root,prefix+name+"/enabled.txt"));
  string txt=Safe(root,prefix+"mods.txt");
  if(File.Exists(txt)){
   if(new FileInfo(txt).Length>262144)throw new Exception("The UE4SS mod list is too large. Existing files have been preserved.");
   foreach(string line in File.ReadAllLines(txt)){
    var match=System.Text.RegularExpressions.Regex.Match(line,@"^\s*"+System.Text.RegularExpressions.Regex.Escape(name)+@"\s*:\s*([01])\s*(?:[;#].*)?$",System.Text.RegularExpressions.RegexOptions.IgnoreCase);
    if(match.Success)enabled=enabled||match.Groups[1].Value=="1";
    else if(System.Text.RegularExpressions.Regex.IsMatch(line,@"^\s*"+System.Text.RegularExpressions.Regex.Escape(name)+@"\s*:",System.Text.RegularExpressions.RegexOptions.IgnoreCase))throw new Exception("The UE4SS mod list cannot be read safely. Existing files have been preserved.");
   }
  }
  string json=Safe(root,prefix+"mods.json");
  if(File.Exists(json)){
   if(new FileInfo(json).Length>262144)throw new Exception("The UE4SS mod list is too large. Existing files have been preserved.");
   // The two UE4SS lists may both be used by an existing installation. A true
   // entry in either is conservatively active; both must be off to certify off.
   try{var rows=Json.Deserialize<List<Dictionary<string,object>>>(File.ReadAllText(json));if(rows==null)throw new Exception();
    foreach(var row in rows){object mod,on;if(row==null)throw new Exception();if(row.TryGetValue("mod_name",out mod)&&String.Equals(Convert.ToString(mod),name,StringComparison.OrdinalIgnoreCase)){if(!row.TryGetValue("mod_enabled",out on)||!(on is bool))throw new Exception();enabled=enabled||(bool)on;}}
   }catch{throw new Exception("The UE4SS mod list cannot be read safely. Existing files have been preserved.");}
  }
  return enabled;
 }
 public static HotasCompatibility InspectHotas(string root) {
  const string prefix="Game/Binaries/Win64/UE4SS/Mods/";
  bool hotas=File.Exists(Safe(root,prefix+"AC8HOTAS/Scripts/main.lua"));
  bool yaw=File.Exists(Safe(root,prefix+"AC8AnalogYaw/Scripts/main.lua"));
  var result=new HotasCompatibility{Present=hotas||yaw};if(!result.Present)return result;
  result.HotasEnabled=hotas&&ExternalModEnabled(root,"AC8HOTAS");result.AnalogYawEnabled=yaw&&ExternalModEnabled(root,"AC8AnalogYaw");
  result.InputEnabled=result.HotasEnabled||result.AnalogYawEnabled;
  bool known=(hotas&&File.Exists(Safe(root,prefix+"AC8HOTAS/bindings.lua"))&&File.Exists(Safe(root,prefix+"AC8HOTAS/Scripts/ac8_hotas_devices_001.dll")))||(yaw&&File.Exists(Safe(root,prefix+"AC8AnalogYaw/Scripts/ac8_analog_yaw_013.dll"))),foreign=false;
  foreach(var pair in HotasRuntimeHashes){string p=Safe(root,pair.Key);if(!File.Exists(p))continue;string hash=HashFile(p);if(hash==pair.Value)foreign=true;else if(hash!=PackRuntimeHashes[pair.Key])known=false;}
  result.KnownSharedRuntime=known&&foreign;return result;
 }
 static bool HotasReplacement(HotasCompatibility hotas,bool mouse,string path,string hash) { string expected;return !mouse&&hotas.KnownSharedRuntime&&HotasRuntimeHashes.TryGetValue(path,out expected)&&hash==expected; }
 public const string HotasMouseConflict="AC8HOTAS or AC8AnalogYaw is enabled. Keep Mouse flight OFF to use its flight-stick controls. Screen, subtitle layout and Korean translation can stay enabled. Existing HOTAS bindings and mod files have been preserved.";
 public const string HotasRuntimeRepair="Shared UE4SS files were supplied by AC8HOTAS. Close the game and rerun Setup with Mouse flight OFF. Setup keeps HOTAS bindings and mod files and installs the pack's tested shared runtime.";
 public const string HotasInputConflictMessage=HotasMouseConflict;
 public const string HotasRuntimeRepairMessage=HotasRuntimeRepair;
 static string Offline(string root) { var o=Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(Safe(root,"EasyAntiCheat/Settings.json"))); if(!o.ContainsKey("executable")||!String.Equals(Convert.ToString(o["executable"]),"Game/Binaries/Win64/AceCombat8.exe",StringComparison.OrdinalIgnoreCase)) throw new Exception("Unexpected game launch configuration."); o["allow_null_client"]="true"; return Json.Serialize(o); }
 static void Locked(string root,Action action) { using(var gate=new System.Threading.Mutex(false,"Local\\KoreanAIR_AC8_"+Hash(Encoding.UTF8.GetBytes(Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar).ToLowerInvariant())).Substring(0,16))) { bool held=false;try{try{held=gate.WaitOne(0);}catch(System.Threading.AbandonedMutexException){held=true;}if(!held)throw new Exception("Another pack operation is already running for this game folder.");action();}finally{if(held)gate.ReleaseMutex();} } }
 public static void Install(string root,bool cp,bool mouse,bool display,Stream payload,string installer) { Locked(root,()=>FgLocked(()=>InstallCore(root,cp,mouse,display,payload,installer))); }
 public static void UpdatePreservingState(string root,Stream payload,string installer) { Locked(root,()=>FgLocked(()=>{
  if(Running(root))throw new Exception("Close ACE COMBAT 8 before changing installed modules.");
  var before=ReadState(root);if(before==null)throw new Exception("Run the installer first.");
  bool parked=before.suspended;
  try {
   if(parked)SuspendCore(root,false);
   InstallCore(root,before.campaign,before.mouse,before.display,payload,installer);
  } finally {
   if(parked){var current=ReadState(root);if(current!=null&&!current.suspended)SuspendCore(root,true);}
  }
 })); }
 static void InstallCore(string root,bool cp,bool mouse,bool display,Stream payload,string installer) {
  root=Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar); VerifyGame(root); if(Running(root)) throw new Exception("Close ACE COMBAT 8 before changing installed modules."); if(!cp&&!mouse&&!display) { Uninstall(root); return; }
  State old=ReadState(root); if(old!=null&&old.suspended) throw new Exception("Resume the installed modules before updating them.");
  var hotas=InspectHotas(root);if(mouse&&hotas.InputEnabled)throw new Exception(HotasMouseConflict);
  string backup=old==null?Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),Folder,"Backups",Hash(Encoding.UTF8.GetBytes(root.ToLowerInvariant())).Substring(0,16),DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff")):old.backup;
  ValidateFrameGeneration(root,old);
  var next=new State{build=ReleaseBuild,root=root,campaign=cp,mouse=mouse,display=display,backup=backup,frameGeneration=old==null?null:old.frameGeneration,
   previousVersion=old==null?null:(old.build!=ReleaseBuild||old.version!=new State().version?old.version:old.previousVersion),
   previousBuild=old==null?0:(old.build!=ReleaseBuild||old.version!=new State().version?old.build:old.previousBuild)};
  var wanted=new Dictionary<string,byte[]>(StringComparer.OrdinalIgnoreCase); var mutable=new HashSet<string>(StringComparer.OrdinalIgnoreCase); Manifest manifest;
  using(var zip=new ZipArchive(payload,ZipArchiveMode.Read)) {
   manifest=ReadManifest(zip);
   foreach(var f in manifest.files) { Safe(root,f.path); if(!Selected(f.group,cp,mouse,display)) continue; var bytes=Entry(zip,f.source); if(Hash(bytes)!=f.hash) throw new Exception("Payload integrity check failed: "+f.path); wanted.Add(f.path,bytes); if(f.mutable) mutable.Add(f.path); }
  }
  // Never install a historical whole-table payload. Generate only the reviewed
  // dialogue changes on top of verified CURRENT stock strings and indices.
  wanted.Remove(CampaignPak);wanted.Remove(SharedLoader.CampaignPak);
  if(cp) {
   byte[] patch;if(!wanted.TryGetValue(CampaignPatch,out patch))throw new InvalidDataException("Missing campaign dialogue dictionary.");
   try {var translated=CampaignSubtitles.Build(root,patch);wanted[CampaignPak]=translated.Pak;next.campaignFingerprint=translated.Fingerprint;next.campaignStatus=translated.Status;}
   catch(InvalidDataException ex) {next.campaignStatus="Original subtitles retained: "+ex.Message;}
   catch(IOException ex) {next.campaignStatus="Original subtitles retained: "+ex.Message;}
  }
  next.campaignLoaderHash=CampaignHash(manifest);next.legacyCampaignLoaderHash=LegacyCampaignHash(manifest);
  var loader=InspectCampaignLoader(root,old,next.campaignLoaderHash,next.legacyCampaignLoaderHash);
  var shared=InspectSharedLoader(root);
  if(cp&&shared.Present&&shared.Enabled&&!shared.CanProvideCampaign)throw new Exception(shared.Reason);
  if(cp&&shared.CanProvideCampaign) {
   // Exactly one PAK constructor hook owns mounting. The third-party loader
   // reads our own approved PAK in its normal recursively scanned directory.
   byte[] campaignPak;wanted.TryGetValue(CampaignPak,out campaignPak);
   wanted.Remove("Game/Content/Paks/pakchunk0-Windows_999_P.pak");wanted.Remove(CampaignLoader);
   if(campaignPak!=null)wanted.Add(SharedLoader.CampaignPak,campaignPak);next.campaignProvider=SharedLoader.Provider;
  } else next.campaignProvider=cp?"standalone":null;
  if(cp&&loader.ForeignLoader)throw new Exception("Another file already occupies this module path. It has been preserved: "+CampaignLoader+". Keep Korean campaign subtitles OFF to install Mouse and Screen modules with this loader. Coexistence in game is unverified.");
  if(File.Exists(installer)) wanted[Folder+"/Setup.exe"]=File.ReadAllBytes(installer);
  wanted["EasyAntiCheat/KoreanAIR_AC8_Offline.json"]=Encoding.UTF8.GetBytes(Offline(root));
  if(cp||mouse||display) {
   string packPath=Safe(root,Mod+"pack.ini");var packLines=File.Exists(packPath)?File.ReadAllLines(packPath).ToList():new List<string>{"[diagnostics]","enabled=0"};
   string packSection="";var retained=new List<string>();foreach(string line in packLines){string trimmed=line.Trim();if(trimmed.StartsWith("[")&&trimmed.EndsWith("]"))packSection=trimmed.Substring(1,trimmed.Length-2);if(!packSection.Equals("modules",StringComparison.OrdinalIgnoreCase))retained.Add(line);}
   mutable.Add(Mod+"pack.ini");
   wanted[Mod+"pack.ini"]=Encoding.UTF8.GetBytes("[modules]\r\nmouseFlight="+(mouse?"1":"0")+"\r\ndisplay="+(display?"1":"0")+"\r\nsubtitles=1\r\n"+String.Join("\r\n",retained)+"\r\n");
   string mods=Safe(root,"Game/Binaries/Win64/UE4SS/Mods/mods.txt"); string lines=File.Exists(mods)?File.ReadAllText(mods):""; lines=String.Join("\r\n",lines.Split(new[]{'\r','\n'},StringSplitOptions.RemoveEmptyEntries).Where(x=>!System.Text.RegularExpressions.Regex.IsMatch(x,@"^\s*AC8MouseAim\s*:",System.Text.RegularExpressions.RegexOptions.IgnoreCase)).ToArray()); wanted["Game/Binaries/Win64/UE4SS/Mods/mods.txt"]=Encoding.UTF8.GetBytes(lines+"\r\nAC8MouseAim : 1\r\n"); mutable.Add("Game/Binaries/Win64/UE4SS/Mods/mods.txt");
  }
  var oldFiles=(old==null?new List<FileState>():old.files).ToDictionary(x=>x.path,StringComparer.OrdinalIgnoreCase);
  if(next.campaignProvider==SharedLoader.Provider) {
   FileState oldLoader;if(oldFiles.TryGetValue(CampaignLoader,out oldLoader)&&oldLoader.original!=null) {
    string original=Safe(old.backup,oldLoader.original);if(!File.Exists(original))throw new Exception("Original-file backup is missing: "+CampaignLoader);
    string hash=HashFile(original);
    if(hash!=oldLoader.hash&&hash!=next.campaignLoaderHash&&hash!=next.legacyCampaignLoaderHash)throw new Exception("A different loader is preserved in the original-file backup. Shared loading cannot be enabled safely until that loader is reviewed. No files have been changed.");
   }
  }
  if(shared.Present&&shared.Recognized&&shared.RuntimeCompatible) {
   // Transfer the identical shared pair to the independently installed loader.
   // Our uninstall/suspend must not remove another mod's runtime. No unknown
   // replacement DLL is adopted and all other owned files keep their checks.
   next.sharedRuntime=true;
   foreach(string path in new[]{"Game/Binaries/Win64/dwmapi.dll","Game/Binaries/Win64/UE4SS/UE4SS.dll","Game/Binaries/Win64/UE4SS/UE4SS-settings.ini"}) {wanted.Remove(path);mutable.Remove(path);oldFiles.Remove(path);}
  }
  // A replacement supplied by another mod is no longer ours to remove or restore.
  if(!cp&&loader.ForeignLoader)oldFiles.Remove(CampaignLoader);
  var hotasReplacements=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
  foreach(var p in wanted.Keys.ToArray()) {
   string target=Safe(root,p); FileState before; oldFiles.TryGetValue(p,out before);
   if(mutable.Contains(p)&&File.Exists(target)&&p!=Mod+"pack.ini"&&p!="Game/Binaries/Win64/UE4SS/Mods/mods.txt") wanted[p]=File.ReadAllBytes(target);
   if(File.Exists(target)&&HotasReplacement(hotas,mouse,p,HashFile(target)))hotasReplacements.Add(p);
   if(File.Exists(target)&&before==null) { string hash=HashFile(target); string known; bool legacy=manifest.legacy.TryGetValue(p,out known)&&known==hash; bool same=hash==Hash(wanted[p]); bool config=mutable.Contains(p)&&p.StartsWith(Mod,StringComparison.OrdinalIgnoreCase); bool list=p=="Game/Binaries/Win64/UE4SS/Mods/mods.txt"; if(!legacy&&!same&&!config&&!list&&!hotasReplacements.Contains(p)) throw new Exception("Another file already occupies this module path. It has been preserved: "+p); }
   if(before!=null&&File.Exists(target)&&!before.mutable&&p!=Mod+"pack.ini"&&HashFile(target)!=before.hash&&!(String.Equals(p,CampaignLoader,StringComparison.OrdinalIgnoreCase)&&!loader.ForeignLoader)&&!hotasReplacements.Contains(p)) throw new Exception("An installed file was changed outside this installer. It has been preserved: "+p);
  }
  foreach(var f in oldFiles.Values) if(!wanted.ContainsKey(f.path)&&File.Exists(Safe(root,f.path))&&!f.mutable&&HashFile(Safe(root,f.path))!=f.hash) throw new Exception("An installed file was changed and cannot be removed: "+f.path);
  PreflightWrites(root,wanted);
  var journal=new Dictionary<string,byte[]>(StringComparer.OrdinalIgnoreCase); Action<string> capture=p=> { if(!journal.ContainsKey(p)) { string t=Safe(root,p); journal[p]=File.Exists(t)?File.ReadAllBytes(t):null; } };
  try {
   foreach(var f in oldFiles.Values) if(!wanted.ContainsKey(f.path)) {
    capture(f.path);
    if(next.campaignProvider==SharedLoader.Provider&&String.Equals(f.path,CampaignLoader,StringComparison.OrdinalIgnoreCase)) {
     // A backup of the old known campaign loader is preserved as evidence,
     // not restored into a second active constructor hook during migration.
     string path=Safe(root,f.path);if(File.Exists(path))File.Delete(path);
    } else Restore(root,old,f);
   }
   foreach(var pair in wanted) {
    string p=pair.Key,t=Safe(root,p); capture(p); FileState before; oldFiles.TryGetValue(p,out before); string original=before==null?null:before.original;
    // An externally supplied pinned HOTAS replacement became the user's new
    // original after our previous install. Preserve that exact file on removal.
    if(before!=null&&hotasReplacements.Contains(p)&&HashFile(t)!=before.hash){original="original/hotas/"+Guid.NewGuid().ToString("N")+".bin";Atomic(Safe(backup,original),File.ReadAllBytes(t));}
    if(before==null&&File.Exists(t)) { string known; bool legacy=manifest.legacy.TryGetValue(p,out known)&&known==HashFile(t); if(!legacy) { original="original/"+p; Atomic(Safe(backup,original),File.ReadAllBytes(t)); } else Atomic(Safe(backup,"legacy/"+p),File.ReadAllBytes(t)); }
    if(!File.Exists(t)||HashFile(t)!=Hash(pair.Value)) Atomic(t,pair.Value);
    next.files.Add(new FileState{path=p,hash=Hash(pair.Value),original=original,mutable=mutable.Contains(p)});
   }
   foreach(var p in manifest.legacy.Keys) { if(wanted.ContainsKey(p)||oldFiles.ContainsKey(p)||(!cp&&String.Equals(p,CampaignLoader,StringComparison.OrdinalIgnoreCase))||(next.sharedRuntime&&new[]{"Game/Binaries/Win64/dwmapi.dll","Game/Binaries/Win64/UE4SS/UE4SS.dll","Game/Binaries/Win64/UE4SS/UE4SS-settings.ini"}.Contains(p,StringComparer.OrdinalIgnoreCase))) continue; string t=Safe(root,p); if(File.Exists(t)&&HashFile(t)==manifest.legacy[p]) { capture(p); Atomic(Safe(backup,"legacy/"+p),File.ReadAllBytes(t)); File.Delete(t); } }
   capture(Folder+"/installed.json"); Text(Safe(root,Folder+"/installed.json"),Json.Serialize(next));
  } catch(Exception ex) { Rollback(root,journal.Reverse(),ex);throw; }
  Prune(root); 
 }
 static void Restore(string root,State s,FileState f) { string p=Safe(root,f.path); if(f.path=="Game/Binaries/Win64/UE4SS/Mods/mods.txt") { string current=File.Exists(p)?File.ReadAllText(p):"";var lines=current.Split(new[]{'\r','\n'},StringSplitOptions.RemoveEmptyEntries).Where(x=>!System.Text.RegularExpressions.Regex.IsMatch(x,@"^\s*AC8MouseAim\s*:",System.Text.RegularExpressions.RegexOptions.IgnoreCase)).ToList(); if(f.original!=null) { string b=Safe(s.backup,f.original); if(!File.Exists(b)) throw new Exception("Original-file backup is missing: "+f.path); lines.AddRange(File.ReadAllLines(b).Where(x=>System.Text.RegularExpressions.Regex.IsMatch(x,@"^\s*AC8MouseAim\s*:",System.Text.RegularExpressions.RegexOptions.IgnoreCase))); } if(lines.Count>0)Text(p,String.Join("\r\n",lines)+"\r\n");else if(File.Exists(p))File.Delete(p);return; } if(f.original!=null) { string b=Safe(s.backup,f.original); if(!File.Exists(b)) throw new Exception("Original-file backup is missing: "+f.path); Atomic(p,File.ReadAllBytes(b)); } else if(File.Exists(p)) File.Delete(p); }
 public static void Uninstall(string root) { Locked(root,()=>FgLocked(()=>UninstallCore(root))); }
 static void UninstallCore(string root) {
  if(Running(root)) throw new Exception("Close ACE COMBAT 8 before removing modules."); var s=ReadState(root); if(s==null)return;if(s.suspended)Suspend(root,false);s=ReadState(root);
  foreach(var f in s.files) { if(File.Exists(Safe(root,f.path))&&!f.mutable&&HashFile(Safe(root,f.path))!=f.hash) throw new Exception("A changed file has been preserved. Remove it manually or restore the installed version: "+f.path); if(f.original!=null&&!File.Exists(Safe(s.backup,f.original)))throw new Exception("Original-file backup is missing: "+f.path); }
  var journal=new Dictionary<string,byte[]>(StringComparer.OrdinalIgnoreCase);foreach(var f in s.files){string p=Safe(root,f.path);journal[f.path]=File.Exists(p)?File.ReadAllBytes(p):null;}journal[Folder+"/installed.json"]=File.ReadAllBytes(Safe(root,Folder+"/installed.json"));
  ValidateFrameGeneration(root,s);var fg=FgPlan(root,s,null,true,true);
  try{fg.Apply();foreach(var f in s.files)Restore(root,s,f);File.Delete(Safe(root,Folder+"/installed.json"));}catch(Exception ex){try{fg.Undo();}catch(Exception rollback){ex=new AggregateException("Frame generation settings could not be fully restored.",ex,rollback);}Rollback(root,journal,ex);throw;}Prune(root);
 }
 public static void Suspend(string root,bool off) { Locked(root,()=>SuspendCore(root,off)); }
 static void SuspendCore(string root,bool off) { FgLocked(()=>SuspendManagedCore(root,off)); }
 static void SuspendManagedCore(string root,bool off) {
  if(Running(root))throw new Exception("Close ACE COMBAT 8 first.");var s=ReadState(root);if(s==null||s.suspended==off)return;
  ValidateFrameGeneration(root,s);var fg=s.frameGeneration==null?null:FgPlan(root,s,null,off,false);
  var paths=new List<string>{"Game/Binaries/Win64/dinput8.dll","Game/Binaries/Win64/dwmapi.dll","Game/Content/Paks/pakchunk0-Windows_999_P.pak",SharedLoader.CampaignPak};
  if(s.sharedRuntime)paths.Add(Mod+"Scripts/main.lua");var changed=new List<string>();
  try{
   foreach(string p in paths){var f=s.files.FirstOrDefault(x=>x.path==p);if(f==null)continue;string live=Safe(root,p),parked=Safe(root,Folder+"/Disabled/"+p),from=off?live:parked,to=off?parked:live;if(!File.Exists(from)||HashFile(from)!=f.hash||File.Exists(to))throw new Exception("Module state changed outside the launcher: "+p);Directory.CreateDirectory(Path.GetDirectoryName(to));File.Move(from,to);changed.Add(p);}
   if(fg!=null){fg.Apply();s.frameGeneration=fg.lease;}s.suspended=off;Text(Safe(root,Folder+"/installed.json"),Json.Serialize(s));
  }catch(Exception ex){var errors=new List<Exception>{ex};if(fg!=null)try{fg.Undo();}catch(Exception rollback){errors.Add(rollback);}foreach(var p in changed.AsEnumerable().Reverse())try{string a=Safe(root,p),b=Safe(root,Folder+"/Disabled/"+p);File.Move(off?b:a,off?a:b);}catch(Exception rollback){errors.Add(rollback);}if(errors.Count>1)throw new AggregateException("Module state could not be fully restored.",errors);throw;}
 }
 static void EmptyDirectories(string d) { if(!Directory.Exists(d)||(File.GetAttributes(d)&FileAttributes.ReparsePoint)!=0)return;foreach(var sub in Directory.GetDirectories(d))EmptyDirectories(sub);if(!Directory.EnumerateFileSystemEntries(d).Any())Directory.Delete(d); }
 static void Prune(string root) { foreach(string rel in new[]{Folder,"Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim","AC8MouseFlight_Licenses","ACE8Thai_Licenses"}) { string d=Path.GetDirectoryName(Safe(root,rel+"/placeholder"));EmptyDirectories(d); } }
 const string FgMarker="; KoreanAIR AC8 frame generation ";
#if FRAME_GENERATION_TEST
 public static string FrameGenerationTestDirectory;
#endif
 static string FgDirectory() {
#if FRAME_GENERATION_TEST
  if(!String.IsNullOrEmpty(FrameGenerationTestDirectory))return Path.GetFullPath(FrameGenerationTestDirectory);
#endif
  return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),@"BANDAI NAMCO Entertainment\ACE COMBAT 8\Saved\Config\Windows");
 }
 static string FgPath(string file) { return Safe(FgDirectory(),file); }
 static byte[] FgBytes(string path) { if(!File.Exists(path))return null;var info=new FileInfo(path);if(info.Length>131072)throw new Exception("Frame generation configuration is too large. Existing settings have been preserved.");return File.ReadAllBytes(path); }
 static Encoding FgEncoding(string name) {
  if(name=="utf8"||name=="utf8bom")return new UTF8Encoding(false,true);
  if(name=="utf16le")return new UnicodeEncoding(false,false,true);
  if(name=="utf16be")return new UnicodeEncoding(true,false,true);
  throw new Exception("Frame generation ownership record is invalid. Existing settings have been preserved.");
 }
 static string FgDecode(byte[] bytes,out string encoding) {
  bytes=bytes??new byte[0];int skip=0;encoding="utf8";
  if(bytes.Length>=3&&bytes[0]==239&&bytes[1]==187&&bytes[2]==191){encoding="utf8bom";skip=3;}
  else if(bytes.Length>=2&&bytes[0]==255&&bytes[1]==254){encoding="utf16le";skip=2;}
  else if(bytes.Length>=2&&bytes[0]==254&&bytes[1]==255){encoding="utf16be";skip=2;}
  string text=FgEncoding(encoding).GetString(bytes,skip,bytes.Length-skip);
  if(text.IndexOf('\0')>=0)throw new Exception("Frame generation configuration is invalid. Existing settings have been preserved.");return text;
 }
 static readonly Dictionary<string,int> FgKeys=new Dictionary<string,int>(StringComparer.OrdinalIgnoreCase){
  {"r.Streamline.InitializePlugin",1},{"r.Streamline.DLSSG.Enable",2},{"r.Streamline.DLSSG.FramesToGenerate",3},{"t.Streamline.Reflex.Mode",2}};
 static Dictionary<string,int> FgParse(string text,out string section) {
  section="";var values=new Dictionary<string,int>(StringComparer.OrdinalIgnoreCase);
  using(var reader=new StringReader(text))for(string raw;(raw=reader.ReadLine())!=null;){
   string line=raw.Trim();if(line.Length==0||line.StartsWith(";")||line.StartsWith("#"))continue;
   if(line.StartsWith("[")){
    if(!line.EndsWith("]")||line.Length<3||line.Length>162||line.Substring(1,line.Length-2).IndexOfAny(new[]{'[',']','\r','\n','\0'})>=0)throw new Exception("Frame generation configuration is invalid. Existing settings have been preserved.");
    section=line.Substring(1,line.Length-2);continue;
   }
   int equal=line.IndexOf('=');if(equal<1||section.Length==0)throw new Exception("Frame generation configuration is invalid. Existing settings have been preserved.");
   string key=line.Substring(0,equal).Trim();int limit;
   if(section.Equals("ConsoleVariables",StringComparison.OrdinalIgnoreCase)&&FgKeys.TryGetValue(key,out limit)){
    string rawValue=line.Substring(equal+1).Split(';')[0].Trim();int value;
    if(!Int32.TryParse(rawValue,System.Globalization.NumberStyles.None,System.Globalization.CultureInfo.InvariantCulture,out value)||value<0||value>limit||(key.Equals("r.Streamline.DLSSG.FramesToGenerate",StringComparison.OrdinalIgnoreCase)&&value<1))throw new Exception("Frame generation configuration is ambiguous. Existing settings have been preserved.");
    values[key]=value;
   }
  }
  return values;
 }
 static string FgOwner(string root) { return Hash(Encoding.UTF8.GetBytes(Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar).ToLowerInvariant())).Substring(0,16); }
 static byte[] FgBlock(string root,FrameGenerationLease lease) {
  if(lease==null||(lease.newline!="\n"&&lease.newline!="\r\n")||(lease.prefix!=""&&lease.prefix!=lease.newline)||lease.previousSection==null||lease.previousSection.Length>160||lease.previousSection.IndexOfAny(new[]{'[',']','\r','\n','\0'})>=0)throw new Exception("Frame generation ownership record is invalid. Existing settings have been preserved.");
  string n=lease.newline,id=FgOwner(root);
  string block=lease.prefix+FgMarker+"BEGIN "+id+n+"[ConsoleVariables]"+n+
   "r.Streamline.InitializePlugin=1"+n+"r.Streamline.DLSSG.Enable="+(lease.enabled?"1":"0")+n+
   "r.Streamline.DLSSG.FramesToGenerate=1"+n+"t.Streamline.Reflex.Mode=1"+n+FgMarker+"END "+id+n;
  if(lease.previousSection.Length!=0)block+="["+lease.previousSection+"]"+n;
  return FgEncoding(lease.encoding).GetBytes(block);
 }
 static int FgFind(byte[] bytes,byte[] block,int start) { if(bytes==null)return -1;for(int i=start;i<=bytes.Length-block.Length;i++){int j=0;while(j<block.Length&&bytes[i+j]==block[j])j++;if(j==block.Length)return i;}return -1; }
 static int FgValidateBlock(string root,FrameGenerationLease lease,byte[] bytes) {
  string encoding,text=FgDecode(bytes,out encoding),section;
  if(encoding!=lease.encoding)throw new Exception("Frame generation settings changed outside the launcher. Existing settings have been preserved.");
  var block=FgBlock(root,lease);int at=FgFind(bytes,block,0);
  if(at<0||FgFind(bytes,block,at+block.Length)>=0||text.Split(new[]{FgMarker},StringSplitOptions.None).Length!=3)throw new Exception("Frame generation settings changed outside the launcher. Existing settings have been preserved.");
  var values=FgParse(text,out section);int value;
  foreach(var pair in new Dictionary<string,int>{{"r.Streamline.InitializePlugin",1},{"r.Streamline.DLSSG.Enable",lease.enabled?1:0},{"r.Streamline.DLSSG.FramesToGenerate",1},{"t.Streamline.Reflex.Mode",1}})
   if(!values.TryGetValue(pair.Key,out value)||value!=pair.Value)throw new Exception("Frame generation configuration is ambiguous. Existing settings have been preserved.");
  return at;
 }
 sealed class FgMutation {
  public string path;public byte[] before,after;public FileAttributes attributes,nextAttributes;public FrameGenerationLease lease;bool applied;
  static bool Equal(byte[] a,byte[] b){return a==null?b==null:b!=null&&a.SequenceEqual(b);}
  static void Store(string path,byte[] bytes,FileAttributes attributes){
   bool exists=File.Exists(path);FileAttributes old=exists?File.GetAttributes(path):FileAttributes.Normal;bool success=false;
   try{if(exists&&(old&FileAttributes.ReadOnly)!=0)File.SetAttributes(path,old&~FileAttributes.ReadOnly);if(bytes==null){if(File.Exists(path))File.Delete(path);}else{Atomic(path,bytes);File.SetAttributes(path,attributes);}success=true;}
   finally{if(!success&&File.Exists(path))File.SetAttributes(path,old);}
  }
  public void Apply(){if(!Equal(FgBytes(path),before))throw new Exception("Frame generation configuration changed during this operation. Existing settings have been preserved.");if(!Equal(before,after)||attributes!=nextAttributes){Store(path,after,nextAttributes);applied=true;}}
  public void Undo(){if(!applied)return;if(!Equal(FgBytes(path),after))throw new Exception("Frame generation rollback stopped because settings changed outside the launcher.");Store(path,before,attributes);applied=false;}
 }
 static FrameGenerationLease FgCopy(FrameGenerationLease lease) { return lease==null?null:Json.Deserialize<FrameGenerationLease>(Json.Serialize(lease)); }
 static bool FgMissingCreated(FrameGenerationLease lease,byte[] bytes) {
  return bytes==null&&lease!=null&&!lease.originalExists&&!lease.originalReadOnly&&
   lease.encoding=="utf8"&&lease.newline=="\n"&&lease.prefix==""&&lease.previousSection=="";
 }
 static FgMutation FgPlan(string root,State state,bool? enabled,bool release,bool forget) {
  string path=FgPath("Engine.ini");var bytes=FgBytes(path);var attributes=bytes==null?FileAttributes.Normal:File.GetAttributes(path);
  var result=new FgMutation{path=path,before=bytes,after=bytes,attributes=attributes,nextAttributes=attributes,lease=FgCopy(state.frameGeneration)};
  var lease=result.lease;
  // AC8 was observed deleting its generated Engine.ini on normal exit. An
  // absent file created by this lease contains no original file to restore;
  // reconcile just this case. A missing pre-existing Engine.ini still fails.
  if(lease!=null&&lease.live&&FgMissingCreated(lease,bytes)){FgBlock(root,lease);lease.live=false;}
  if(release){
   if(lease==null)return result;
   if(lease.live){int at=FgValidateBlock(root,lease,bytes);var block=FgBlock(root,lease);var tail=bytes.Skip(at+block.Length).ToArray();
    var separator=tail.Length!=0&&lease.prefix.Length!=0?FgEncoding(lease.encoding).GetBytes(lease.prefix):new byte[0];
    result.after=bytes.Take(at).Concat(separator).Concat(tail).ToArray();if(!lease.originalExists&&result.after.Length==0)result.after=null;
    result.nextAttributes=lease.originalReadOnly?attributes|FileAttributes.ReadOnly:attributes&~FileAttributes.ReadOnly;lease.live=false;
   }
   if(forget)result.lease=null;return result;
  }
  if(lease!=null&&lease.live){
   int at=FgValidateBlock(root,lease,bytes);var old=FgBlock(root,lease);lease.enabled=enabled??lease.enabled;
   result.after=bytes.Take(at).Concat(FgBlock(root,lease)).Concat(bytes.Skip(at+old.Length)).ToArray();
  }else{
   string encoding,text=FgDecode(bytes,out encoding),section;FgParse(text,out section);
   if(text.Contains(FgMarker))throw new Exception("Another frame generation ownership block is present. Existing settings have been preserved.");
   string newline=text.Contains("\r\n")?"\r\n":"\n";
   lease=new FrameGenerationLease{enabled=enabled??(lease!=null&&lease.enabled),live=true,originalExists=bytes!=null,originalReadOnly=(attributes&FileAttributes.ReadOnly)!=0,encoding=encoding,newline=newline,prefix=text.Length==0||text.EndsWith("\n")?"":newline,previousSection=section};
   result.lease=lease;result.after=(bytes??new byte[0]).Concat(FgBlock(root,lease)).ToArray();
  }
  // Protect only while our override is live. AC8 removes an unprotected
  // Engine.ini on normal exit; release restores the original ReadOnly flag.
  lease.live=true;result.nextAttributes=attributes|FileAttributes.ReadOnly;return result;
 }
 static void FgLocked(Action action) {
  using(var mutex=new System.Threading.Mutex(false,"Local\\KoreanAIR_AC8_FG_"+Hash(Encoding.UTF8.GetBytes(FgDirectory().ToLowerInvariant())).Substring(0,16))){bool held=false;try{try{held=mutex.WaitOne(0);}catch(System.Threading.AbandonedMutexException){held=true;}if(!held)throw new Exception("Another frame generation operation is already running.");action();}finally{if(held)mutex.ReleaseMutex();}}
 }
 public static void ValidateFrameGeneration(string root,State state) {
  if(state==null||state.frameGeneration==null)return;
  if(state.suspended==state.frameGeneration.live)throw new Exception("Frame generation ownership record does not match the pack state. Existing settings have been preserved.");
  if(state.frameGeneration.live){var bytes=FgBytes(FgPath("Engine.ini"));if(FgMissingCreated(state.frameGeneration,bytes))FgBlock(root,state.frameGeneration);else FgValidateBlock(root,state.frameGeneration,bytes);}
  else FgBlock(root,state.frameGeneration);
 }
 public static bool? FrameGenerationRequested(string root) {
  var state=ReadState(root);if(state!=null&&state.frameGeneration!=null){ValidateFrameGeneration(root,state);return state.frameGeneration.enabled;}
  foreach(string file in new[]{"Engine.ini","GameUserSettings.ini"}){var bytes=FgBytes(FgPath(file));if(bytes==null)continue;string encoding,section;var values=FgParse(FgDecode(bytes,out encoding),out section);int value;if(values.TryGetValue("r.Streamline.DLSSG.Enable",out value))return value!=0;}
  return null;
 }
 static void FgSave(string root,bool? enabled) {
  if(Running(root))throw new Exception("Close ACE COMBAT 8 before changing frame generation. Restart the game to apply the setting.");
  var state=ReadState(root);if(state==null)throw new Exception("Run the installer first.");
  if(enabled.HasValue&&state.suspended)throw new Exception("Resume the mod pack before changing frame generation.");
  ValidateFrameGeneration(root,state);var plan=FgPlan(root,state,enabled,!enabled.HasValue,!enabled.HasValue);
  try{plan.Apply();state.frameGeneration=plan.lease;Text(Safe(root,Folder+"/installed.json"),Json.Serialize(state));}
  catch(Exception ex){try{plan.Undo();}catch(Exception rollback){throw new AggregateException("Frame generation settings could not be fully restored.",ex,rollback);}throw;}
 }
 public static void SetFrameGeneration(string root,bool enabled) { Locked(root,()=>FgLocked(()=>FgSave(root,enabled))); }
 public static void RestoreFrameGeneration(string root) { Locked(root,()=>FgLocked(()=>FgSave(root,null))); }
 public static Dictionary<string,string> ReadUpscalerStatus(string root) {
  var result=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);string path=Config(root,"upscaler_status.ini");
  try{
   if(!File.Exists(path)||new FileInfo(path).Length>2048)return result;
   var values=ReadIni(path,"upscaler_status");string schema,stamp;long sample;
   if(!values.TryGetValue("schema",out schema)||schema!="1"||!values.TryGetValue("sample_unix",out stamp)||!Int64.TryParse(stamp,out sample))return result;
   long now=(long)(DateTime.UtcNow-new DateTime(1970,1,1)).TotalSeconds;if(sample>now+2||now-sample>20)return result;
   foreach(string key in new[]{"dlss_supported","dlss_enabled","dlaa_enabled","dlss_active","dlaa_active","fg_supported","fg_active","fg_last_present_generated"}){string value;if(values.TryGetValue(key,out value)&&(value=="0"||value=="1"||value=="unknown"))result[key]=value;}
   foreach(string key in new[]{"dlss_mode","fg_mode"}){string value;if(values.TryGetValue(key,out value)&&new[]{"unknown","off","auto","dlaa","ultra_quality","quality","balanced","performance","ultra_performance","2x","3x","4x"}.Contains(value))result[key]=value;}
   string source,frames,rate;int count;double hz;
   if(values.TryGetValue("timing_source",out source)&&source=="native_last_present"&&values.TryGetValue("fg_actual_frames",out frames)&&Int32.TryParse(frames,out count)&&count>=1&&count<=4&&values.TryGetValue("fg_frame_rate",out rate)&&Double.TryParse(rate,System.Globalization.NumberStyles.AllowDecimalPoint,System.Globalization.CultureInfo.InvariantCulture,out hz)&&hz>0&&hz<=2000){result["fg_actual_frames"]=count.ToString();result["fg_frame_rate"]=hz.ToString("F1",System.Globalization.CultureInfo.InvariantCulture);result["timing_source"]=source;}
  }catch{}return result;
 }
 public static Dictionary<string,string> ReadIni(string path,string section) { var data=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase); if(!File.Exists(path)) return data; string active=""; foreach(string raw in File.ReadAllLines(path)) { string l=raw.Trim(); if(l.StartsWith("[")&&l.EndsWith("]")) active=l.Substring(1,l.Length-2); else if(active.Equals(section,StringComparison.OrdinalIgnoreCase)&&!l.StartsWith(";")&&!l.StartsWith("#")&&l.Contains("=")) { int i=l.IndexOf('='); data[l.Substring(0,i).Trim()]=l.Substring(i+1).Split(';')[0].Trim(); } } return data; }
 public static void WriteIni(string path,string section,Dictionary<string,string> values) { var lines=File.Exists(path)?File.ReadAllLines(path).ToList():new List<string>(); string active=""; bool found=false; var keys=new HashSet<string>(values.Keys,StringComparer.OrdinalIgnoreCase); for(int i=0;i<lines.Count;i++) { string l=lines[i].Trim(); if(l.StartsWith("[")&&l.EndsWith("]")) { if(active.Equals(section,StringComparison.OrdinalIgnoreCase)) { foreach(var k in keys) lines.Insert(i++,k+"="+values[k]); keys.Clear(); } active=l.Substring(1,l.Length-2); if(active.Equals(section,StringComparison.OrdinalIgnoreCase)) found=true; } else if(active.Equals(section,StringComparison.OrdinalIgnoreCase)&&l.Contains("=")&&!l.StartsWith(";")&&!l.StartsWith("#")) { string k=l.Substring(0,l.IndexOf('=')).Trim(); if(values.ContainsKey(k)) { lines[i]=k+"="+values[k]; keys.Remove(k); } } } if(!found) lines.Add("["+section+"]"); foreach(var k in keys) lines.Add(k+"="+values[k]); Atomic(path,Encoding.Unicode.GetBytes(String.Join("\r\n",lines)+"\r\n").PrependBom()); }
 static byte[] PrependBom(this byte[] bytes) { return Encoding.Unicode.GetPreamble().Concat(bytes).ToArray(); }
 public static string Config(string root,string file) { return Safe(root,Mod+file); }
 static void ValidateLaunchFiles(string root,State s) {
  var hotas=InspectHotas(root);if(s.mouse&&hotas.InputEnabled)throw new Exception(HotasMouseConflict);
  var shared=InspectSharedLoader(root);
  if(s.sharedRuntime&&(!shared.Recognized||!shared.RuntimeCompatible))throw new Exception("The shared mod runtime changed. Existing files were preserved. Reinstall the compatible loader before launching.");
  if(s.campaign&&s.campaignProvider==SharedLoader.Provider&&!shared.CanProvideCampaign)throw new Exception(shared.Reason);
  if(s.campaign&&s.campaignProvider!=SharedLoader.Provider&&shared.Present&&shared.Enabled)throw new Exception("Two campaign/mod loaders would hook the same game function. Close the game and rerun Setup to use one shared loader; existing mod files will be preserved.");
  foreach(var f in s.files.Where(x=>!x.mutable))if(!File.Exists(Safe(root,f.path))||HashFile(Safe(root,f.path))!=f.hash){
   if(hotas.KnownSharedRuntime&&HotasRuntimeHashes.ContainsKey(f.path))throw new Exception(HotasRuntimeRepair);
   throw new Exception("Installation verification failed: "+f.path);
  }
 }
 // Runs only before launch, never in the game's frame/UI path. A game update
 // must not leave an old full-table overlay active after verification fails.
 public static void RefreshCampaignSubtitles(string root) {
  Locked(root,()=>RefreshCampaignSubtitlesCore(root));
 }
 static void RefreshCampaignSubtitlesCore(string root) {
  var s=ReadState(root);if(s==null||!s.campaign||s.suspended)return;
  if(Running(root))throw new Exception("Close ACE COMBAT 8 before refreshing subtitles.");
  string relative=s.campaignProvider==SharedLoader.Provider?SharedLoader.CampaignPak:CampaignPak;
  string target=Safe(root,relative),record=Safe(root,Folder+"/installed.json");
  var owned=s.files.FirstOrDefault(x=>String.Equals(x.path,relative,StringComparison.OrdinalIgnoreCase));
  if(File.Exists(target)&&(owned==null||HashFile(target)!=owned.hash))throw new Exception("A changed subtitle archive has been preserved: "+relative);
  var dictionary=s.files.FirstOrDefault(x=>String.Equals(x.path,CampaignPatch,StringComparison.OrdinalIgnoreCase));
  string patchPath=Safe(root,CampaignPatch);
  if(dictionary==null||!File.Exists(patchPath)||new FileInfo(patchPath).Length>4*1024*1024||HashFile(patchPath)!=dictionary.hash)throw new Exception("Campaign dialogue dictionary verification failed. Rerun Setup.");
  byte[] patch=File.ReadAllBytes(patchPath);CampaignSubtitles.Result result=null;string status=null;
  try {
   string fingerprint=CampaignSubtitles.Fingerprint(root,patch);
   if(s.campaignFingerprint==fingerprint&&owned!=null&&File.Exists(target))return;
   result=CampaignSubtitles.Build(root,patch);status=result.Status;
  } catch(InvalidDataException ex) {status="Original subtitles retained: "+ex.Message;}
    catch(IOException ex) {status="Original subtitles retained: "+ex.Message;}
  var journal=new Dictionary<string,byte[]>(StringComparer.OrdinalIgnoreCase);
  journal[relative]=File.Exists(target)?File.ReadAllBytes(target):null;journal[Folder+"/installed.json"]=File.ReadAllBytes(record);
  try {
   if(result==null){if(File.Exists(target))File.Delete(target);s.files.RemoveAll(x=>String.Equals(x.path,relative,StringComparison.OrdinalIgnoreCase));s.campaignFingerprint=null;}
   else {Atomic(target,result.Pak);if(owned==null){owned=new FileState{path=relative};s.files.Add(owned);}owned.hash=Hash(result.Pak);owned.mutable=false;s.campaignFingerprint=result.Fingerprint;}
   s.campaignStatus=status;Text(record,Json.Serialize(s));
  }catch(Exception ex){Rollback(root,journal.Reverse(),ex);throw;}
 }
 public static void Launch(string root) { Locked(root,()=>LaunchCore(root)); }
 static void LaunchCore(string root) {
  VerifyGame(root);var s=ReadState(root);if(s==null)throw new Exception("Run the installer first.");
  if(Running(root))throw new Exception("ACE COMBAT 8 is already running.");
  if(s.mouse&&InspectHotas(root).InputEnabled)throw new Exception(HotasMouseConflict);
  if(s.suspended)Suspend(root,false);s=ReadState(root);
  RefreshCampaignSubtitlesCore(root);s=ReadState(root);
  ValidateFrameGeneration(root,s);if(s.frameGeneration!=null)FgLocked(()=>FgSave(root,s.frameGeneration.enabled));s=ReadState(root);ValidateLaunchFiles(root,s);
  var p=new ProcessStartInfo(Safe(root,"start_protected_game.exe"),"-SaveToUserDir -anticheat_settings=KoreanAIR_AC8_Offline.json");
  p.WorkingDirectory=root;p.UseShellExecute=false;p.EnvironmentVariables["EOS_USE_ANTICHEATCLIENTNULL"]="1";
  p.EnvironmentVariables["SteamAppId"]="2288340";p.EnvironmentVariables["KOREANAIR_AC8_MODPACK"]="1";
  var pak=s.files.FirstOrDefault(x=>x.path==(s.campaignProvider==SharedLoader.Provider?SharedLoader.CampaignPak:CampaignPak));
  bool translated=s.campaign&&!String.IsNullOrEmpty(s.campaignFingerprint)&&pak!=null;
  p.EnvironmentVariables["KOREANAIR_AC8_CAMPAIGN"]=translated?"1":"0";
  p.EnvironmentVariables["KOREANAIR_AC8_CAMPAIGN_SHA256"]=translated?pak.hash:"";
  p.EnvironmentVariables["KOREANAIR_AC8_CAMPAIGN_SIZE"]=translated?new FileInfo(Safe(root,pak.path)).Length.ToString(System.Globalization.CultureInfo.InvariantCulture):"";
  if(s.campaign&&!translated&&SubtitleFallbackNotice!=null)SubtitleFallbackNotice(s.campaignStatus);
  Process.Start(p);
 }
}
}

namespace KoreanAIR {
// Exact, read-only recognition of the separately installed loader. It is not
// an endorsement of unknown replacement DLLs or proof of an in-game mount.
public sealed class SharedLoaderCompatibility {
 public bool Present,Enabled,Recognized,RuntimeCompatible,CampaignEnabled;
 public string Kind="absent",Reason="No separately installed IoStore loader.";
 public bool CanProvideCampaign { get { return Present&&Enabled&&Recognized&&RuntimeCompatible&&CampaignEnabled; } }
}
public static class SharedLoader {
 public const string Provider="iostore131";
 public const string Root="Game/Binaries/Win64/UE4SS/Mods/IoStoreLoaderMod/";
 public const string Main=Root+"dlls/main.dll";
 public const string CampaignDirectory="KoreanAIRCampaign";
 public const string CampaignPak=Root+CampaignDirectory+"/pakchunk0-Windows_999_P.pak";
 public const string MainHash="fe79479b7346c8d30170e81d3dd759cc44c241c37bed10ce58939a1bebb08789";
 public const string RuntimeHash="680a026890abb4d0df2211251f8defc1681a584275f1521dcc0fe30af480006f";
 public const string ProxyHash="cf440b9eb8643bb7c434acfda696aee57fd981d185dca5e57fb8dbb18f8fc1cd";
 static bool ExactFile(string root,string relative,long maximum,string hash) {
  string path=Core.Safe(root,relative);
  return File.Exists(path)&&new FileInfo(path).Length<=maximum&&Core.HashFile(path)==hash;
 }
 // UE4SS activation is supplied by Core's existing bounded mods.txt/mods.json
 // reader. This avoids implementing a second, subtly different activation rule.
 public static SharedLoaderCompatibility Inspect(string root,bool enabled) {
  var result=new SharedLoaderCompatibility();
  string main=Core.Safe(root,Main);result.Present=File.Exists(main);
  if(!result.Present)return result;
  result.Enabled=enabled;result.Kind="unrecognized";
  if(!ExactFile(root,Main,1048576,MainHash)) {
   result.Reason="A different IoStore loader is installed. Its files have been preserved; coexistence is not verified.";return result;
  }
  result.Recognized=true;result.Kind=Provider;
  result.RuntimeCompatible=ExactFile(root,"Game/Binaries/Win64/UE4SS/UE4SS.dll",67108864,RuntimeHash)&&
    ExactFile(root,"Game/Binaries/Win64/dwmapi.dll",1048576,ProxyHash);
  if(!result.RuntimeCompatible) {
   result.Reason="IoStoreLoaderMod 1.3.1 was recognized, but its shared UE4SS files differ from the tested runtime. Existing files have been preserved.";return result;
  }
  if(!result.Enabled) {result.Reason="IoStoreLoaderMod 1.3.1 is disabled in UE4SS.";return result;}
  result.CampaignEnabled=CampaignOrderEnabled(root);
  if(!result.CampaignEnabled) {result.Reason="KoreanAIRCampaign is disabled in IoStoreLoaderMod/loadorder.txt. Enable that entry in the mod manager before using Korean campaign subtitles.";return result;}
  result.Reason="Recognized IoStoreLoaderMod 1.3.1 with the tested shared UE4SS runtime. In-game mounting still requires verification for this game version.";
  return result;
 }
 public static bool CampaignOrderEnabled(string root) {
  string path=Core.Safe(root,Root+"loadorder.txt");
  if(!File.Exists(path))return true; // Loader's documented unlisted=enabled rule.
  if(new FileInfo(path).Length>262144)throw new IOException("The IoStore load order is too large. Existing files have been preserved.");
  // War's BuildPlan chooses the FIRST matching entry and ignores duplicates.
  // Do not rewrite any user's load order just to enable our own provider.
  foreach(string raw in File.ReadAllLines(path)) {
   string line=raw.Trim(' ','\t','\r','\n','\uFEFF');
   if(line.Length==0||line[0]=='#'||line[0]==';')continue;
   bool enabled=true;
   if(line[0]=='+'||line[0]=='-'){enabled=line[0]=='+';line=line.Substring(1).Trim(' ','\t');}
   line=line.Replace('/','\\');
   if(String.Equals(line,CampaignDirectory,StringComparison.OrdinalIgnoreCase))return enabled;
  }
  return true;
 }
}
}
