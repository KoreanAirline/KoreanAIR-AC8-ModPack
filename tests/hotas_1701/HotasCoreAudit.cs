using System;
using System.IO;
using System.IO.Compression;
using System.Text;
using System.Linq;
using System.Collections.Generic;
using System.Reflection;
using KoreanAIR;

class HotasCoreAudit {
 static string home,download,game;static int checks;
 const string Mods="Game/Binaries/Win64/UE4SS/Mods/",Proxy="Game/Binaries/Win64/dwmapi.dll",Runtime="Game/Binaries/Win64/UE4SS/UE4SS.dll";
 static void Check(bool pass,string name){if(!pass)throw new Exception("FAIL "+name);++checks;Console.WriteLine("PASS "+name);}
 static void Put(string root,string path,byte[] bytes){var p=Core.Safe(root,path);Directory.CreateDirectory(Path.GetDirectoryName(p));File.WriteAllBytes(p,bytes);}
 static void Put(string root,string path,string text){Put(root,path,new UTF8Encoding(false).GetBytes(text));}
 static string New(string name){string root=Path.Combine(home,name);Directory.CreateDirectory(root);var bytes=new byte[1024];using(var m=new MemoryStream(bytes))using(var b=new BinaryWriter(m)){b.Write((ushort)0x5a4d);m.Position=0x3c;b.Write(128);m.Position=128;b.Write(0x4550);b.Write((ushort)0x8664);m.Position=136;b.Write(0x6AA0E27D);m.Position=208;b.Write(0x2195A000);}Put(root,"Game/Binaries/Win64/AceCombat8.exe",bytes);Put(root,"start_protected_game.exe",bytes);Put(root,"EasyAntiCheat/Settings.json","{\"executable\":\"Game/Binaries/Win64/AceCombat8.exe\"}");Core.FrameGenerationTestDirectory=Path.Combine(root,"isolated-settings");return root;}
 static void AddHotas(string root,bool on=true,bool foreign=true){
  foreach(string rel in new[]{"AC8HOTAS/bindings.lua","AC8HOTAS/Scripts/main.lua","AC8HOTAS/Scripts/ac8_hotas_devices_001.dll","AC8AnalogYaw/Scripts/main.lua","AC8AnalogYaw/Scripts/ac8_analog_yaw_013.dll"})Put(root,Mods+rel,File.ReadAllBytes(Path.Combine(download,Mods+rel)));
  Put(root,Mods+"mods.txt","OtherMod : 1\r\nAC8HOTAS : "+(on?"1":"0")+"\r\nAC8AnalogYaw : "+(on?"1":"0")+"\r\n");
  Put(root,Mods+"mods.json","[{\"mod_name\":\"AC8HOTAS\",\"mod_enabled\":"+(on?"true":"false")+"},{\"mod_name\":\"AC8AnalogYaw\",\"mod_enabled\":"+(on?"true":"false")+"}]");
  if(foreign)foreach(string p in new[]{Proxy,Runtime})Put(root,p,File.ReadAllBytes(Path.Combine(download,p)));
 }
 static Dictionary<string,string> HotasFiles(string root){var map=new Dictionary<string,string>();foreach(string name in new[]{"AC8HOTAS","AC8AnalogYaw"}){string p=Core.Safe(root,Mods+name+"/placeholder");string folder=Path.GetDirectoryName(p);if(Directory.Exists(folder))foreach(string f in Directory.GetFiles(folder,"*",SearchOption.AllDirectories))map[f.Substring(root.Length+1)]=Core.HashFile(f);}return map;}
 static bool SameFiles(string root,Dictionary<string,string> before){var after=HotasFiles(root);return after.Count==before.Count&&before.All(x=>after.ContainsKey(x.Key)&&after[x.Key]==x.Value);}
 static MemoryStream Payload(){var memory=new MemoryStream();var items=new List<Item>();using(var z=new ZipArchive(memory,ZipArchiveMode.Create,true)){
  Action<string,byte[],bool> add=(path,data,mutable)=>{string key="payload/"+path;items.Add(new Item{path=path,source=key,hash=Core.Hash(data),group="runtime",mutable=mutable});using(var s=z.CreateEntry(key).Open())s.Write(data,0,data.Length);};
  foreach(string p in new[]{Proxy,Runtime})add(p,File.ReadAllBytes(Path.Combine(game,p)),false);
  add(Core.Mod+"config.ini",Encoding.UTF8.GetBytes("[control]\nsensitivity=0.04\n"),true);
  add(Core.Mod+"Scripts/main.lua",Encoding.UTF8.GetBytes("-- harmless fixture, never executed\n"),false);
  byte[] json=Encoding.UTF8.GetBytes(Core.Json.Serialize(new Manifest{files=items,legacy=new Dictionary<string,string>()}));using(var s=z.CreateEntry("manifest.json").Open())s.Write(json,0,json.Length);
 }memory.Position=0;return memory;}
 static void Install(string root,bool mouse){using(var p=Payload())Core.Install(root,false,mouse,true,p,Path.Combine(root,"nonexistent-setup"));}
 static string Error(Action a){try{a();return null;}catch(Exception e){return e.Message;}}
 static string Validate(string root){try{typeof(Core).GetMethod("ValidateLaunchFiles",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{root,Core.ReadState(root)});return null;}catch(TargetInvocationException e){return e.InnerException.Message;}}
 static void AssertCanonical(string root,string label){foreach(string p in new[]{Proxy,Runtime})Check(Core.HashFile(Core.Safe(root,p))==Core.HashFile(Path.Combine(game,p)),label+" canonical "+p);}
 static void Fresh(){string root=New("foreign-first");AddHotas(root);var original=HotasFiles(root);var info=Core.InspectHotas(root);Check(info.Present&&info.InputEnabled&&info.KnownSharedRuntime&&info.HotasEnabled&&info.AnalogYawEnabled,"recognizes exact supplied package");
  string error=Error(()=>Install(root,true));Check(error==Core.HotasMouseConflict,"enabled input mods reject Mouse flight before mutation");Check(!File.Exists(Core.Safe(root,Core.Folder+"/installed.json"))&&SameFiles(root,original),"conflict leaves existing HOTAS untouched");
  Install(root,false);AssertCanonical(root,"fresh");Check(SameFiles(root,original),"fresh install preserves all HOTAS native files and bindings");Check(!Core.ReadState(root).mouse&&Core.ReadState(root).display,"screen-only module selection retained");Check(File.ReadAllText(Core.Safe(root,Mods+"mods.txt")).Contains("OtherMod : 1")&&File.ReadAllText(Core.Safe(root,Mods+"mods.txt")).Contains("AC8HOTAS : 1"),"shared mod rows retained");Check(Validate(root)==null,"canonical runtime and enabled HOTAS pass screen-only launch preflight");
  Install(root,false);Core.Uninstall(root);foreach(string p in new[]{Proxy,Runtime})Check(Core.HashFile(Core.Safe(root,p))==Core.HashFile(Path.Combine(download,p)),"fresh uninstall restores foreign "+p);Check(SameFiles(root,original),"fresh uninstall keeps HOTAS bindings");Check(!File.ReadAllText(Core.Safe(root,Mods+"mods.txt")).Contains("AC8MouseAim"),"uninstall only removes our mod row");
 }
 static void OursFirst(){string root=New("ours-first");Install(root,true);AddHotas(root);Put(root,Core.Mod+"config.ini","[control]\nsensitivity=0.093\n");var original=HotasFiles(root);
  Check(Validate(root)==Core.HotasMouseConflict,"installing HOTAS later blocks conflicting active Mouse flight");Check(Error(()=>Install(root,true))==Core.HotasMouseConflict,"update cannot silently keep conflicting mouse enabled");
  Install(root,false);AssertCanonical(root,"ours-first");Check(SameFiles(root,original),"repair keeps HOTAS bindings byte-for-byte");Check(File.ReadAllText(Core.Safe(root,Core.Mod+"config.ini")).Contains("0.093"),"repair preserves existing mouse settings");
  AddHotas(root);Check(Validate(root)==Core.HotasRuntimeRepair,"foreign shared replacement gives repair guidance without launching");Install(root,false);Core.Uninstall(root);
  foreach(string p in new[]{Proxy,Runtime})Check(Core.HashFile(Core.Safe(root,p))==Core.HashFile(Path.Combine(download,p)),"ours-first uninstall restores latest external replacement "+p);Check(SameFiles(root,original),"ours-first uninstall keeps other mod files");
 }
 static void Rejections(){
  string root=New("unknown-runtime");AddHotas(root);Put(root,Runtime,"unrecognized runtime bytes");var before=File.ReadAllBytes(Core.Safe(root,Proxy));Check(!Core.InspectHotas(root).KnownSharedRuntime,"mixed unknown runtime is never recognized");Check(Error(()=>Install(root,false))!=null,"unknown shared runtime refused");Check(before.SequenceEqual(File.ReadAllBytes(Core.Safe(root,Proxy)))&&!File.Exists(Core.Safe(root,Core.Folder+"/installed.json")),"unknown pair refusal is atomic");
  root=New("orphan-pinned");foreach(string p in new[]{Proxy,Runtime})Put(root,p,File.ReadAllBytes(Path.Combine(download,p)));Check(!Core.InspectHotas(root).Present,"pinned hashes alone do not impersonate installed HOTAS");Check(Error(()=>Install(root,false))!=null,"orphan pinned runtime remains protected");
  root=New("changed-owned-unknown");Install(root,false);Put(root,Proxy,"other unknown proxy");Check(Error(()=>Install(root,false))!=null,"unknown change to owned immutable file still refused");Check(File.ReadAllText(Core.Safe(root,Proxy))=="other unknown proxy","unknown replacement preserved");
  root=New("disabled-hotAS");Install(root,true);AddHotas(root,false,false);var status=Core.InspectHotas(root);Check(status.Present&&!status.InputEnabled,"both lists disabled is distinguished from enabled input");Install(root,true);Check(Validate(root)==null,"disabled input mods do not block mouse with canonical runtime");
  Put(root,Mods+"mods.json","[{\"mod_name\":\"AC8HOTAS\",\"mod_enabled\":true}]");Check(Core.InspectHotas(root).InputEnabled,"JSON-enabled entry is not bypassed by text-disabled entry");Check(Validate(root)==Core.HotasMouseConflict,"conflicting lists fail conservatively");
  Put(root,Mods+"mods.json","[]");Put(root,Mods+"mods.txt","AC8HOTAS : 1\nAC8HOTAS : 0\n");Check(Core.InspectHotas(root).InputEnabled,"duplicate conflicting text rows cannot bypass input protection");
  File.Delete(Core.Safe(root,Mods+"mods.txt"));File.Delete(Core.Safe(root,Mods+"mods.json"));Put(root,Mods+"AC8HOTAS/enabled.txt","");Check(Core.InspectHotas(root).InputEnabled,"enabled marker without lists is detected");
  File.Delete(Core.Safe(root,Mods+"AC8HOTAS/enabled.txt"));Put(root,Mods+"mods.json","[{\"mod_name\":\"AC8HOTAS\",\"mod_enabled\":\"false\"}]");Check(Error(()=>Core.InspectHotas(root))!=null,"malformed enabled value refuses ambiguous list");
  Put(root,Mods+"mods.json","[]");Put(root,Mods+"mods.txt","AC8HOTAS : unknown\n");Check(Error(()=>Core.InspectHotas(root))!=null,"malformed text enabled value refuses ambiguous list");
 }
 static int Main(string[] args){try{home=Path.GetFullPath(args[0]);download=Path.GetFullPath(args[1]);game=Path.GetFullPath(args[2]);if(Directory.Exists(home))throw new Exception("Use a new isolated fixture directory.");if(!home.Contains(Path.DirectorySeparatorChar+"tests"+Path.DirectorySeparatorChar))throw new Exception("Unsafe fixture path.");Directory.CreateDirectory(home);Fresh();OursFirst();Rejections();Console.WriteLine("PASS "+checks+" production Core compatibility cases; no game or downloaded DLL executed.");return 0;}catch(Exception e){Console.WriteLine("ERROR "+e.GetType().Name+" "+e.Message);Console.WriteLine(e.StackTrace);return 1;}}
}
