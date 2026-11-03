using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Windows.Forms;
using KoreanAIR;

// Compiles the production Setup and Launcher together. Only this test owns Main.
// Forms remain hidden: no update checks, game launch, worker, or native mod runs.
static class SubtitleDefaultsTests {
 static int checks;
 static string destination,payload;
 static void Check(bool result,string name){if(!result)throw new Exception(name);checks++;Console.WriteLine("PASS: "+name);}
 static void Put(string root,string relative,byte[] bytes){string path=Core.Safe(root,relative);Directory.CreateDirectory(Path.GetDirectoryName(path));File.WriteAllBytes(path,bytes);}
 static void Text(string root,string relative,string text){Put(root,relative,Encoding.UTF8.GetBytes(text));}
 static bool Has(string root,string relative){return File.Exists(Core.Safe(root,relative));}
 static T Find<T>(Control owner,string name) where T:Control {
  var found=owner.Controls.Find(name,true);if(found.Length!=1||!(found[0] is T))throw new Exception("Expected one control: "+name);return (T)found[0];
 }
 static void Event(Control control,string method){typeof(Control).GetMethod(method,BindingFlags.Instance|BindingFlags.NonPublic).Invoke(control,new object[]{EventArgs.Empty});}
 static void Switch(Setup form,string root){var path=Find<TextBox>(form,"gamePath");path.Text=root;Event(path,"OnLeave");}
 static void Save(string root,bool campaign){var state=new State{root=root,build=Core.ReleaseBuild,campaign=campaign,mouse=true,backup=Path.Combine(root,"backups")};Text(root,Core.Folder+"/installed.json",Core.Json.Serialize(state));}
 static string Fake(string name){
  string root=Path.Combine(destination,name);var bytes=new byte[1024];
  Action<int,byte[]> put=(offset,value)=>Buffer.BlockCopy(value,0,bytes,offset,value.Length);
  put(0,BitConverter.GetBytes((ushort)0x5a4d));put(0x3c,BitConverter.GetBytes(128));put(128,BitConverter.GetBytes(0x4550));put(132,BitConverter.GetBytes((ushort)0x8664));put(152,BitConverter.GetBytes((ushort)0x20b));put(208,BitConverter.GetBytes(0x1000));
  Put(root,"Game/Binaries/Win64/AceCombat8.exe",bytes);Put(root,"start_protected_game.exe",bytes);
  Text(root,"EasyAntiCheat/Settings.json","{\"executable\":\"Game/Binaries/Win64/AceCombat8.exe\"}");return root;
 }
 static void Install(string root){using(var stream=File.OpenRead(payload))Core.Install(root,false,true,false,stream,"");}
 static void UiChoices(){
  string fresh=Fake("fresh"),otherFresh=Fake("other_fresh"),enabled=Fake("existing_enabled"),disabled=Fake("existing_disabled");Save(enabled,true);Save(disabled,false);
  using(var setup=new Setup(fresh)){
   Check(!Find<CheckBox>(setup,"campaign").Checked,"fresh Setup leaves Korean translation OFF");
   Check(Find<CheckBox>(setup,"mouse").Checked,"fresh Setup retains independent mouse default");
   Switch(setup,enabled);Check(Find<CheckBox>(setup,"campaign").Checked,"Setup restores existing explicit translation ON");
   Switch(setup,otherFresh);Check(!Find<CheckBox>(setup,"campaign").Checked,"switching existing ON to a fresh path resets translation OFF");
   Switch(setup,enabled);Switch(setup,disabled);Check(!Find<CheckBox>(setup,"campaign").Checked,"Setup restores existing explicit translation OFF");
  }
  using(var setup=new Setup(enabled))Check(Find<CheckBox>(setup,"campaign").Checked,"opening existing ON installation retains the selection");
  using(var setup=new Setup(disabled))Check(!Find<CheckBox>(setup,"campaign").Checked,"opening existing OFF installation retains the selection");
  using(var setup=new Setup(fresh,true))Check(Find<CheckBox>(setup,"campaign").Checked,"explicit translation=true opts fresh Setup in");
  using(var setup=new Setup(enabled,false))Check(!Find<CheckBox>(setup,"campaign").Checked,"explicit translation=false overrides existing ON for review");
  foreach(var root in new[]{enabled,disabled})using(var launcher=new Launcher(root)){
   launcher.CheckUpdatesOnOpen=false;bool expected=Core.ReadState(root).campaign;
   Check(Find<CheckBox>(launcher,"koreanTranslation").Checked==expected,"Launcher reflects stored translation "+(expected?"ON":"OFF"));
   Check(Find<ComboBox>(launcher,"subtitlePosition").SelectedIndex==0,"Launcher uses original subtitle position when no preference exists");
  }
 }
 static void RuntimeDefaults(){
  string root=Fake("mouse_only_install");Install(root);var state=Core.ReadState(root);
  Check(state!=null&&!state.campaign&&state.mouse&&!state.display,"actual Core.Install records translation OFF and independent mouse ON");
  Check(Core.ReadIni(Core.Config(root,"subtitle.ini"),"subtitles")["position"]=="native","fresh installed subtitle.ini uses native position");
  var modules=Core.ReadIni(Core.Config(root,"pack.ini"),"modules");
  Check(modules["subtitles"]=="1"&&modules["mouseFlight"]=="1"&&modules["display"]=="0","subtitle layout remains enabled independently of translation");
  Check(!Has(root,Core.CampaignLoader)&&!Has(root,Core.CampaignPatch),"translation OFF installs neither campaign hook nor dictionary");
  Check(!Has(root,Core.CampaignPak)&&!Has(root,SharedLoader.CampaignPak)&&!Directory.GetFiles(root,"*.pak",SearchOption.AllDirectories).Any(),"translation OFF installs no PAK even if a stale whole PAK is supplied as common");
  Check(!state.files.Any(f=>f.path.EndsWith(".pak",StringComparison.OrdinalIgnoreCase)||f.path==Core.CampaignPatch||f.path==Core.CampaignLoader),"translation OFF owns no archive or translation files");
  using(var launcher=new Launcher(root)){
   launcher.CheckUpdatesOnOpen=false;launcher.Dialog=(message,icon)=>{throw new Exception("Unexpected launcher dialog: "+message);};
   var position=Find<ComboBox>(launcher,"subtitlePosition");Check(position.SelectedIndex==0,"Launcher reads fresh native subtitle position");
   Event(Find<Button>(launcher,"saveSubtitles"),"OnClick");
   Check(Core.ReadIni(Core.Config(root,"subtitle.ini"),"subtitles")["position"]=="native","real Launcher save preserves native subtitle position");
   position.SelectedIndex=1;Event(Find<Button>(launcher,"saveSubtitles"),"OnClick");
   Check(Core.ReadIni(Core.Config(root,"subtitle.ini"),"subtitles")["position"]=="bottom","owner can explicitly opt into bottom subtitle position");
  }
  using(var stream=File.OpenRead(payload))Core.UpdatePreservingState(root,stream,"");state=Core.ReadState(root);
  Check(!state.campaign&&state.mouse&&!state.display,"real update preserves selected OFF translation modules");
  Check(Core.ReadIni(Core.Config(root,"subtitle.ini"),"subtitles")["position"]=="bottom","real update preserves explicit subtitle position");
 }
 [STAThread] static int Main(string[] args){
  try{
   if(args.Length!=2)throw new ArgumentException("Expected temporary fixture folder and inert payload ZIP.");
   destination=Path.GetFullPath(args[0]);payload=Path.GetFullPath(args[1]);
   string temp=Path.GetFullPath(Path.GetTempPath()).TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar;
   if(!destination.StartsWith(temp,StringComparison.OrdinalIgnoreCase))throw new Exception("Fixtures must be inside the temporary directory.");
   Core.FrameGenerationTestDirectory=Path.Combine(destination,"isolated_user_settings");
   UiChoices();RuntimeDefaults();Console.WriteLine("PASS "+checks+" subtitle default/selection checks; no game or native mod executed.");return 0;
  }catch(Exception error){Console.Error.WriteLine(error);return 1;}
 }
}
