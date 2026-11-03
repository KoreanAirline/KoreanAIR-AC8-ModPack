using System;
using System.IO;
using System.Text;
using System.Linq;
using KoreanAIR;
class SubtitleLifecycleTests {
 static int checks;static int builds;
 static void Check(bool ok,string name){if(!ok)throw new Exception(name);checks++;}
 static void Refuse(Action action,string name){bool failed=false;try{action();}catch{failed=true;}Check(failed,name);}
 static void Put(string root,string relative,byte[] data){string path=Core.Safe(root,relative);Directory.CreateDirectory(Path.GetDirectoryName(path));File.WriteAllBytes(path,data);}
 static byte[] B(string value){return Encoding.UTF8.GetBytes(value);}
 static void Save(string root,State state){Core.Text(Core.Safe(root,Core.Folder+"/installed.json"),Core.Json.Serialize(state));}
 static void Main(string[] args){
  string root=Path.Combine(args[0],Guid.NewGuid().ToString("N"));Directory.CreateDirectory(root);
  var patch=B("verified fixture dictionary");Put(root,Core.CampaignPatch,patch);Put(root,Core.CampaignPak,B("old archive"));Put(root,Core.Mod+"config.ini",B("keep user input settings"));
  var state=new State{root=root,campaign=true,campaignProvider="standalone",backup=Path.Combine(root,"backup"),build=Core.ReleaseBuild};
  state.files.Add(new FileState{path=Core.CampaignPatch,hash=Core.Hash(patch)});state.files.Add(new FileState{path=Core.CampaignPak,hash=Core.Hash(B("old archive"))});Save(root,state);
  string inputHash=Core.HashFile(Core.Safe(root,Core.Mod+"config.ini"));
  CampaignSubtitles.TestFingerprint=(r,p)=>"current stock";
  CampaignSubtitles.TestBuild=(r,p)=>{builds++;return new CampaignSubtitles.Result{Pak=B("current dialogue archive"),Fingerprint="current stock",Status="Current dialogue only"};};
  Core.RefreshCampaignSubtitles(root);state=Core.ReadState(root);
  Check(builds==1&&state.campaignFingerprint=="current stock","current overlay generated once");
  Check(Core.HashFile(Core.Safe(root,Core.CampaignPak))==state.files.Single(x=>x.path==Core.CampaignPak).hash,"generated hash recorded");
  Core.RefreshCampaignSubtitles(root);Check(builds==1,"verified stock cache avoids regeneration");
  CampaignSubtitles.TestFingerprint=(r,p)=>{throw new InvalidDataException("updated stock fixture");};
  Core.RefreshCampaignSubtitles(root);state=Core.ReadState(root);
  Check(!File.Exists(Core.Safe(root,Core.CampaignPak))&&!state.files.Any(x=>x.path==Core.CampaignPak),"unknown update removes stale overlay");
  Check(state.campaign&&state.campaignFingerprint==null&&state.campaignStatus.StartsWith("Original subtitles retained:"),"selection retained with visible fallback reason");
  Check(Core.HashFile(Core.Safe(root,Core.Mod+"config.ini"))==inputHash,"input settings untouched by update fallback");
  Core.RefreshCampaignSubtitles(root);Check(!File.Exists(Core.Safe(root,Core.CampaignPak)),"repeated fallback never revives stale overlay");
  CampaignSubtitles.TestFingerprint=(r,p)=>"current stock";Core.RefreshCampaignSubtitles(root);Check(builds==2,"supported data regenerates after fallback");
  Put(root,Core.CampaignPak,B("foreign changed archive"));Refuse(()=>Core.RefreshCampaignSubtitles(root),"changed third-party archive preserved");
  Check(File.ReadAllText(Core.Safe(root,Core.CampaignPak))=="foreign changed archive","foreign bytes unchanged");
  Put(root,Core.CampaignPak,B("current dialogue archive"));Put(root,Core.CampaignPatch,B("changed dictionary"));
  Refuse(()=>Core.RefreshCampaignSubtitles(root),"changed dictionary rejected before launch");
  state=Core.ReadState(root);state.suspended=true;Save(root,state);Core.RefreshCampaignSubtitles(root);Check(builds==2,"suspended modules remain suspended");
  Console.WriteLine("PASS "+checks+" subtitle lifecycle checks; no live game changes.");
 }
}
