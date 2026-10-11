using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Drawing;
using System.Windows.Forms;
using KoreanAIR;

// Synthetic files only: no game process is launched and no real game path is used.
class LoaderCompatibilityAudit {
 static readonly List<object> checks=new List<object>();
 static string destination;
 static readonly byte[] current=System.Text.Encoding.UTF8.GetBytes("current campaign fixture");
 static readonly byte[] legacy=System.Text.Encoding.UTF8.GetBytes("legacy campaign fixture");
 static readonly byte[] foreign=new byte[]{77,90,0,255,70,79,82,69,73,71,78};
 static void Check(string name,bool value){checks.Add(new{name=name,passed=value});if(!value)throw new Exception(name);}
 static Stream Payload(){return Assembly.GetExecutingAssembly().GetManifestResourceStream("Payload.zip");}
 static void Install(string root,bool cp,bool mouse,bool display){using(var payload=Payload())Core.Install(root,cp,mouse,display,payload,Assembly.GetExecutingAssembly().Location);}
 static LoaderCompatibility Inspect(string root){using(var payload=Payload())return Core.InspectCampaignLoader(root,payload);}
 static void Put(string root,string path,byte[] value){string target=Core.Safe(root,path);Directory.CreateDirectory(Path.GetDirectoryName(target));File.WriteAllBytes(target,value);}
 static string Fake(string name){
  string root=Path.Combine(destination,name);Directory.CreateDirectory(root);byte[] exe=new byte[1024];
  Action<int,byte[]> put=(offset,value)=>Buffer.BlockCopy(value,0,exe,offset,value.Length);
  put(0,BitConverter.GetBytes((ushort)0x5A4D));put(0x3C,BitConverter.GetBytes(128));put(128,BitConverter.GetBytes(0x4550));put(132,BitConverter.GetBytes((ushort)0x8664));put(136,BitConverter.GetBytes(0x6AA0E27D));put(208,BitConverter.GetBytes(0x2195A000));
  Put(root,"Game/Binaries/Win64/AceCombat8.exe",exe);Put(root,"start_protected_game.exe",exe);
  Put(root,"EasyAntiCheat/Settings.json",System.Text.Encoding.UTF8.GetBytes("{\"executable\":\"Game/Binaries/Win64/AceCombat8.exe\"}"));return root;
 }
 static Dictionary<string,byte[]> External(string root){
  var files=new Dictionary<string,byte[]>{
   {Core.CampaignLoader,foreign},
   {"Game/Binaries/Win64/WeaponPack/config.ini",System.Text.Encoding.UTF8.GetBytes("[weapon]\r\nfixture=18.5\r\n")},
   {"Game/Binaries/Win64/WeaponPack/Resource/weapon.bin",Enumerable.Range(0,256).Select(x=>(byte)x).ToArray()},
   {"Game/Binaries/Win64/WeaponPack.log",System.Text.Encoding.UTF8.GetBytes("fixture log\r\n")},
   {"Game/Content/Paks/WeaponPack_v18.5_P.pak",System.Text.Encoding.UTF8.GetBytes("unrelated fixture pak")}
  };foreach(var file in files)Put(root,file.Key,file.Value);return files;
 }
 static Dictionary<string,byte[]> Snapshot(string root){return Directory.GetFiles(root,"*",SearchOption.AllDirectories).ToDictionary(p=>p.Substring(root.Length+1),File.ReadAllBytes,StringComparer.OrdinalIgnoreCase);}
 static bool Same(Dictionary<string,byte[]> a,Dictionary<string,byte[]> b){return a.Count==b.Count&&a.All(f=>b.ContainsKey(f.Key)&&f.Value.SequenceEqual(b[f.Key]));}
 static bool Preserved(string root,Dictionary<string,byte[]> originals){return originals.All(f=>File.Exists(Core.Safe(root,f.Key))&&File.ReadAllBytes(Core.Safe(root,f.Key)).SequenceEqual(f.Value));}
 static Control Find(Control parent,string name){if(parent.Name==name)return parent;foreach(Control child in parent.Controls){var result=Find(child,name);if(result!=null)return result;}return null;}
 static void Await(Setup setup,string button){((Button)Find(setup,button)).PerformClick();var work=setup.PendingWork;DateTime deadline=DateTime.UtcNow.AddSeconds(30);while(work!=null&&!work.IsCompleted&&DateTime.UtcNow<deadline){Application.DoEvents();System.Threading.Thread.Sleep(10);}Check(button+"_finished",work!=null&&work.IsCompleted);work.GetAwaiter().GetResult();Application.DoEvents();}
 static void Language(Setup setup,string language){((UiLanguage)typeof(Setup).GetField("ui",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(setup)).Change(language,false);}
 static void CoreCases(){
  string root=Fake("foreign");var originals=External(root);var before=Snapshot(root);
  Check("foreign_detected",Inspect(root).ForeignLoader&&Inspect(root).Kind=="foreign");
  try{Install(root,true,true,true);Check("foreign_campaign_rejected",false);}catch(Exception e){Check("foreign_campaign_rejected",e.Message.Contains("dinput8.dll")&&e.Message.Contains("OFF"));}
  Check("foreign_preflight_exact_snapshot",Same(before,Snapshot(root)));
  foreach(var modules in new[]{new[]{true,false},new[]{false,true},new[]{true,true}}){
   string id=(modules[0]?"mouse":"")+(modules[1]?"display":"");Install(root,false,modules[0],modules[1]);
   Check(id+"_runtime_success",!Core.ReadState(root).campaign&&Core.ReadState(root).mouse==modules[0]&&Core.ReadState(root).display==modules[1]);
   Check(id+"_loader_not_owned",Core.ReadState(root).files.All(f=>f.path!=Core.CampaignLoader)&&Core.InspectCampaignLoader(root).ForeignLoader);
   Check(id+"_subtitles_available",File.ReadAllText(Core.Config(root,"pack.ini")).Contains("subtitles=1"));
   Check(id+"_originals_installed",Preserved(root,originals));
   Core.WriteIni(Core.Config(root,"config.ini"),"control",new Dictionary<string,string>{{"sensitivity","0.04"}});
   Core.WriteIni(Core.Config(root,"display.ini"),"display",new Dictionary<string,string>{{"span","7680"}});
   Check(id+"_originals_after_settings",Preserved(root,originals));
   Core.Suspend(root,true);Check(id+"_originals_suspended",Preserved(root,originals));
   Core.Suspend(root,false);Check(id+"_originals_resumed",Preserved(root,originals));
   Core.Uninstall(root);Check(id+"_exact_originals_after_removal",Same(before,Snapshot(root)));
  }
  foreach(string kind in new[]{"current","legacy"}){
   root=Fake(kind);Put(root,Core.CampaignLoader,kind=="current"?current:legacy);
   Check(kind+"_recognized",!Inspect(root).ForeignLoader&&Inspect(root).Kind==kind);Install(root,true,false,false);
   Check(kind+"_upgrade_success",Core.ReadState(root).campaign&&File.ReadAllBytes(Core.Safe(root,Core.CampaignLoader)).SequenceEqual(current));Core.Uninstall(root);
  }
  root=Fake("old_owned");Install(root,true,true,true);var state=Core.ReadState(root);Put(root,Core.CampaignLoader,legacy);state.files.Single(f=>f.path==Core.CampaignLoader).hash=Core.Hash(legacy);Core.Text(Core.Safe(root,Core.Folder+"/installed.json"),Core.Json.Serialize(state));
  Check("old_owned_proxy_recognized",Inspect(root).Kind=="owned");Install(root,true,true,true);Check("old_owned_proxy_upgraded",File.ReadAllBytes(Core.Safe(root,Core.CampaignLoader)).SequenceEqual(current));
  Put(root,Core.CampaignLoader,foreign);before=Snapshot(root);Check("owned_replaced_is_foreign",Inspect(root).ForeignLoader);
  try{Install(root,true,true,true);Check("owned_foreign_campaign_rejected",false);}catch(Exception e){Check("owned_foreign_campaign_rejected",e.Message.Contains("dinput8.dll"));}
  Check("owned_foreign_preflight_exact_snapshot",Same(before,Snapshot(root)));Install(root,false,true,true);
  Check("owned_foreign_replacement_detached",Core.ReadState(root).files.All(f=>f.path!=Core.CampaignLoader));Core.Suspend(root,true);Core.Suspend(root,false);Core.Uninstall(root);
  Check("owned_foreign_replacement_preserved",File.ReadAllBytes(Core.Safe(root,Core.CampaignLoader)).SequenceEqual(foreign));
 }
 static void UiCases(){
  string root=Fake("ui_foreign");var originals=External(root);var before=Snapshot(root);
  using(var setup=new Setup(root)){
   setup.StartPosition=FormStartPosition.Manual;setup.Location=new Point(-32000,-32000);setup.ShowInTaskbar=false;setup.Show();Application.DoEvents();
   var dialogs=new List<string>();setup.Dialog=(text,icon)=>dialogs.Add(text);var campaign=(CheckBox)Find(setup,"campaign");var mouse=(CheckBox)Find(setup,"mouse");var display=(CheckBox)Find(setup,"display");
   foreach(string language in new[]{"en","ko"}){
    Language(setup,language);campaign.Checked=true;mouse.Checked=true;display.Checked=true;string warning=null;
    setup.ConfirmCoexistence=text=>{warning=text;Check(language+"_warning_before_any_mutation",Same(before,Snapshot(root)));return DialogResult.No;};Await(setup,"installPack");
    Check(language+"_concrete_warning",warning!=null&&warning.Contains("Game/Binaries/Win64/dinput8.dll")&&warning.Contains(language=="ko"?"검증되지":"unverified"));
    Check(language+"_foreign_notice",Find(setup,"campaignLoaderCompatibility").Visible&&Find(setup,"campaignLoaderCompatibility").Text.Contains("dinput8.dll"));
    Check(language+"_cancel_exact_snapshot",Same(before,Snapshot(root))&&campaign.Checked);
   }
   setup.ConfirmCoexistence=text=>DialogResult.Yes;Await(setup,"installPack");
   if(Core.ReadState(root)==null)throw new Exception("UI installation did not complete: "+Find(setup,"installStatus").Text+" / "+String.Join(" | ",dialogs));
   Check("ui_continue_campaign_visibly_off",!campaign.Checked&&!Core.ReadState(root).campaign&&mouse.Checked&&display.Checked);
   Check("ui_continue_preserves_all_external_bytes",Preserved(root,originals));
   Check("ui_continue_no_error",dialogs.Count==1&&!dialogs[0].Contains("dinput8.dll"));
   Await(setup,"uninstallPack");Check("ui_remove_exact_original_snapshot",Same(before,Snapshot(root)));
  }
  File.Delete(Core.Safe(root,Core.CampaignLoader));Check("external_removed_preflight_allows_campaign",!Inspect(root).ForeignLoader);Install(root,true,true,true);
  Check("campaign_can_be_added_later",Core.ReadState(root).campaign&&Inspect(root).Kind=="owned");Core.Uninstall(root);
  Check("later_campaign_preserves_external_resources",Preserved(root,originals.Where(f=>f.Key!=Core.CampaignLoader).ToDictionary(f=>f.Key,f=>f.Value)));
 }
 [STAThread]static int Main(string[] args){
  destination=Path.GetFullPath(args[0]);Directory.CreateDirectory(destination);bool passed=false;string error=null;
  try{Application.EnableVisualStyles();CoreCases();UiCases();passed=true;}catch(Exception ex){error=ex.ToString();}
  File.WriteAllText(Path.Combine(destination,"results.json"),Core.Json.Serialize(new{passed=passed,checks=checks.Count,error=error,results=checks}));
  Console.WriteLine("Checks: "+checks.Count+"; passed: "+passed);if(error!=null)Console.WriteLine(error);return passed?0:1;
 }
}
