using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Globalization;
using System.Diagnostics;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.RegularExpressions;

namespace KoreanAIR {
// A manual, bounded diagnostic export. It never polls, uploads or changes settings.
public static class SupportReport {
 const int MaximumBytes=900*1024, SettingsLimit=64*1024;
 public sealed class Monitor {
  public int X,Y,Width,Height,WorkX,WorkY,WorkWidth,WorkHeight,ModeWidth,ModeHeight,Refresh;
  public bool Primary;
  public string Device;
 }
 public sealed class Sources {
  public string LocalData,Temporary,Profile,UserName,MachineName;
  public Func<Monitor[]> Monitors;
  public Func<bool> Running;
  public Sources() {
   LocalData=Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
   Temporary=Path.GetTempPath();Profile=Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
   UserName=Environment.UserName;MachineName=Environment.MachineName;Monitors=ReadMonitors;
  }
 }
 sealed class Writer {
  public readonly StringBuilder Text=new StringBuilder();
  readonly string root;readonly Sources sources;
  int used;bool full;
  public Writer(string r,Sources s){root=r;sources=s;}
  public void Add(string value) {
   if(full)return;value=Redact(value??"",root,sources)+"\r\n";
   int bytes=Encoding.UTF8.GetByteCount(value);
   if(used+bytes>MaximumBytes-256){Text.Append("\r\n[Report size limit reached; remaining sections omitted.]\r\n");full=true;return;}
   Text.Append(value);used+=bytes;
  }
  public void Section(string title,Action action) {
   Add("\r\n=== "+title+" ===");try{action();}catch(Exception ex){Add("Unavailable: "+ex.GetType().Name+": "+ex.Message);}
  }
 }
 public static string Create(string root){return Create(root,"en");}
 public static string Create(string root,string language){return Create(root,language,new Sources());}
 // Explicit sources allow topology and privacy tests without touching a user's configuration.
 public static string Create(string root,string language,Sources sources) {
  if(sources==null)throw new ArgumentNullException("sources");
  root=Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar,Path.AltDirectorySeparatorChar);
  var report=new Writer(root,sources);bool running=false;
  report.Add("KoreanAIR AC8 Mod Pack - Bug report (manual export)");
  report.Add("Generated UTC: "+DateTime.UtcNow.ToString("o",CultureInfo.InvariantCulture));
  report.Add("Launcher: "+Core.Brand+" build "+Core.ReleaseBuild+"; UI language: "+(language=="ko"?"ko":"en"));
  report.Add("OS: "+Environment.OSVersion.VersionString+"; OS 64-bit: "+Environment.Is64BitOperatingSystem+"; process 64-bit: "+Environment.Is64BitProcess);
  report.Add("Culture: "+CultureInfo.CurrentCulture.Name+"; UI culture: "+CultureInfo.CurrentUICulture.Name);
  report.Section("Capture status",delegate {
   running=sources.Running==null?Core.Running(root):sources.Running();report.Add("Game running: "+running);
   report.Add("This file is created only on request. No upload, memory dump or ongoing scan is performed.");
   report.Add("Close the game after reproducing the issue, then export again so buffered logs are flushed.");
   report.Add("Review this text before sharing it. Add the mission, camera mode, keys used, and approximate issue time.");
   if(language=="ko")report.Add("문제 재현 후 게임을 종료하고 이 보고서를 다시 만들어 보내주세요. 미션·시점·누른 키·발생 시각을 함께 적어주세요.");
  });
  State state=null;
  report.Section("Installed modules",delegate {
   string path=Core.Safe(root,Core.Folder+"/installed.json");
   if(!File.Exists(path)){report.Add("Installation record: missing");return;}
   bool truncated;string body=ReadBounded(path,512*1024,false,out truncated);
   if(truncated){report.Add("Installation record exceeds safe read limit; not parsed.");return;}
   state=Core.Json.Deserialize<State>(body);if(state==null){report.Add("Installation record: invalid");return;}
   report.Add("Installed version: "+state.version+"; build: "+state.build);
   report.Add("Korean translation: "+state.campaign+"; Mouse flight: "+state.mouse+"; Screen & camera: "+state.display+"; Suspended: "+state.suspended);
   report.Add("Frame generation request recorded by pack: "+(state.frameGeneration==null?"unmanaged":state.frameGeneration.enabled.ToString()));
   report.Add("The pack.ini subtitles module controls layout; Korean translation is the separate installed module above.");
  });
  report.Section("Monitors (current physical desktop)",delegate {
   var monitors=sources.Monitors==null?new Monitor[0]:sources.Monitors();
   report.Add(DescribeTopology(monitors));
   for(int i=0;i<monitors.Length;i++) {
    var m=monitors[i];report.Add("Monitor "+(i+1)+" "+(m.Primary?"PRIMARY ":"")+"bounds="+Rect(m.X,m.Y,m.Width,m.Height)+" work="+Rect(m.WorkX,m.WorkY,m.WorkWidth,m.WorkHeight)+" current mode="+m.ModeWidth+"x"+m.ModeHeight+" refresh="+m.Refresh+" Hz");
   }
  });
  report.Section("Mod settings (allowlisted values)",delegate {
   foreach(string name in new[]{"pack.ini","config.ini","display.ini","subtitle.ini","upscaler_status.ini"})
    AddIni(report,Core.Safe(root,Core.Mod+name),name,ModKey);
   report.Add("Diagnostic support snapshots, when enabled, are in the MouseAim log section below. Without them, input ownership/oscillation cannot be reconstructed from a screenshot.");
  });
  report.Section("Game settings (allowlisted values)",delegate {
   string config=LocalPath(sources,@"BANDAI NAMCO Entertainment\ACE COMBAT 8\Saved\Config\Windows");
   foreach(string name in new[]{"GameUserSettings.ini","Engine.ini","Game.ini"})AddIni(report,Path.Combine(config,name),name,GameKey);
   AddIni(report,Path.Combine(config,"Input.ini"),"Input.ini",InputKey);
  });
  report.Section("HOTAS input compatibility",delegate {var h=Core.InspectHotas(root);report.Add("Present="+h.Present+"; HOTAS enabled="+h.HotasEnabled+"; AnalogueYaw enabled="+h.AnalogYawEnabled+"; recognized shared runtime="+h.KnownSharedRuntime);});
  report.Section("Installed critical files",delegate {AddHashes(report,root,state);});
  report.Section("Game executable version/header",delegate {AddGameVersion(report,Core.Safe(root,"Game/Binaries/Win64/AceCombat8.exe"));});
  report.Section("MouseAim logs (latest two, bounded tails)",delegate {
   string logs=Core.Safe(root,Core.Mod+"Logs/placeholder.txt");
   var latest=LatestFiles(Path.GetDirectoryName(logs),"MouseAim-*.log",report);
   if(latest.Count==0)report.Add("No MouseAim logs found. The runtime may not have loaded; check critical files, modules and UE4SS log.");
   foreach(var path in latest.Take(2))AddTail(report,path,128*1024,running);
  });
  report.Section("UE4SS log (bounded tail)",delegate {AddTail(report,Core.Safe(root,"Game/Binaries/Win64/UE4SS/UE4SS.log"),128*1024,running);});
  report.Section("Launcher/setup/update errors (bounded)",delegate {
   if(!String.IsNullOrEmpty(sources.Temporary)) {
    AddTail(report,Path.Combine(sources.Temporary,"KoreanAIR_AC8_Launcher_error.txt"),24*1024,false);
    AddTail(report,Path.Combine(sources.Temporary,"KoreanAIR_AC8_Setup_error.txt"),24*1024,false);
   }
   AddTail(report,LocalPath(sources,Core.Folder+@"\Updates\last-result.json"),16*1024,false);
  });
  string relative=Core.Folder+"/Reports/BugReport_"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff",CultureInfo.InvariantCulture)+"_"+Guid.NewGuid().ToString("N").Substring(0,6)+".txt";
  try {string result=Core.Safe(root,relative);Core.Text(result,report.Text.ToString());return result;}
  catch(UnauthorizedAccessException){}
  catch(IOException){}
  // Installed games may be read-only for a standard user. Keep the same
  // bounded, private export in that user's application data instead.
  string fallback=LocalPath(sources,relative);Core.Text(fallback,report.Text.ToString());return fallback;
 }
 static string LocalPath(Sources sources,string relative) {
  if(String.IsNullOrEmpty(sources.LocalData))throw new IOException("Local application data is unavailable.");
  return Core.Safe(sources.LocalData,relative.Replace('\\','/'));
 }
 static string Rect(int x,int y,int w,int h){return x+","+y+" "+w+"x"+h;}
 public static string DescribeTopology(Monitor[] monitors) {
  if(monitors==null||monitors.Length==0)return "Active monitor count: 0 (enumeration unavailable).";
  long left=monitors.Min(m=>(long)m.X),top=monitors.Min(m=>(long)m.Y);
  long right=monitors.Max(m=>(long)m.X+m.Width),bottom=monitors.Max(m=>(long)m.Y+m.Height);
  string value="Active monitor count: "+monitors.Length+"; desktop union="+left+","+top+" "+(right-left)+"x"+(bottom-top);
  if(monitors.Length==1&&monitors[0].Height>0&&(double)monitors[0].Width/monitors[0].Height>2.0)
   value+="\r\nOne already-wide logical display detected (ultrawide or Surround); three-monitor span is not required.";
  return value;
 }
 static bool ModKey(string section,string key,string value) {
  section=section.ToLowerInvariant();key=key.ToLowerInvariant();
  string keys=null;
  if(section=="modules")keys="mouseflight display subtitles";
  else if(section=="diagnostics")keys="enabled support support_token";
  else if(section=="display")keys="span fov distance height enabled left_monitor center_monitor right_monitor";
  else if(section=="subtitles")keys="position";
  else if(section=="control")keys="sensitivity roll_gain pitch_gain yaw_gain turn_pull max_bank smoothing roll_damping pitch_damping yaw_damping dead_zone pitch_sign roll_sign yaw_sign horizontal_fov vertical_fov pitch_slot roll_slot look_sensitivity bank_limit response native_response_sync";
  else if(section=="hud")keys="aim_style heading_style aim_size heading_size aim_color heading_color line_width outline outline_width outline_color opacity";
  else if(section=="keys")keys="free_look hud_toggle steering_toggle recenter reload zoom";
  else if(section=="zoom")keys="enabled ratio";
  else if(section=="upscaler_status")return Regex.IsMatch(key,"^(schema|sample_unix|dlss|dlaa|dlssg|frame|reflex|resolution|render|screen|status|enabled|quality|fg|requested|active|supported|source|timing|cache|present|generated|native)[a-z0-9_]*$");
  return keys!=null&&(" "+keys+" ").IndexOf(" "+key+" ",StringComparison.Ordinal)>=0;
 }
 static bool GameKey(string section,string key,string value) {
  return Regex.IsMatch(key,@"^(sg\.[A-Za-z]+Quality|r\.(?:NGX|Streamline|ScreenPercentage|DynamicRes|VSync|OneFrameThreadLag|MaxAnisotropy|TextureStreaming|Streaming)[A-Za-z0-9_.]*|bUseVSync|bUseDynamicResolution|ResolutionSize[XY]|LastUserConfirmedResolutionSize[XY]|WindowPos[XY]|FullscreenMode|LastConfirmedFullscreenMode|PreferredFullscreenMode|FrameRateLimit|DesiredScreenWidth|DesiredScreenHeight|bUseHDRDisplayOutput|HDRDisplayOutputNits|Culture|Language|DLSS[A-Za-z]*|b[A-Za-z]*DLSS[A-Za-z]*|NVIDIA[A-Za-z]*)$",RegexOptions.IgnoreCase);
 }
 static bool InputKey(string section,string key,string value) {
  string k=key.TrimStart('+','-','.');
  if(k.Equals("AxisMappings",StringComparison.OrdinalIgnoreCase)||k.Equals("ActionMappings",StringComparison.OrdinalIgnoreCase))
   return Regex.IsMatch(value,"(?:pitch|roll|yaw|look|mouse|turn|camera|thrust|aircraft|highg|accel|decel)",RegexOptions.IgnoreCase);
  return Regex.IsMatch(k,"^(bEnableMouseSmoothing|bEnableFOVScaling|FOVScale|DoubleClickTime|DefaultViewportMouseCaptureMode|DefaultViewportMouseLockMode|bUseMouseForTouch|AxisConfig)$",RegexOptions.IgnoreCase);
 }
 delegate bool IniFilter(string section,string key,string value);
 static void AddIni(Writer report,string path,string name,IniFilter filter) {
  report.Add("--- "+name+" ---");if(!File.Exists(path)){report.Add("Missing");return;}
  try {
   bool truncated;string text=ReadBounded(path,SettingsLimit,false,out truncated),section="",last="";int count=0;
   foreach(string raw in text.Split(new[]{'\r','\n'},StringSplitOptions.RemoveEmptyEntries)) {
    string line=raw.Trim();if(line.Length==0||line.StartsWith(";")||line.StartsWith("#"))continue;
    if(line.StartsWith("[")&&line.EndsWith("]")){section=line.Substring(1,line.Length-2);continue;}
    int equals=line.IndexOf('=');if(equals<=0)continue;string key=line.Substring(0,equals).Trim(),value=line.Substring(equals+1).Trim();
    if(!filter(section,key,value))continue;
    if(last!=section){report.Add("["+section+"]");last=section;}
    report.Add(key+"="+(value.Length>512?value.Substring(0,512)+" [truncated]":value));if(++count>=256){report.Add("[Key limit reached]");break;}
   }
   if(count==0)report.Add("No allowlisted settings present.");if(truncated)report.Add("[File read limit reached]");
  }catch(Exception ex){report.Add("Unreadable: "+ex.GetType().Name+": "+ex.Message);}
 }
 static void AddHashes(Writer report,string root,State state) {
  string[] critical={"Game/Binaries/Win64/UE4SS/UE4SS.dll","Game/Binaries/Win64/UE4SS.dll","Game/Binaries/Win64/dwmapi.dll","Game/Binaries/Win64/dxgi.dll",Core.CampaignLoader,Core.Mod+"scripts/ac8_mouse_aim_010.dll",Core.Mod+"scripts/main.lua",Core.Mod+"scripts/display.lua",Core.Mod+"scripts/headlook.lua",Core.Mod+"enabled.txt","Game/Binaries/Win64/UE4SS/Mods/mods.txt","Game/Binaries/Win64/UE4SS/UE4SS-settings.ini",Core.Brand+".exe"};
  long remaining=64L*1024*1024;
  foreach(string relative in critical) {
   try {
    string path=Core.Safe(root,relative);var owned=state==null||state.files==null?null:state.files.FirstOrDefault(f=>f!=null&&String.Equals(f.path,relative,StringComparison.OrdinalIgnoreCase));
    string expected=owned==null?"not recorded":owned.mutable?"mutable (no integrity expectation)":owned.hash;
    if(!File.Exists(path)){report.Add(relative+": MISSING; expected="+expected);continue;}
    var info=new FileInfo(path);long size=info.Length;string actual="skipped (read budget)";
    if(size<=24L*1024*1024&&size<=remaining) {remaining-=size;actual=HashBounded(path,size);}
    string status=owned!=null&&!owned.mutable&&actual.Length==64?(String.Equals(actual,owned.hash,StringComparison.OrdinalIgnoreCase)?"MATCH":"MISMATCH"):"informational";
    report.Add(relative+": bytes="+size+" SHA256="+actual+" expected="+expected+" status="+status);
   }catch(Exception ex){report.Add(relative+": "+ex.GetType().Name+": "+ex.Message);}
  }
 }
 static string HashBounded(string path,long length) {
  using(var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(var sha=SHA256.Create()) {
   if(file.Length!=length)throw new IOException("File changed during collection; regenerate after closing the game.");
   byte[] buffer=new byte[65536];long remaining=length;
   while(remaining>0){int n=file.Read(buffer,0,(int)Math.Min(buffer.Length,remaining));if(n<=0)throw new EndOfStreamException();sha.TransformBlock(buffer,0,n,null,0);remaining-=n;}
   sha.TransformFinalBlock(new byte[0],0,0);if(file.Length!=length)throw new IOException("File changed during collection.");
   return BitConverter.ToString(sha.Hash).Replace("-","").ToLowerInvariant();
  }
 }
 static void AddGameVersion(Writer report,string path) {
  if(!File.Exists(path)){report.Add("Game executable: missing");return;}
  var version=FileVersionInfo.GetVersionInfo(path);report.Add("Game file version: "+version.FileVersion+"; product version: "+version.ProductVersion+"; bytes="+new FileInfo(path).Length);
  using(var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete))using(var reader=new BinaryReader(file)) {
   if(file.Length<64||reader.ReadUInt16()!=0x5A4D){report.Add("Invalid MZ header");return;}file.Position=0x3C;int pe=reader.ReadInt32();
   if(pe<64||pe>1024*1024||pe>file.Length-120){report.Add("Invalid PE offset");return;}file.Position=pe;
   if(reader.ReadUInt32()!=0x4550){report.Add("Invalid PE header");return;}ushort machine=reader.ReadUInt16();file.Position=pe+8;uint timestamp=reader.ReadUInt32();file.Position=pe+24+56;uint image=reader.ReadUInt32();
   report.Add("PE machine=0x"+machine.ToString("X4")+" timestamp=0x"+timestamp.ToString("X8")+" imageSize=0x"+image.ToString("X8"));
   report.Add("Supported native image: "+(machine==0x8664&&timestamp==0x6AA0E27D&&image==0x2195A000));
  }
 }
 static List<string> LatestFiles(string folder,string pattern,Writer report) {
  var files=new List<FileInfo>();if(!Directory.Exists(folder))return new List<string>();int count=0;
  foreach(string file in Directory.EnumerateFiles(folder,pattern,SearchOption.TopDirectoryOnly)) {
   if(++count>1024){report.Add("Log directory enumeration limited to 1024 files.");break;}
   try{if((File.GetAttributes(file)&FileAttributes.ReparsePoint)==0)files.Add(new FileInfo(file));}catch{}
  }
  return files.OrderByDescending(f=>f.LastWriteTimeUtc).ThenByDescending(f=>f.Name,StringComparer.OrdinalIgnoreCase).Take(2).Select(f=>f.FullName).ToList();
 }
 static void AddTail(Writer report,string path,int limit,bool running) {
  report.Add("--- "+Path.GetFileName(path)+" ---");
  if(!File.Exists(path)){report.Add("Missing");return;}
  try {
   var info=new FileInfo(path);report.Add("Bytes="+info.Length+"; modified UTC="+info.LastWriteTimeUtc.ToString("o",CultureInfo.InvariantCulture));
   if(info.Length==0){report.Add(running?"EMPTY / FLUSH PENDING: game is running; close it and export again.":"EMPTY: no saved data; the log may not have been flushed or runtime loading may have failed.");return;}
   bool truncated;string text=ReadBounded(path,limit,true,out truncated);if(truncated)report.Add("[Earlier lines omitted; bounded tail follows]");report.Add(text);
  }catch(Exception ex){report.Add("Unreadable: "+ex.GetType().Name+": "+ex.Message);}
 }
 static string ReadBounded(string path,int limit,bool tail,out bool truncated) {
  if((File.GetAttributes(path)&FileAttributes.ReparsePoint)!=0)throw new IOException("Redirected files are not collected.");
  using(var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete)) {
   long size=file.Length;truncated=size>limit;long start=tail&&truncated?size-limit:0;file.Position=start;
   int length=(int)Math.Min(limit,size-start),total=0;byte[] bytes=new byte[length];
   while(total<length){int n=file.Read(bytes,total,length-total);if(n==0)break;total+=n;}
   string text;using(var memory=new MemoryStream(bytes,0,total))using(var reader=new StreamReader(memory,Encoding.UTF8,true))text=reader.ReadToEnd();
   if(start>0){int line=text.IndexOf('\n');text=line<0?"[No complete line in tail]":text.Substring(line+1);}
   return text;
  }
 }
 static string Replace(string text,string value,string replacement) {
  if(String.IsNullOrEmpty(value))return text;
  text=Regex.Replace(text,Regex.Escape(value.TrimEnd('\\','/')),delegate(Match m){return replacement;},RegexOptions.IgnoreCase);
  return Regex.Replace(text,Regex.Escape(value.TrimEnd('\\','/').Replace('\\','/')),delegate(Match m){return replacement;},RegexOptions.IgnoreCase);
 }
 public static string Redact(string text,string root,Sources sources) {
  text=Replace(text,root,"<GAME>");text=Replace(text,sources.LocalData,"<LOCALAPPDATA>");text=Replace(text,sources.Temporary,"<TEMP>");text=Replace(text,sources.Profile,"<USERPROFILE>");
  text=Regex.Replace(text,@"(?i)[A-Z]:[\\/][^\r\n\""<>|]*","<PATH>");
  text=Regex.Replace(text,@"(?i)\\\\(?!\.\\)[^\r\n\""<>|]+","<NETWORK_PATH>");
  if(!String.IsNullOrEmpty(sources.UserName))text=Regex.Replace(text,@"(?i)(?<![\p{L}\p{N}_])"+Regex.Escape(sources.UserName)+@"(?![\p{L}\p{N}_])","<USER>");
  if(!String.IsNullOrEmpty(sources.MachineName))text=Regex.Replace(text,@"(?i)(?<![\p{L}\p{N}_])"+Regex.Escape(sources.MachineName)+@"(?![\p{L}\p{N}_])","<MACHINE>");
  text=Regex.Replace(text,@"(?im)^.*(?:access[_ -]?token|refresh[_ -]?token|authorization\s*:|password\s*[:=]|client_secret|steamid|epicid|hardwareid|machineguid|machinename|computername|username\s*[:=]|(?:PCI|USB)\\(?:VEN_|VID_)).*$","[Sensitive line omitted]");
  text=Regex.Replace(text,@"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b","<EMAIL>");
  text=Regex.Replace(text,@"\b7656119\d{10}\b","<ACCOUNT_ID>");
  return text.Replace("\0","");
 }
 [StructLayout(LayoutKind.Sequential)]struct RECT {public int Left,Top,Right,Bottom;}
 [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)]struct MONITORINFOEX {public int Size;public RECT Monitor,Work;public uint Flags;[MarshalAs(UnmanagedType.ByValTStr,SizeConst=32)]public string Device;}
 [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)]struct DEVMODE {
  [MarshalAs(UnmanagedType.ByValTStr,SizeConst=32)]public string Device;
  public ushort SpecVersion,DriverVersion,Size,Extra;public uint Fields;public int PositionX,PositionY;public uint Orientation,FixedOutput;
  public short Color,Duplex,YResolution,TTOption,Collate;[MarshalAs(UnmanagedType.ByValTStr,SizeConst=32)]public string Form;
  public ushort LogPixels;public uint BitsPerPixel,Width,Height,DisplayFlags,Frequency,ICMMethod,ICMIntent,MediaType,DitherType,Reserved1,Reserved2,PanningWidth,PanningHeight;
 }
 delegate bool MonitorEnum(IntPtr monitor,IntPtr dc,ref RECT rectangle,IntPtr data);
 [DllImport("user32.dll")]static extern bool EnumDisplayMonitors(IntPtr dc,IntPtr clip,MonitorEnum callback,IntPtr data);
 [DllImport("user32.dll",CharSet=CharSet.Unicode,EntryPoint="GetMonitorInfoW")]static extern bool GetMonitorInfo(IntPtr monitor,ref MONITORINFOEX info);
 [DllImport("user32.dll",CharSet=CharSet.Unicode,EntryPoint="EnumDisplaySettingsW")]static extern bool EnumDisplaySettings(string device,int mode,ref DEVMODE settings);
 [DllImport("user32.dll")]static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);
 public static Monitor[] ReadMonitors() {
  var result=new List<Monitor>();IntPtr previous=IntPtr.Zero;
  try {
   try{previous=SetThreadDpiAwarenessContext(new IntPtr(-4));}catch(EntryPointNotFoundException){}
   MonitorEnum callback=delegate(IntPtr handle,IntPtr dc,ref RECT rectangle,IntPtr data) {
    var info=new MONITORINFOEX{Size=Marshal.SizeOf(typeof(MONITORINFOEX))};if(!GetMonitorInfo(handle,ref info))return true;
    var mode=new DEVMODE{Size=(ushort)Marshal.SizeOf(typeof(DEVMODE))};bool current=EnumDisplaySettings(info.Device,-1,ref mode);
    result.Add(new Monitor{Device=info.Device,X=info.Monitor.Left,Y=info.Monitor.Top,Width=info.Monitor.Right-info.Monitor.Left,Height=info.Monitor.Bottom-info.Monitor.Top,WorkX=info.Work.Left,WorkY=info.Work.Top,WorkWidth=info.Work.Right-info.Work.Left,WorkHeight=info.Work.Bottom-info.Work.Top,Primary=(info.Flags&1)!=0,ModeWidth=current?(int)mode.Width:0,ModeHeight=current?(int)mode.Height:0,Refresh=current?(int)mode.Frequency:0});return true;
   };
   if(!EnumDisplayMonitors(IntPtr.Zero,IntPtr.Zero,callback,IntPtr.Zero))throw new IOException("Windows monitor enumeration failed.");
  }finally{if(previous!=IntPtr.Zero)SetThreadDpiAwarenessContext(previous);}
  return result.ToArray();
 }
}
}
