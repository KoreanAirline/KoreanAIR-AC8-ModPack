using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Reflection;
using KoreanAIR;
static class SharedProviderIntegrationTests {
 static string destination,bin,payload;static int checks;
 static void Check(bool ok,string name) {if(!ok)throw new Exception(name);++checks;Console.WriteLine("PASS: "+name);}
 static void Put(string root,string relative,byte[] bytes) {string p=Core.Safe(root,relative);Directory.CreateDirectory(Path.GetDirectoryName(p));File.WriteAllBytes(p,bytes);}
 static void Text(string root,string relative,string value) {Put(root,relative,System.Text.Encoding.UTF8.GetBytes(value));}
 static bool Has(string root,string relative) {return File.Exists(Core.Safe(root,relative));}
 static string Hash(string root,string relative) {return Core.HashFile(Core.Safe(root,relative));}
 static string Fake(string name) {
  string root=Path.Combine(destination,name);byte[] exe=new byte[1024];
  Action<int,byte[]> put=(offset,value)=>Buffer.BlockCopy(value,0,exe,offset,value.Length);
  put(0,BitConverter.GetBytes((ushort)0x5a4d));put(0x3c,BitConverter.GetBytes(128));put(128,BitConverter.GetBytes(0x4550));put(132,BitConverter.GetBytes((ushort)0x8664));put(136,BitConverter.GetBytes(0x6ad2d0a7));put(152,BitConverter.GetBytes((ushort)0x20b));put(208,BitConverter.GetBytes(0x215a2000));
  Put(root,"Game/Binaries/Win64/AceCombat8.exe",exe);Put(root,"start_protected_game.exe",exe);
  Text(root,"EasyAntiCheat/Settings.json","{\"executable\":\"Game/Binaries/Win64/AceCombat8.exe\"}");return root;
 }
 static void Install(string root) {using(var stream=File.OpenRead(payload))Core.Install(root,true,true,true,stream,"");}
 static void External(string root,bool runtime) {
  Put(root,SharedLoader.Main,File.ReadAllBytes(Path.Combine(bin,"ue4ss/Mods/IoStoreLoaderMod/dlls/main.dll")));
  Text(root,SharedLoader.Root+"enabled.txt","");
  Text(root,SharedLoader.Root+"loadorder.txt","# user order\r\n+Falken_addon\r\n-AnotherMod\r\n");
  Text(root,"Game/Binaries/Win64/UE4SS/Mods/falken-us4ss/enabled.txt","");
  Text(root,"Game/Binaries/Win64/UE4SS/Mods/falken-us4ss/Scripts/main.lua","-- inert fixture; never executed\r\n");
  if(runtime) {
   Put(root,"Game/Binaries/Win64/UE4SS/UE4SS.dll",File.ReadAllBytes(Path.Combine(bin,"ue4ss/UE4SS.dll")));
   Put(root,"Game/Binaries/Win64/dwmapi.dll",File.ReadAllBytes(Path.Combine(bin,"dwmapi.dll")));
   Text(root,"Game/Binaries/Win64/UE4SS/UE4SS-settings.ini","[fixture]\r\nexternal=preserved\r\n");
  }
 }
 static Dictionary<string,string> ExternalHashes(string root) {
  return new[]{SharedLoader.Main,SharedLoader.Root+"enabled.txt",SharedLoader.Root+"loadorder.txt","Game/Binaries/Win64/UE4SS/Mods/falken-us4ss/enabled.txt","Game/Binaries/Win64/UE4SS/Mods/falken-us4ss/Scripts/main.lua","Game/Binaries/Win64/UE4SS/UE4SS.dll","Game/Binaries/Win64/dwmapi.dll","Game/Binaries/Win64/UE4SS/UE4SS-settings.ini"}.ToDictionary(x=>x,x=>Hash(root,x));
 }
 static bool Preserved(string root,Dictionary<string,string> files) {return files.All(x=>Has(root,x.Key)&&Hash(root,x.Key)==x.Value);}
 static Dictionary<string,string> Snapshot(string root) {return Directory.GetFiles(root,"*",SearchOption.AllDirectories).ToDictionary(x=>x.Substring(root.Length+1),x=>Core.HashFile(x));}
 static void RejectedWithoutChanges(string root,string name) {
  var before=Snapshot(root);bool rejected=false;try{Install(root);}catch{rejected=true;}
  Check(rejected,name+" refused");var after=Snapshot(root);Check(before.Count==after.Count&&before.All(x=>after.ContainsKey(x.Key)&&after[x.Key]==x.Value),name+" preserves exact files");
 }
 static int Main(string[] args) {
  try{Console.WriteLine("START: inert installer fixtures");return Run(args);}
  catch(Exception error){Console.WriteLine("FAIL type: "+error.GetType().FullName);Console.WriteLine("FAIL message: "+error.Message);return 1;}
 }
 static int Run(string[] args) {
  destination=Path.GetFullPath(args[0]);bin=Path.GetFullPath(args[1]);payload=Path.GetFullPath(args[2]);
  // Exercise the actual installer/provider transactions with inert byte fixtures.
  // Current-stock decoding is checked independently by the real generator suite.
  CampaignSubtitles.TestFingerprint=(folder,patch)=>"fixture-current";
  CampaignSubtitles.TestBuild=(folder,patch)=>new CampaignSubtitles.Result{Pak=System.Text.Encoding.UTF8.GetBytes("inert generated current-stock dialogue overlay"),Fingerprint="fixture-current",Status="Fixture current-stock dialogue",Applied=1,Changed=1,Skipped=0};
  string root=Fake("external_first");External(root,true);var external=ExternalHashes(root);Install(root);
  var state=Core.ReadState(root);
  Check(state.campaignProvider==SharedLoader.Provider&&state.sharedRuntime,"recognized external loader supplies campaign provider");
  Check(Has(root,SharedLoader.CampaignPak)&&!Has(root,Core.CampaignLoader),"one constructor owner; campaign PAK uses loader folder");
  Check(state.files.Any(x=>x.path==Core.CampaignPatch&&!x.mutable)&&Has(root,Core.CampaignPatch),"owned dialogue dictionary is installed and tracked as immutable");
  Check(state.campaignFingerprint=="fixture-current"&&state.campaignStatus=="Fixture current-stock dialogue","generated current-stock fingerprint and status are retained");
  Check(File.ReadAllText(Core.Safe(root,SharedLoader.CampaignPak))=="inert generated current-stock dialogue overlay","shared provider receives newly generated bytes instead of a static PAK payload");
  Check(!state.files.Any(x=>x.path=="Game/Binaries/Win64/dwmapi.dll"||x.path=="Game/Binaries/Win64/UE4SS/UE4SS.dll"),"shared runtime is not claimed by this pack");
  Check(Preserved(root,external),"all external files and order preserved by install");
  Text(root,Core.Mod+"config.ini","[control]\r\nsensitivity=0.071\r\n");string config=Hash(root,Core.Mod+"config.ini");
  state.version="2.3";state.build=2026101902;Core.Text(Core.Safe(root,Core.Folder+"/installed.json"),Core.Json.Serialize(state));Install(root);state=Core.ReadState(root);
  Check(state.previousVersion=="2.3"&&state.previousBuild==2026101902,"updating records previous version/build");
  Check(Hash(root,Core.Mod+"config.ini")==config,"update preserves user control settings");
  Core.Suspend(root,true);
  Check(!Has(root,SharedLoader.CampaignPak)&&!Has(root,Core.Mod+"Scripts/main.lua"),"suspend parks only owned campaign/runtime entry");
  Check(Preserved(root,external),"suspend keeps external runtime and mods enabled files");
  Core.Suspend(root,false);Check(Has(root,SharedLoader.CampaignPak)&&Has(root,Core.Mod+"Scripts/main.lua"),"resume restores owned entries");
  Core.Uninstall(root);Check(Preserved(root,external),"uninstall preserves complete external loader stack");
  Check(!Has(root,SharedLoader.CampaignPak),"uninstall removes only owned campaign PAK");
  root=Fake("pack_first");Install(root);Check(Has(root,Core.CampaignLoader),"legacy standalone fixture starts with own constructor");
  External(root,false);external=ExternalHashes(root);Install(root);state=Core.ReadState(root);
  Check(state.campaignProvider==SharedLoader.Provider&&!Has(root,Core.CampaignLoader),"standalone-to-shared migration removes own hook");
  Check(!Has(root,"Game/Content/Paks/pakchunk0-Windows_999_P.pak")&&Has(root,SharedLoader.CampaignPak),"migration moves approved campaign PAK to shared provider");
  Core.Uninstall(root);Check(Preserved(root,external),"pack-first external-later removal retains needed shared pair");
  root=Fake("manual_own_original");
  using(var stream=File.OpenRead(payload))using(var zip=new System.IO.Compression.ZipArchive(stream))using(var entry=zip.GetEntry("payload/"+Core.CampaignLoader).Open())using(var bytes=new MemoryStream()){entry.CopyTo(bytes);Put(root,Core.CampaignLoader,bytes.ToArray());}
  Install(root);External(root,false);Install(root);
  Check(!Has(root,Core.CampaignLoader),"migration does not restore the same old constructor from original backup");
  root=Fake("disabled_campaign");External(root,true);Text(root,SharedLoader.Root+"loadorder.txt","-KoreanAIRCampaign\r\n+Falken_addon\r\n");RejectedWithoutChanges(root,"explicitly disabled shared campaign");
  root=Fake("unknown_loader");External(root,true);Text(root,SharedLoader.Main,"unknown replacement DLL fixture");RejectedWithoutChanges(root,"unknown shared loader");
  root=Fake("foreign_constructor");External(root,true);Text(root,Core.CampaignLoader,"foreign constructor fixture");RejectedWithoutChanges(root,"foreign constructor owner");
  root=Fake("foreign_original_backup");Install(root);state=Core.ReadState(root);
  var constructor=state.files.Single(x=>x.path==Core.CampaignLoader);constructor.original="original/foreign-constructor.bin";
  Put(state.backup,constructor.original,System.Text.Encoding.UTF8.GetBytes("foreign original constructor fixture"));
  Core.Text(Core.Safe(root,Core.Folder+"/installed.json"),Core.Json.Serialize(state));External(root,false);RejectedWithoutChanges(root,"foreign constructor backup during migration");
  root=Fake("provider_removed");External(root,true);Install(root);state=Core.ReadState(root);File.Delete(Core.Safe(root,SharedLoader.Main));
  bool launchRejected=false;try{typeof(Core).GetMethod("ValidateLaunchFiles",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{root,state});}catch(TargetInvocationException){launchRejected=true;}
  Check(launchRejected,"launch verification rejects a removed shared provider without starting a process");
  root=Fake("generation_failure");External(root,true);external=ExternalHashes(root);Install(root);
  CampaignSubtitles.TestFingerprint=(folder,patch)=>"changed-fixture-stock";
  CampaignSubtitles.TestBuild=(folder,patch)=>{throw new InvalidDataException("Fixture stock verification failed.");};
  Core.RefreshCampaignSubtitles(root);state=Core.ReadState(root);
  Check(!Has(root,SharedLoader.CampaignPak)&&state.campaignFingerprint==null&&state.campaignStatus.Contains("Original subtitles retained")&&Preserved(root,external),"failed current-stock verification removes stale owned overlay while preserving external provider files");
  Console.WriteLine("Checks="+checks);return 0;
 }
}
