using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Drawing;
using System.Windows.Forms;
using System.Collections;
using System.Runtime.ExceptionServices;
using System.Web.Script.Serialization;

// Thin reflection adapter: this executable contains no installer/updater source
// or embedded payload. Every operation below invokes the actual Setup assembly.
static class Real {
 internal static Assembly Assembly;
 static Type core;
 internal static void Load(string path){Assembly=System.Reflection.Assembly.LoadFrom(Path.GetFullPath(path));core=Assembly.GetType("KoreanAIR.Core",true);}
 static object Invoke(string name,Type[] signature,params object[] args){
  var method=core.GetMethod(name,BindingFlags.Public|BindingFlags.Static,null,signature,null);
  if(method==null)throw new MissingMethodException(core.FullName,name);
  try{return method.Invoke(null,args);}catch(TargetInvocationException e){ExceptionDispatchInfo.Capture(e.InnerException??e).Throw();throw;}
 }
 internal static string CampaignLoader{get{return (string)core.GetField("CampaignLoader").GetValue(null);}}
 internal static string Folder{get{return (string)core.GetField("Folder").GetValue(null);}}
 internal static JavaScriptSerializer Json{get{return (JavaScriptSerializer)core.GetField("Json").GetValue(null);}}
 internal static string Safe(string root,string relative){return (string)Invoke("Safe",new[]{typeof(string),typeof(string)},root,relative);}
 internal static string Config(string root,string file){return (string)Invoke("Config",new[]{typeof(string),typeof(string)},root,file);}
 internal static string Hash(byte[] value){return (string)Invoke("Hash",new[]{typeof(byte[])},value);}
 internal static dynamic ReadState(string root){return Invoke("ReadState",new[]{typeof(string)},root);}
 internal static IEnumerable<dynamic> Files(object state){return ((IEnumerable)state.GetType().GetField("files").GetValue(state)).Cast<dynamic>();}
 internal static dynamic InspectCampaignLoader(string root){return Invoke("InspectCampaignLoader",new[]{typeof(string)},root);}
 internal static dynamic InspectCampaignLoader(string root,Stream payload){return Invoke("InspectCampaignLoader",new[]{typeof(string),typeof(Stream)},root,payload);}
 internal static void Install(string root,bool cp,bool mouse,bool display,Stream payload,string installer){Invoke("Install",new[]{typeof(string),typeof(bool),typeof(bool),typeof(bool),typeof(Stream),typeof(string)},root,cp,mouse,display,payload,installer);}
 internal static void Text(string path,string text){Invoke("Text",new[]{typeof(string),typeof(string)},path,text);}
 internal static void WriteIni(string path,string section,Dictionary<string,string> values){Invoke("WriteIni",new[]{typeof(string),typeof(string),typeof(Dictionary<string,string>)},path,section,values);}
 internal static void Suspend(string root,bool off){Invoke("Suspend",new[]{typeof(string),typeof(bool)},root,off);}
 internal static void Uninstall(string root){Invoke("Uninstall",new[]{typeof(string)},root);}
}

// Synthetic files only: no game process is launched and no real game path is used.
class LoaderCompatibilityAudit {
 static readonly List<object> checks=new List<object>();
 static string destination;
 static string payloadPath;
 static readonly byte[] current=System.Text.Encoding.UTF8.GetBytes("current campaign fixture");
 static readonly byte[] legacy=System.Text.Encoding.UTF8.GetBytes("legacy campaign fixture");
 static readonly byte[] foreign=new byte[]{77,90,0,255,70,79,82,69,73,71,78};
 static void Check(string name,bool value){checks.Add(new{name=name,passed=value});if(!value)throw new Exception(name);}
 static Stream Payload(){return File.OpenRead(payloadPath);}
 static void Install(string root,bool cp,bool mouse,bool display){using(var payload=Payload())Real.Install(root,cp,mouse,display,payload,Real.Assembly.Location);}
 static dynamic Inspect(string root){using(var payload=Payload())return Real.InspectCampaignLoader(root,payload);}
 static void Put(string root,string path,byte[] value){string target=Real.Safe(root,path);Directory.CreateDirectory(Path.GetDirectoryName(target));File.WriteAllBytes(target,value);}
 static string Fake(string name){
  string root=Path.Combine(destination,name);Directory.CreateDirectory(root);byte[] exe=new byte[1024];
  Action<int,byte[]> put=(offset,value)=>Buffer.BlockCopy(value,0,exe,offset,value.Length);
  put(0,BitConverter.GetBytes((ushort)0x5A4D));put(0x3C,BitConverter.GetBytes(128));put(128,BitConverter.GetBytes(0x4550));put(132,BitConverter.GetBytes((ushort)0x8664));put(136,BitConverter.GetBytes(0x6AA0E27D));put(208,BitConverter.GetBytes(0x2195A000));
  Put(root,"Game/Binaries/Win64/AceCombat8.exe",exe);Put(root,"start_protected_game.exe",exe);
  Put(root,"EasyAntiCheat/Settings.json",System.Text.Encoding.UTF8.GetBytes("{\"executable\":\"Game/Binaries/Win64/AceCombat8.exe\"}"));return root;
 }
 static Dictionary<string,byte[]> External(string root){
  var files=new Dictionary<string,byte[]>{
   {Real.CampaignLoader,foreign},
   {"Game/Binaries/Win64/WeaponPack/config.ini",System.Text.Encoding.UTF8.GetBytes("[weapon]\r\nfixture=18.5\r\n")},
   {"Game/Binaries/Win64/WeaponPack/Resource/weapon.bin",Enumerable.Range(0,256).Select(x=>(byte)x).ToArray()},
   {"Game/Binaries/Win64/WeaponPack.log",System.Text.Encoding.UTF8.GetBytes("fixture log\r\n")},
   {"Game/Content/Paks/WeaponPack_v18.5_P.pak",System.Text.Encoding.UTF8.GetBytes("unrelated fixture pak")}
  };foreach(var file in files)Put(root,file.Key,file.Value);return files;
 }
 static Dictionary<string,byte[]> Snapshot(string root){return Directory.GetFiles(root,"*",SearchOption.AllDirectories).ToDictionary(p=>p.Substring(root.Length+1),File.ReadAllBytes,StringComparer.OrdinalIgnoreCase);}
 static bool Same(Dictionary<string,byte[]> a,Dictionary<string,byte[]> b){return a.Count==b.Count&&a.All(f=>b.ContainsKey(f.Key)&&f.Value.SequenceEqual(b[f.Key]));}
 static bool Preserved(string root,Dictionary<string,byte[]> originals){return originals.All(f=>File.Exists(Real.Safe(root,f.Key))&&File.ReadAllBytes(Real.Safe(root,f.Key)).SequenceEqual(f.Value));}
 static Control Find(Control parent,string name){if(parent.Name==name)return parent;foreach(Control child in parent.Controls){var result=Find(child,name);if(result!=null)return result;}return null;}
 static FieldInfo SetupField(Form setup,string name){return setup.GetType().GetField(name,BindingFlags.Instance|BindingFlags.NonPublic);}
 static void Await(Form setup,string button){((Button)Find(setup,button)).PerformClick();var work=(Task)SetupField(setup,"PendingWork").GetValue(setup);DateTime deadline=DateTime.UtcNow.AddSeconds(30);while(work!=null&&!work.IsCompleted&&DateTime.UtcNow<deadline){Application.DoEvents();System.Threading.Thread.Sleep(10);}Check(button+"_finished",work!=null&&work.IsCompleted);work.GetAwaiter().GetResult();Application.DoEvents();}
 static void Language(Form setup,string language){var ui=SetupField(setup,"ui").GetValue(setup);ui.GetType().GetMethod("Change").Invoke(ui,new object[]{language,false});}
 static void CoreCases(){
  string root=Fake("foreign");var originals=External(root);var before=Snapshot(root);
  Check("foreign_detected",Inspect(root).ForeignLoader&&Inspect(root).Kind=="foreign");
  try{Install(root,true,true,true);Check("foreign_campaign_rejected",false);}catch(Exception e){Check("foreign_campaign_rejected",e.Message.Contains("dinput8.dll")&&e.Message.Contains("OFF"));}
  Check("foreign_preflight_exact_snapshot",Same(before,Snapshot(root)));
  foreach(var modules in new[]{new[]{true,false},new[]{false,true},new[]{true,true}}){
   string id=(modules[0]?"mouse":"")+(modules[1]?"display":"");Install(root,false,modules[0],modules[1]);
   Check(id+"_runtime_success",!Real.ReadState(root).campaign&&Real.ReadState(root).mouse==modules[0]&&Real.ReadState(root).display==modules[1]);
   Check(id+"_loader_not_owned",Real.Files((object)Real.ReadState(root)).All(f=>f.path!=Real.CampaignLoader)&&Real.InspectCampaignLoader(root).ForeignLoader);
   Check(id+"_subtitles_available",File.ReadAllText(Real.Config(root,"pack.ini")).Contains("subtitles=1"));
   Check(id+"_originals_installed",Preserved(root,originals));
   Real.WriteIni(Real.Config(root,"config.ini"),"control",new Dictionary<string,string>{{"sensitivity","0.04"}});
   Real.WriteIni(Real.Config(root,"display.ini"),"display",new Dictionary<string,string>{{"span","7680"}});
   Check(id+"_originals_after_settings",Preserved(root,originals));
   Real.Suspend(root,true);Check(id+"_originals_suspended",Preserved(root,originals));
   Real.Suspend(root,false);Check(id+"_originals_resumed",Preserved(root,originals));
   Real.Uninstall(root);Check(id+"_exact_originals_after_removal",Same(before,Snapshot(root)));
  }
  foreach(string kind in new[]{"current","legacy"}){
   root=Fake(kind);Put(root,Real.CampaignLoader,kind=="current"?current:legacy);
   Check(kind+"_recognized",!Inspect(root).ForeignLoader&&Inspect(root).Kind==kind);Install(root,true,false,false);
   Check(kind+"_upgrade_success",Real.ReadState(root).campaign&&File.ReadAllBytes(Real.Safe(root,Real.CampaignLoader)).SequenceEqual(current));Real.Uninstall(root);
  }
  root=Fake("old_owned");Install(root,true,true,true);var state=Real.ReadState(root);Put(root,Real.CampaignLoader,legacy);Real.Files((object)state).Single(f=>f.path==Real.CampaignLoader).hash=Real.Hash(legacy);Real.Text(Real.Safe(root,Real.Folder+"/installed.json"),Real.Json.Serialize(state));
  Check("old_owned_proxy_recognized",Inspect(root).Kind=="owned");Install(root,true,true,true);Check("old_owned_proxy_upgraded",File.ReadAllBytes(Real.Safe(root,Real.CampaignLoader)).SequenceEqual(current));
  Put(root,Real.CampaignLoader,foreign);before=Snapshot(root);Check("owned_replaced_is_foreign",Inspect(root).ForeignLoader);
  try{Install(root,true,true,true);Check("owned_foreign_campaign_rejected",false);}catch(Exception e){Check("owned_foreign_campaign_rejected",e.Message.Contains("dinput8.dll"));}
  Check("owned_foreign_preflight_exact_snapshot",Same(before,Snapshot(root)));Install(root,false,true,true);
  Check("owned_foreign_replacement_detached",Real.Files((object)Real.ReadState(root)).All(f=>f.path!=Real.CampaignLoader));Real.Suspend(root,true);Real.Suspend(root,false);Real.Uninstall(root);
  Check("owned_foreign_replacement_preserved",File.ReadAllBytes(Real.Safe(root,Real.CampaignLoader)).SequenceEqual(foreign));
 }
 static void UiCases(){
  string root=Fake("ui_foreign");var originals=External(root);var before=Snapshot(root);
  // The genuine UI opens its own genuine embedded payload. Only Core's direct
  // fixture cases use fakePayload.zip; no method or resource is substituted.
  using(var setup=(Form)Activator.CreateInstance(Real.Assembly.GetType("Setup",true),new object[]{root})){
   setup.StartPosition=FormStartPosition.Manual;setup.Location=new Point(-32000,-32000);setup.Opacity=0;setup.ShowInTaskbar=false;setup.Show();Application.DoEvents();
   var dialogs=new List<string>();SetupField(setup,"Dialog").SetValue(setup,new Action<string,MessageBoxIcon>((text,icon)=>dialogs.Add(text)));var campaign=(CheckBox)Find(setup,"campaign");var mouse=(CheckBox)Find(setup,"mouse");var display=(CheckBox)Find(setup,"display");
   foreach(string language in new[]{"en","ko"}){
    Language(setup,language);campaign.Checked=true;mouse.Checked=true;display.Checked=true;string warning=null;
    SetupField(setup,"ConfirmCoexistence").SetValue(setup,new Func<string,DialogResult>(text=>{warning=text;Check(language+"_warning_before_any_mutation",Same(before,Snapshot(root)));return DialogResult.No;}));Await(setup,"installPack");
    Check(language+"_concrete_warning",warning!=null&&warning.Contains("Game/Binaries/Win64/dinput8.dll")&&warning.Contains(language=="ko"?"검증되지":"unverified"));
    Check(language+"_foreign_notice",Find(setup,"campaignLoaderCompatibility").Visible&&Find(setup,"campaignLoaderCompatibility").Text.Contains("dinput8.dll"));
    Check(language+"_cancel_exact_snapshot",Same(before,Snapshot(root))&&campaign.Checked);
   }
   SetupField(setup,"ConfirmCoexistence").SetValue(setup,new Func<string,DialogResult>(text=>DialogResult.Yes));Await(setup,"installPack");
   if(Real.ReadState(root)==null)throw new Exception("UI installation did not complete: "+Find(setup,"installStatus").Text+" / "+String.Join(" | ",dialogs));
   Check("ui_continue_campaign_visibly_off",!campaign.Checked&&!Real.ReadState(root).campaign&&mouse.Checked&&display.Checked);
   Check("ui_continue_preserves_all_external_bytes",Preserved(root,originals));
   Check("ui_continue_no_error",dialogs.Count==1&&!dialogs[0].Contains("dinput8.dll"));
   Await(setup,"uninstallPack");Check("ui_remove_exact_original_snapshot",Same(before,Snapshot(root)));
  }
  File.Delete(Real.Safe(root,Real.CampaignLoader));Check("external_removed_preflight_allows_campaign",!Inspect(root).ForeignLoader);Install(root,true,true,true);
  Check("campaign_can_be_added_later",Real.ReadState(root).campaign&&Inspect(root).Kind=="owned");Real.Uninstall(root);
  Check("later_campaign_preserves_external_resources",Preserved(root,originals.Where(f=>f.Key!=Real.CampaignLoader).ToDictionary(f=>f.Key,f=>f.Value)));
 }
 [STAThread]static int Main(string[] args){
  destination=Path.GetFullPath(args[0]);Directory.CreateDirectory(destination);bool passed=false;string error=null;
  try{Real.Load(args[1]);payloadPath=Path.GetFullPath(args[2]);Application.EnableVisualStyles();CoreCases();UiCases();passed=true;}catch(Exception ex){error=ex.ToString();}
  File.WriteAllText(Path.Combine(destination,"results.json"),new JavaScriptSerializer().Serialize(new{passed=passed,checks=checks.Count,error=error,results=checks}));
  Console.WriteLine("Checks: "+checks.Count+"; passed: "+passed);if(error!=null)Console.WriteLine(error);return passed?0:1;
 }
}
