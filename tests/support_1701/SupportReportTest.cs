using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Collections.Generic;
using KoreanAIR;

static class SupportReportTest {
 static int checks;
 static void Check(bool value,string message){checks++;if(!value)throw new Exception(message);}
 static void Put(string path,string value){Directory.CreateDirectory(Path.GetDirectoryName(path));File.WriteAllText(path,value,new UTF8Encoding(false));}
 static SupportReport.Monitor Monitor(int x,int y,int w,int h,bool primary,int hz) {return new SupportReport.Monitor{X=x,Y=y,Width=w,Height=h,WorkX=x,WorkY=y,WorkWidth=w,WorkHeight=h-40,Primary=primary,ModeWidth=w,ModeHeight=h,Refresh=hz};}
 static int Main(string[] args) {try{Run(args);return 0;}catch(Exception ex){Console.Error.WriteLine(ex.GetType().FullName);Console.Error.WriteLine(ex.Message);Console.Error.WriteLine("Completed checks: "+checks);return 1;}}
 static void Run(string[] args) {
  string work=Path.GetFullPath(args[0]),game=Path.Combine(work,"sample-game"),local=Path.Combine(work,"private-local"),temp=Path.Combine(work,"private-temp"),profile=Path.Combine(work,"private-profile");
  Directory.CreateDirectory(game);Directory.CreateDirectory(local);Directory.CreateDirectory(temp);Directory.CreateDirectory(profile);
  var monitors=new[]{Monitor(-1920,0,1920,1080,false,144),Monitor(0,0,1920,1080,true,180),Monitor(1920,0,1920,1080,false,165)};
  var sources=new SupportReport.Sources{LocalData=local,Temporary=temp,Profile=profile,UserName="PRIVATE_NAME",MachineName="PRIVATE_MACHINE",Monitors=()=>monitors,Running=()=>true};
  string mod=Path.Combine(game,Core.Mod.Replace('/',Path.DirectorySeparatorChar));
  string ini=Path.Combine(mod,"config.ini"),display=Path.Combine(mod,"display.ini"),pack=Path.Combine(mod,"pack.ini");
  Put(ini,"[control]\nsensitivity=0.1\nlook_sensitivity=0.03\nsecret=OMIT_SECRET\n[keys]\nfree_look=18\nzoom=2\n");
  Put(display,"[display]\nspan=1\nfov=100\nenabled=1\n");Put(pack,"[modules]\nmouseFlight=1\ndisplay=1\nsubtitles=1\n[diagnostics]\nsupport=1\nenabled=0\n");
  Put(Path.Combine(mod,"upscaler_status.ini"),"[upscaler_status]\ndlss_enabled=1\ndlss_mode=quality\nfg_mode=2x\nfg_actual_frames=2\n");
  Put(Path.Combine(mod,"subtitle.ini"),"[subtitles]\nposition=bottom\n");
  string native=Path.Combine(mod,"scripts","ac8_mouse_aim_010.dll");Put(native,"dummy-runtime");
  var state=new State{version="2.2",build=2026101608,root=game,campaign=false,mouse=true,display=true,suspended=false,backup="PRIVATE_BACKUP_DO_NOT_EXPORT"};
  state.files.Add(new FileState{path=Core.Mod+"scripts/ac8_mouse_aim_010.dll",hash=new string('0',64)});
  Put(Path.Combine(game,Core.Folder,"installed.json"),Core.Json.Serialize(state));
  string config=Path.Combine(local,@"BANDAI NAMCO Entertainment\ACE COMBAT 8\Saved\Config\Windows");
  Put(Path.Combine(config,"GameUserSettings.ini"),"[ScalabilityGroups]\nsg.ShadowQuality=2\n[/Script/Live.LiveGameUserSettings]\nDefaultUsername=OMIT_USERNAME\nResolutionSizeX=5760\nResolutionSizeY=1080\nFullscreenMode=2\nFrameRateLimit=0\n");
  Put(Path.Combine(config,"Engine.ini"),"[ConsoleVariables]\nr.NGX.DLSS.Enable=1\nr.Streamline.DLSSG.Enable=1\n[Internationalization]\nCulture=en-US\n");
  Put(Path.Combine(config,"Input.ini"),"[/Script/Engine.InputSettings]\n+AxisMappings=(AxisName=\"MouseLook\",Scale=1.0,Key=MouseX)\n+ActionMappings=(ActionName=\"CameraLook\",Key=LeftAlt)\n+ActionMappings=(ActionName=\"Chat\",Key=Enter)\nExec=OMIT_EXEC\nbEnableMouseSmoothing=False\n");
  string logs=Path.Combine(mod,"Logs");Put(Path.Combine(logs,"MouseAim-00001.log"),"OMIT_OLD_THIRD_LOG");
  Put(Path.Combine(logs,"MouseAim-00002.log"),"OMIT_FIRST_LINE\n"+new string('x',140*1024)+"\nSUPPORT dx=0 dy=0 pitch=0.3\n"+game+"\\native.dll\n"+local+"\\private.ini\n"+profile+"\\settings\nPRIVATE_NAME\npassword=OMIT_PASSWORD\nC:\\Users\\USER\\private.txt\nFINAL_LOG_SENTINEL\n");
  Put(Path.Combine(logs,"MouseAim-00003.log"),"");DateTime time=DateTime.UtcNow.AddSeconds(-10);
  for(int i=1;i<=3;i++)File.SetLastWriteTimeUtc(Path.Combine(logs,"MouseAim-0000"+i+".log"),time.AddSeconds(i));
  Put(Path.Combine(game,"Game","Binaries","Win64","UE4SS","UE4SS.log"),"UE4SS_LOADED\nAuthorization: Bearer OMIT_TOKEN\nPRIVATE_MACHINE\nprivate@example.com\n76561191234567890\nPCI\\VEN_OMIT_HARDWARE\n");
  Put(Path.Combine(temp,"KoreanAIR_AC8_Launcher_error.txt"),"System.IO.FileNotFoundException: "+game+"\\file.tmp\n");
  Put(Path.Combine(local,Core.Folder,"Updates","last-result.json"),"{\"success\":true,\"build\":2026101608}");
  string original=File.ReadAllText(ini),originalDisplay=File.ReadAllText(display),originalPack=File.ReadAllText(pack);
  string result=SupportReport.Create(game,"ko",sources),text=File.ReadAllText(result,Encoding.UTF8);
  Check(result.StartsWith(Path.Combine(game,Core.Folder,"Reports")),"fixed report destination");
  Check(Path.GetExtension(result)==".txt"&&new FileInfo(result).Length<=900*1024,"bounded UTF8 text");
  foreach(string present in new[]{"Installed version: 2.2; build: 2026101608","Korean translation: False; Mouse flight: True; Screen & camera: True","desktop union=-1920,0 5760x1080","refresh=180 Hz","span=1","look_sensitivity=0.03","dlss_mode=quality","fg_actual_frames=2","support=1","Culture=en-US","Key=MouseX","Key=LeftAlt","FLUSH PENDING","FINAL_LOG_SENTINEL","UE4SS_LOADED","MISMATCH","<GAME>","<LOCALAPPDATA>","<USERPROFILE>","<USER>","<PATH>","Sensitive line omitted"})Check(text.Contains(present),"expected evidence: "+present);
  foreach(string absent in new[]{"OMIT_SECRET","OMIT_USERNAME","OMIT_EXEC","PRIVATE_BACKUP_DO_NOT_EXPORT","OMIT_OLD_THIRD_LOG","OMIT_FIRST_LINE","OMIT_PASSWORD","OMIT_TOKEN","OtherPerson","PRIVATE_NAME","PRIVATE_MACHINE","private@example.com","76561191234567890","OMIT_HARDWARE",game,local,profile,"ActionName=\"Chat\""})Check(!text.Contains(absent),"privacy/whitelist: "+absent);
  Check(original==File.ReadAllText(ini)&&originalDisplay==File.ReadAllText(display)&&originalPack==File.ReadAllText(pack),"settings unchanged");
  Check(File.ReadAllText(native)=="dummy-runtime","critical files unchanged");
  Check(Directory.GetFiles(Path.Combine(game,Core.Folder,"Reports")).Length==1,"manual export only one file");
  monitors=new[]{Monitor(-2560,0,2560,1440,false,180),Monitor(0,0,2560,1440,true,180),Monitor(2560,0,2560,1440,false,180)};
  Check(SupportReport.DescribeTopology(monitors).Contains("7680x1440"),"QHD triple");
  monitors=new[]{Monitor(0,-2160,3840,2160,false,120),Monitor(0,0,3840,2160,true,144),Monitor(3840,0,3840,2160,false,60)};
  Check(SupportReport.DescribeTopology(monitors).Contains("7680x4320"),"4K mixed topology");
  foreach(int width in new[]{3440,3840,5120,5760})Check(SupportReport.DescribeTopology(new[]{Monitor(0,0,width,1080,true,240)}).Contains("already-wide"),"single ultrawide/surround "+width);
  Check(SupportReport.DescribeTopology(new SupportReport.Monitor[0]).Contains("unavailable"),"empty enumeration explicit");
  string active=Path.Combine(logs,"MouseAim-00003.log");
  Put(active,"LOCKED_NONEMPTY_LOG\n");
  using(var file=new FileStream(active,FileMode.Open,FileAccess.ReadWrite,FileShare.None)) {
   string locked=File.ReadAllText(SupportReport.Create(game,"en",sources));Check(locked.Contains("Unreadable: IOException")&&locked.Contains("UE4SS_LOADED"),"locked log isolated");
  }
  Put(active,"ACTIVE_UNFLUSHED_DATA\n");
  using(var file=new FileStream(active,FileMode.Open,FileAccess.ReadWrite,FileShare.ReadWrite)) {
   string shared=File.ReadAllText(SupportReport.Create(game,"en",sources));Check(shared.Contains("ACTIVE_UNFLUSHED_DATA"),"active shared log readable");
  }
  sources.Running=()=>false;Put(active,"");
  Check(File.ReadAllText(SupportReport.Create(game,"en",sources)).Contains("EMPTY: no saved data"),"closed empty log diagnostic");
  sources.Monitors=()=>{throw new IOException("Enumeration unavailable");};
  Check(File.ReadAllText(SupportReport.Create(game,"en",sources)).Contains("Enumeration unavailable"),"monitor failure isolated");
  string iniLong=original+new string('z',100*1024);Put(ini,iniLong);
  Check(File.ReadAllText(SupportReport.Create(game,"en",sources)).Contains("File read limit reached"),"oversized config bounded");
  var physical=SupportReport.ReadMonitors();Check(physical.Length>0,"real Win32 monitor enumeration");
  foreach(var monitor in physical)Check(monitor.Width>0&&monitor.Height>0&&monitor.ModeWidth>0&&monitor.ModeHeight>0&&monitor.Refresh>0,"physical monitor mode");
  string blockedGame=Path.Combine(work,"blocked-game"),occupied=Path.Combine(blockedGame,Core.Folder,"Reports");
  Put(occupied,"EXISTING_FILE_MUST_STAY");
  string fallback=SupportReport.Create(blockedGame,"en",sources);
  Check(fallback.StartsWith(Path.Combine(local,Core.Folder,"Reports")),"unwritable game report destination falls back to per-user application data");
  Check(File.Exists(fallback)&&new FileInfo(fallback).Length<=900*1024&&File.ReadAllText(fallback).Contains("Bug report (manual export)"),"fallback preserves bounded text report");
  Check(File.ReadAllText(occupied)=="EXISTING_FILE_MUST_STAY","fallback preserves blocking original file");
  Check(File.ReadAllText(ini)==iniLong&&File.ReadAllText(display)==originalDisplay&&File.ReadAllText(pack)==originalPack,"fallback leaves settings unchanged");
  string summary="PASS "+checks+" checks; physical monitors="+physical.Length;
  Console.WriteLine(summary);File.WriteAllText(Path.Combine(work,"results.json"),"{\"pass\":true,\"checks\":"+checks+",\"physical_monitors\":"+physical.Length+"}");
 }
}
