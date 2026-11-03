using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using KoreanAIR;

// Reflection entry point only. Setup.Main and Core.Install are production code;
// all game headers, DLL/PAK bytes and subtitle output are inert synthetic data.
static class InstalledSetupCacheAudit {
 static readonly List<object> checks=new List<object>();
 static void Check(string name,bool result){checks.Add(new{name=name,passed=result});if(!result)throw new Exception(name);}
 static byte[] B(string text){return Encoding.UTF8.GetBytes(text);}
 static void Put(string root,string relative,byte[] bytes){string path=Core.Safe(root,relative);Directory.CreateDirectory(Path.GetDirectoryName(path));File.WriteAllBytes(path,bytes);}
 static void Text(string root,string relative,string text){Put(root,relative,B(text));}
 static int SetupInstall(string root,bool cp){
  var main=typeof(Setup).GetMethod("Main",BindingFlags.NonPublic|BindingFlags.Static);
  try{return (int)main.Invoke(null,new object[]{new[]{"--install",root,cp?"1":"0","1","1"}});}
  catch(TargetInvocationException error){throw error.InnerException;}
 }
 static string SetupPath(string root){return Core.Safe(root,Core.Folder+"/Setup.exe");}
 static string CachePath(){var descriptor=ReleasePayload.ReadDescriptor(typeof(Core).Assembly);return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),Core.Folder,"Payloads",descriptor.sha256,"Payload.zip");}
 static void FakeGame(string root){
  var bytes=new byte[1024];Action<int,byte[]> put=(offset,value)=>Buffer.BlockCopy(value,0,bytes,offset,value.Length);
  put(0,BitConverter.GetBytes((ushort)0x5a4d));put(0x3c,BitConverter.GetBytes(128));put(128,BitConverter.GetBytes(0x4550));put(132,BitConverter.GetBytes((ushort)0x8664));put(152,BitConverter.GetBytes((ushort)0x20b));put(208,BitConverter.GetBytes(0x1000));
  Put(root,"Game/Binaries/Win64/AceCombat8.exe",bytes);Put(root,"start_protected_game.exe",bytes);
  Text(root,"EasyAntiCheat/Settings.json","{\"executable\":\"Game/Binaries/Win64/AceCombat8.exe\"}");
 }
 static Dictionary<string,string> Settings(string root){return new[]{"config.ini","display.ini","subtitle.ini"}.ToDictionary(x=>x,x=>Core.HashFile(Core.Safe(root,Core.Mod+x)));}
 static void Prepare(string root){
  FakeGame(root);
  var existing=new State{root=root,build=Core.ReleaseBuild,campaign=false,mouse=true,display=true,backup=Path.Combine(root,"backups")};
  Text(root,Core.Folder+"/installed.json",Core.Json.Serialize(existing));
  Text(root,Core.Mod+"config.ini","[control]\r\nsensitivity=0.037\r\nownerBinding=preserve\r\n");
  Text(root,Core.Mod+"display.ini","[display]\r\nfov=107\r\nownerSpan=preserve\r\n");
  Text(root,Core.Mod+"subtitle.ini","[subtitles]\r\nposition=bottom\r\nsize=29\r\n");
  Text(root,"Game/Binaries/Win64/UE4SS/Mods/mods.txt","OwnerOtherMod : 1\r\n");
  Text(root,"Game/Binaries/Win64/UE4SS/Mods/OwnerOtherMod/keep.txt","unrelated mod must remain");
  var settings=Settings(root);
  Check("production_Setup_CLI_initial_install_succeeds",SetupInstall(root,false)==0);
  var state=Core.ReadState(root);
  Check("initial_install_has_CP_off_mouse_and_display_on",!state.campaign&&state.mouse&&state.display);
  Check("initial_install_has_no_campaign_dictionary",!File.Exists(Core.Safe(root,Core.CampaignPatch)));
  Check("real_provider_warms_exact_SHA_cache",File.Exists(CachePath())&&Core.HashFile(CachePath())==ReleasePayload.ReadDescriptor(typeof(Core).Assembly).sha256);
  Check("production_Core_installs_identical_Setup_bytes",Core.HashFile(SetupPath(root))==Core.HashFile(typeof(Core).Assembly.Location));
  Check("installed_Setup_has_no_sibling_Payload_zip",!File.Exists(Path.Combine(Path.GetDirectoryName(SetupPath(root)),"Payload.zip")));
  Check("initial_install_preserves_user_settings",settings.All(x=>Settings(root)[x.Key]==x.Value));
  Check("initial_install_never_requests_network",UpdateCore.NetworkAttempts==0);
 }
 static void Enable(string root){
  string self=SetupPath(root);
  Check("audit_runs_from_installed_Setup_location",String.Equals(Path.GetFullPath(typeof(Core).Assembly.Location),Path.GetFullPath(self),StringComparison.OrdinalIgnoreCase));
  Check("installed_Setup_has_no_sibling_Payload_zip",!File.Exists(Path.Combine(Path.GetDirectoryName(self),"Payload.zip")));
  var settings=Settings(root);string unrelated=Core.HashFile(Core.Safe(root,"Game/Binaries/Win64/UE4SS/Mods/OwnerOtherMod/keep.txt"));
  string before=Core.HashFile(self);DateTime timestamp=File.GetLastWriteTimeUtc(self);int selfCommits=0;
  Core.AtomicBeforeCommit=(path,temporary)=>{if(String.Equals(Path.GetFullPath(path),Path.GetFullPath(self),StringComparison.OrdinalIgnoreCase)){selfCommits++;throw new Exception("Installed Setup must not replace itself.");}};
  // This share mode blocks writes and deletion just as a running executable
  // does. A changed-self replace would fail; identical bytes must be skipped.
  using(var lockedSelf=new FileStream(self,FileMode.Open,FileAccess.Read,FileShare.Read)){
   Check("installed_Setup_CLI_enables_CP_from_cache_offline",SetupInstall(root,true)==0);
  }
  var state=Core.ReadState(root);
  Check("real_Core_records_CP_on_and_preserves_other_module_selection",state.campaign&&state.mouse&&state.display);
  Check("real_Core_installs_campaign_loader_and_dictionary",File.Exists(Core.Safe(root,Core.CampaignLoader))&&File.Exists(Core.Safe(root,Core.CampaignPatch)));
  Check("real_Core_records_synthetic_current_stock_overlay",File.ReadAllText(Core.Safe(root,Core.CampaignPak))=="inert generated current-stock dialogue archive"&&state.campaignFingerprint=="synthetic-current-stock");
  Check("locked_identical_installed_Setup_never_reaches_Atomic_replace",selfCommits==0);
  Check("installed_Setup_bytes_and_write_time_unchanged",Core.HashFile(self)==before&&File.GetLastWriteTimeUtc(self)==timestamp);
  Check("CP_enable_preserves_all_user_settings",settings.All(x=>Settings(root)[x.Key]==x.Value));
  Check("CP_enable_preserves_unrelated_mod",Core.HashFile(Core.Safe(root,"Game/Binaries/Win64/UE4SS/Mods/OwnerOtherMod/keep.txt"))==unrelated&&File.ReadAllText(Core.Safe(root,"Game/Binaries/Win64/UE4SS/Mods/mods.txt")).Contains("OwnerOtherMod : 1"));
  Check("default_allowDownload_true_cache_hit_never_requests_network",UpdateCore.NetworkAttempts==0);
  Check("provider_uses_same_verified_SHA_cache",Core.HashFile(CachePath())==ReleasePayload.ReadDescriptor(typeof(Core).Assembly).sha256);
  string cached=CachePath(),held=cached+".fixture-held";
  string stateHash=Core.HashFile(Core.Safe(root,Core.Folder+"/installed.json"));
  File.Move(cached,held);
  try{
   bool missing=false;
   try{using(var stream=ReleasePayload.OpenPayload(typeof(Core).Assembly,null,System.Threading.CancellationToken.None,false)){} }
   catch(FileNotFoundException){missing=true;}
   Check("missing_cache_and_sibling_fail_promptly_offline",missing);
   Check("missing_cache_refusal_preserves_installed_state",Core.HashFile(Core.Safe(root,Core.Folder+"/installed.json"))==stateHash&&Core.HashFile(self)==before);
   Check("missing_cache_offline_refusal_never_requests_network",UpdateCore.NetworkAttempts==0);
  }finally{File.Move(held,cached);}
 }
 static int Main(string[] args){
  bool passed=false;string error=null;
  try{
   if(args.Length!=3)throw new ArgumentException("Expected phase, isolated game fixture and report path.");
   string root=Path.GetFullPath(args[1]);
   Core.FrameGenerationTestDirectory=Path.Combine(root,"isolated-user-settings");
   if(args[0]=="prepare")Prepare(root);else if(args[0]=="enable")Enable(root);else throw new ArgumentException("Unknown phase.");
   passed=true;
  }catch(Exception ex){error=ex.ToString();}
  File.WriteAllText(args[2],new JavaScriptSerializer().Serialize(new{passed=passed,checks=checks,error=error}));
  Console.WriteLine("Installed Setup cache phase="+args[0]+" checks="+checks.Count+" passed="+passed+(error==null?"":"\n"+error));return passed?0:1;
 }
}
