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

[assembly:System.Reflection.AssemblyVersion("1.3.0.0")]
[assembly:System.Reflection.AssemblyFileVersion("1.3.0.0")]
[assembly:System.Reflection.AssemblyInformationalVersion("1.3+b2026101302")]
[assembly:System.Reflection.AssemblyProduct("KoreanAIR AC8 Mod Pack")]

namespace KoreanAIR {
public sealed class Item { public string path; public string source; public string hash; public string group; public bool mutable; }
public sealed class FileState { public string path; public string hash; public string original; public bool mutable; }
public sealed class State { public string version="1.3"; public long build; public string root; public bool campaign; public bool mouse; public bool display; public bool suspended; public string backup; public string campaignLoaderHash; public string legacyCampaignLoaderHash; public List<FileState> files=new List<FileState>(); }
public sealed class Manifest { public List<Item> files; public Dictionary<string,string> legacy; }
public sealed class LoaderCompatibility { public bool ForeignLoader; public string Path; public string Hash; public string Kind; }
public sealed class PackWriteException : IOException {
 public readonly string Target,Stage;
 public PackWriteException(string target,string stage,Exception cause):base("Unable to write installed file: "+target+"\n"+cause.Message,cause){Target=target;Stage=stage;}
}
public static class Core {
 public const string Brand="KoreanAIR_AC8_ModPack_1.3";
 public const long ReleaseBuild=2026101302;
 public const string Folder="KoreanAIR_AC8_ModPack";
 public const string Mod="Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/";
 public const string CampaignLoader="Game/Binaries/Win64/dinput8.dll";
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
  Directory.CreateDirectory(Path.GetDirectoryName(path)); string tmp=Path.Combine(Path.GetDirectoryName(path),"."+Guid.NewGuid().ToString("N")+".tmp");
  string stage="write";
  try {
   File.WriteAllBytes(tmp,bytes);stage="commit";
   if(File.Exists(path)) {
#if ATOMIC_TEST
    if(AtomicBeforeCommit!=null)AtomicBeforeCommit(path,tmp);
#endif
    try {File.Replace(tmp,path,null);}
    catch(FileNotFoundException){
     // Recover only a destination-removal race. Never recreate a missing staged file.
     if(File.Exists(tmp)&&!File.Exists(path))File.Move(tmp,path);else throw;
    }
   } else File.Move(tmp,path);
  } catch(IOException ex){throw new PackWriteException(path,stage,ex);}
    catch(UnauthorizedAccessException ex){throw new PackWriteException(path,stage,ex);}
  finally {try{if(File.Exists(tmp))File.Delete(tmp);}catch{}}
 }
#if ATOMIC_TEST
 public static Action<string,string> AtomicBeforeCommit;
#endif
 public static string RecordInstallError(Exception ex) {
  string log=Path.Combine(Path.GetTempPath(),"KoreanAIR_AC8_Setup_error.txt");
  try{File.WriteAllText(log,DateTime.UtcNow.ToString("o")+"\n"+ex.ToString());return log;}catch{return null;}
 }
 static void Rollback(string root,IEnumerable<KeyValuePair<string,byte[]>> journal,Exception initiating) {
  var errors=new List<Exception>{initiating};
  foreach(var entry in journal) {
   try {
    string path=Safe(root,entry.Key);
    if(entry.Value==null){if(File.Exists(path))File.Delete(path);}
    else if(!File.Exists(path)||!File.ReadAllBytes(path).SequenceEqual(entry.Value))Atomic(path,entry.Value);
   }catch(Exception ex){errors.Add(ex);}
  }
  if(errors.Count>1)throw new AggregateException("Rollback could not restore every file.",errors);
 }
 public static void Text(string path,string text) { Atomic(path,new UTF8Encoding(false).GetBytes(text)); }
 public static State ReadState(string root) { string p=Safe(root,Folder+"/installed.json"); if(!File.Exists(p)) return null; var s=Json.Deserialize<State>(File.ReadAllText(p)); if(s==null||!String.Equals(Path.GetFullPath(s.root).TrimEnd(Path.DirectorySeparatorChar),Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar),StringComparison.OrdinalIgnoreCase)) throw new Exception("Installation record belongs to another game folder."); foreach(var f in s.files) { Safe(root,f.path); if(f.original!=null) Safe(s.backup,f.original); } return s; }
 public static bool Running(string root) { foreach(var p in Process.GetProcessesByName("AceCombat8")) { try { if(String.Equals(p.MainModule.FileName,Safe(root,"Game/Binaries/Win64/AceCombat8.exe"),StringComparison.OrdinalIgnoreCase)) return true; } catch { return true; } } return false; }
 public static void VerifyGame(string root) {
  string exe=Safe(root,"Game/Binaries/Win64/AceCombat8.exe"); if(!File.Exists(exe)||!File.Exists(Safe(root,"start_protected_game.exe"))) throw new Exception("Select the ACE COMBAT 8 game folder containing start_protected_game.exe.");
  using(var b=new BinaryReader(File.OpenRead(exe))) { if(b.ReadUInt16()!=0x5A4D) throw new Exception("Invalid game executable."); b.BaseStream.Position=0x3C; int pe=b.ReadInt32(); if(pe<64||pe>b.BaseStream.Length-120) throw new Exception("Invalid executable header."); b.BaseStream.Position=pe; if(b.ReadUInt32()!=0x4550||b.ReadUInt16()!=0x8664) throw new Exception("The 64-bit game is required."); b.BaseStream.Position=pe+8; uint timestamp=b.ReadUInt32(); b.BaseStream.Position=pe+24+56; uint size=b.ReadUInt32(); if(timestamp!=0x6AA0E27D||size!=0x2195A000) throw new Exception("This game build is not supported. No files have been changed."); }
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
 static string Offline(string root) { var o=Json.Deserialize<Dictionary<string,object>>(File.ReadAllText(Safe(root,"EasyAntiCheat/Settings.json"))); if(!o.ContainsKey("executable")||!String.Equals(Convert.ToString(o["executable"]),"Game/Binaries/Win64/AceCombat8.exe",StringComparison.OrdinalIgnoreCase)) throw new Exception("Unexpected game launch configuration."); o["allow_null_client"]="true"; return Json.Serialize(o); }
 static void Locked(string root,Action action) { using(var gate=new System.Threading.Mutex(false,"Local\\KoreanAIR_AC8_"+Hash(Encoding.UTF8.GetBytes(Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar).ToLowerInvariant())).Substring(0,16))) { bool held=false;try{try{held=gate.WaitOne(0);}catch(System.Threading.AbandonedMutexException){held=true;}if(!held)throw new Exception("Another pack operation is already running for this game folder.");action();}finally{if(held)gate.ReleaseMutex();} } }
 public static void Install(string root,bool cp,bool mouse,bool display,Stream payload,string installer) { Locked(root,()=>InstallCore(root,cp,mouse,display,payload,installer)); }
 public static void UpdatePreservingState(string root,Stream payload,string installer) { Locked(root,()=>{
  if(Running(root))throw new Exception("Close ACE COMBAT 8 before changing installed modules.");
  var before=ReadState(root);if(before==null)throw new Exception("Run the installer first.");
  bool parked=before.suspended;
  try {
   if(parked)SuspendCore(root,false);
   InstallCore(root,before.campaign,before.mouse,before.display,payload,installer);
  } finally {
   if(parked){var current=ReadState(root);if(current!=null&&!current.suspended)SuspendCore(root,true);}
  }
 }); }
 static void InstallCore(string root,bool cp,bool mouse,bool display,Stream payload,string installer) {
  root=Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar); VerifyGame(root); if(Running(root)) throw new Exception("Close ACE COMBAT 8 before changing installed modules."); if(!cp&&!mouse&&!display) { Uninstall(root); return; }
  State old=ReadState(root); if(old!=null&&old.suspended) throw new Exception("Resume the installed modules before updating them.");
  string backup=old==null?Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),Folder,"Backups",Hash(Encoding.UTF8.GetBytes(root.ToLowerInvariant())).Substring(0,16),DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff")):old.backup;
  var next=new State{build=ReleaseBuild,root=root,campaign=cp,mouse=mouse,display=display,backup=backup};
  var wanted=new Dictionary<string,byte[]>(StringComparer.OrdinalIgnoreCase); var mutable=new HashSet<string>(StringComparer.OrdinalIgnoreCase); Manifest manifest;
  using(var zip=new ZipArchive(payload,ZipArchiveMode.Read)) {
   manifest=ReadManifest(zip);
   foreach(var f in manifest.files) { Safe(root,f.path); if(!Selected(f.group,cp,mouse,display)) continue; var bytes=Entry(zip,f.source); if(Hash(bytes)!=f.hash) throw new Exception("Payload integrity check failed: "+f.path); wanted.Add(f.path,bytes); if(f.mutable) mutable.Add(f.path); }
  }
  next.campaignLoaderHash=CampaignHash(manifest);next.legacyCampaignLoaderHash=LegacyCampaignHash(manifest);
  var loader=InspectCampaignLoader(root,old,next.campaignLoaderHash,next.legacyCampaignLoaderHash);
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
  // A replacement supplied by another mod is no longer ours to remove or restore.
  if(!cp&&loader.ForeignLoader)oldFiles.Remove(CampaignLoader);
  foreach(var p in wanted.Keys.ToArray()) {
   string target=Safe(root,p); FileState before; oldFiles.TryGetValue(p,out before);
   if(mutable.Contains(p)&&File.Exists(target)&&p!=Mod+"pack.ini"&&p!="Game/Binaries/Win64/UE4SS/Mods/mods.txt") wanted[p]=File.ReadAllBytes(target);
   if(File.Exists(target)&&before==null) { string hash=HashFile(target); string known; bool legacy=manifest.legacy.TryGetValue(p,out known)&&known==hash; bool same=hash==Hash(wanted[p]); bool config=mutable.Contains(p)&&p.StartsWith(Mod,StringComparison.OrdinalIgnoreCase); bool list=p=="Game/Binaries/Win64/UE4SS/Mods/mods.txt"; if(!legacy&&!same&&!config&&!list) throw new Exception("Another file already occupies this module path. It has been preserved: "+p); }
   if(before!=null&&File.Exists(target)&&!before.mutable&&p!=Mod+"pack.ini"&&HashFile(target)!=before.hash&&!(String.Equals(p,CampaignLoader,StringComparison.OrdinalIgnoreCase)&&!loader.ForeignLoader)) throw new Exception("An installed file was changed outside this installer. It has been preserved: "+p);
  }
  foreach(var f in oldFiles.Values) if(!wanted.ContainsKey(f.path)&&File.Exists(Safe(root,f.path))&&!f.mutable&&HashFile(Safe(root,f.path))!=f.hash) throw new Exception("An installed file was changed and cannot be removed: "+f.path);
  var journal=new Dictionary<string,byte[]>(StringComparer.OrdinalIgnoreCase); Action<string> capture=p=> { if(!journal.ContainsKey(p)) { string t=Safe(root,p); journal[p]=File.Exists(t)?File.ReadAllBytes(t):null; } };
  try {
   foreach(var f in oldFiles.Values) if(!wanted.ContainsKey(f.path)) { capture(f.path); Restore(root,old,f); }
   foreach(var pair in wanted) {
    string p=pair.Key,t=Safe(root,p); capture(p); FileState before; oldFiles.TryGetValue(p,out before); string original=before==null?null:before.original;
    if(before==null&&File.Exists(t)) { string known; bool legacy=manifest.legacy.TryGetValue(p,out known)&&known==HashFile(t); if(!legacy) { original="original/"+p; Atomic(Safe(backup,original),File.ReadAllBytes(t)); } else Atomic(Safe(backup,"legacy/"+p),File.ReadAllBytes(t)); }
    if(!File.Exists(t)||HashFile(t)!=Hash(pair.Value)) Atomic(t,pair.Value);
    next.files.Add(new FileState{path=p,hash=Hash(pair.Value),original=original,mutable=mutable.Contains(p)});
   }
   foreach(var p in manifest.legacy.Keys) { if(wanted.ContainsKey(p)||oldFiles.ContainsKey(p)||(!cp&&String.Equals(p,CampaignLoader,StringComparison.OrdinalIgnoreCase))) continue; string t=Safe(root,p); if(File.Exists(t)&&HashFile(t)==manifest.legacy[p]) { capture(p); Atomic(Safe(backup,"legacy/"+p),File.ReadAllBytes(t)); File.Delete(t); } }
   capture(Folder+"/installed.json"); Text(Safe(root,Folder+"/installed.json"),Json.Serialize(next));
  } catch(Exception ex) { Rollback(root,journal.Reverse(),ex);throw; }
  Prune(root); 
 }
 static void Restore(string root,State s,FileState f) { string p=Safe(root,f.path); if(f.path=="Game/Binaries/Win64/UE4SS/Mods/mods.txt") { string current=File.Exists(p)?File.ReadAllText(p):"";var lines=current.Split(new[]{'\r','\n'},StringSplitOptions.RemoveEmptyEntries).Where(x=>!System.Text.RegularExpressions.Regex.IsMatch(x,@"^\s*AC8MouseAim\s*:",System.Text.RegularExpressions.RegexOptions.IgnoreCase)).ToList(); if(f.original!=null) { string b=Safe(s.backup,f.original); if(!File.Exists(b)) throw new Exception("Original-file backup is missing: "+f.path); lines.AddRange(File.ReadAllLines(b).Where(x=>System.Text.RegularExpressions.Regex.IsMatch(x,@"^\s*AC8MouseAim\s*:",System.Text.RegularExpressions.RegexOptions.IgnoreCase))); } if(lines.Count>0)Text(p,String.Join("\r\n",lines)+"\r\n");else if(File.Exists(p))File.Delete(p);return; } if(f.original!=null) { string b=Safe(s.backup,f.original); if(!File.Exists(b)) throw new Exception("Original-file backup is missing: "+f.path); Atomic(p,File.ReadAllBytes(b)); } else if(File.Exists(p)) File.Delete(p); }
 public static void Uninstall(string root) { Locked(root,()=>UninstallCore(root)); }
 static void UninstallCore(string root) {
  if(Running(root)) throw new Exception("Close ACE COMBAT 8 before removing modules."); var s=ReadState(root); if(s==null)return;if(s.suspended)Suspend(root,false);s=ReadState(root);
  foreach(var f in s.files) { if(File.Exists(Safe(root,f.path))&&!f.mutable&&HashFile(Safe(root,f.path))!=f.hash) throw new Exception("A changed file has been preserved. Remove it manually or restore the installed version: "+f.path); if(f.original!=null&&!File.Exists(Safe(s.backup,f.original)))throw new Exception("Original-file backup is missing: "+f.path); }
  var journal=new Dictionary<string,byte[]>(StringComparer.OrdinalIgnoreCase);foreach(var f in s.files){string p=Safe(root,f.path);journal[f.path]=File.Exists(p)?File.ReadAllBytes(p):null;}journal[Folder+"/installed.json"]=File.ReadAllBytes(Safe(root,Folder+"/installed.json"));
  try{foreach(var f in s.files)Restore(root,s,f);File.Delete(Safe(root,Folder+"/installed.json"));}catch(Exception ex){Rollback(root,journal,ex);throw;}Prune(root);
 }
 public static void Suspend(string root,bool off) { Locked(root,()=>SuspendCore(root,off)); } static void SuspendCore(string root,bool off) { if(Running(root)) throw new Exception("Close ACE COMBAT 8 first."); var s=ReadState(root); if(s==null||s.suspended==off) return; string[] paths={"Game/Binaries/Win64/dinput8.dll","Game/Binaries/Win64/dwmapi.dll","Game/Content/Paks/pakchunk0-Windows_999_P.pak"}; var changed=new List<string>(); try { foreach(string p in paths) { var f=s.files.FirstOrDefault(x=>x.path==p); if(f==null) continue; string live=Safe(root,p),parked=Safe(root,Folder+"/Disabled/"+p); string from=off?live:parked,to=off?parked:live; if(!File.Exists(from)||HashFile(from)!=f.hash||File.Exists(to)) throw new Exception("Module state changed outside the launcher: "+p); Directory.CreateDirectory(Path.GetDirectoryName(to)); File.Move(from,to); changed.Add(p); } s.suspended=off; Text(Safe(root,Folder+"/installed.json"),Json.Serialize(s)); } catch { foreach(var p in changed.AsEnumerable().Reverse()) { string a=Safe(root,p),b=Safe(root,Folder+"/Disabled/"+p); File.Move(off?b:a,off?a:b); } throw; } }
 static void EmptyDirectories(string d) { if(!Directory.Exists(d)||(File.GetAttributes(d)&FileAttributes.ReparsePoint)!=0)return;foreach(var sub in Directory.GetDirectories(d))EmptyDirectories(sub);if(!Directory.EnumerateFileSystemEntries(d).Any())Directory.Delete(d); }
 static void Prune(string root) { foreach(string rel in new[]{Folder,"Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim","AC8MouseFlight_Licenses","ACE8Thai_Licenses"}) { string d=Path.GetDirectoryName(Safe(root,rel+"/placeholder"));EmptyDirectories(d); } }
 public static Dictionary<string,string> ReadIni(string path,string section) { var data=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase); if(!File.Exists(path)) return data; string active=""; foreach(string raw in File.ReadAllLines(path)) { string l=raw.Trim(); if(l.StartsWith("[")&&l.EndsWith("]")) active=l.Substring(1,l.Length-2); else if(active.Equals(section,StringComparison.OrdinalIgnoreCase)&&!l.StartsWith(";")&&!l.StartsWith("#")&&l.Contains("=")) { int i=l.IndexOf('='); data[l.Substring(0,i).Trim()]=l.Substring(i+1).Split(';')[0].Trim(); } } return data; }
 public static void WriteIni(string path,string section,Dictionary<string,string> values) { var lines=File.Exists(path)?File.ReadAllLines(path).ToList():new List<string>(); string active=""; bool found=false; var keys=new HashSet<string>(values.Keys,StringComparer.OrdinalIgnoreCase); for(int i=0;i<lines.Count;i++) { string l=lines[i].Trim(); if(l.StartsWith("[")&&l.EndsWith("]")) { if(active.Equals(section,StringComparison.OrdinalIgnoreCase)) { foreach(var k in keys) lines.Insert(i++,k+"="+values[k]); keys.Clear(); } active=l.Substring(1,l.Length-2); if(active.Equals(section,StringComparison.OrdinalIgnoreCase)) found=true; } else if(active.Equals(section,StringComparison.OrdinalIgnoreCase)&&l.Contains("=")&&!l.StartsWith(";")&&!l.StartsWith("#")) { string k=l.Substring(0,l.IndexOf('=')).Trim(); if(values.ContainsKey(k)) { lines[i]=k+"="+values[k]; keys.Remove(k); } } } if(!found) lines.Add("["+section+"]"); foreach(var k in keys) lines.Add(k+"="+values[k]); Atomic(path,Encoding.Unicode.GetBytes(String.Join("\r\n",lines)+"\r\n").PrependBom()); }
 static byte[] PrependBom(this byte[] bytes) { return Encoding.Unicode.GetPreamble().Concat(bytes).ToArray(); }
 public static string Config(string root,string file) { return Safe(root,Mod+file); }
 public static void Launch(string root) { Locked(root,()=>LaunchCore(root)); } static void LaunchCore(string root) { VerifyGame(root); var s=ReadState(root); if(s==null) throw new Exception("Run the installer first."); if(Running(root)) throw new Exception("ACE COMBAT 8 is already running."); if(s.suspended) Suspend(root,false); s=ReadState(root); foreach(var f in s.files.Where(x=>!x.mutable)) if(!File.Exists(Safe(root,f.path))||HashFile(Safe(root,f.path))!=f.hash) throw new Exception("Installation verification failed: "+f.path); var p=new ProcessStartInfo(Safe(root,"start_protected_game.exe"),"-SaveToUserDir -anticheat_settings=KoreanAIR_AC8_Offline.json"); p.WorkingDirectory=root;p.UseShellExecute=false; p.EnvironmentVariables["EOS_USE_ANTICHEATCLIENTNULL"]="1";p.EnvironmentVariables["SteamAppId"]="2288340";p.EnvironmentVariables["KOREANAIR_AC8_MODPACK"]="1";p.EnvironmentVariables["KOREANAIR_AC8_CAMPAIGN"]=s.campaign?"1":"0";Process.Start(p); }
}
}
