using System;
using System.IO;
using System.Net;
using System.Net.Cache;
using System.Linq;
using System.Diagnostics;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;

namespace KoreanAIR {
public sealed class UpdateManifest {
 public int schema; public string version; public long build; public string tag;
 public string installer; public string sha256; public long size;
}
public static class UpdateCore {
 public const string Repository="KoreanAirline/KoreanAIR-AC8-ModPack";
 public const string Feed="https://github.com/"+Repository+"/releases/latest/download/update.json";
 const long MaximumInstaller=128L*1024*1024;
 static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
 public static UpdateManifest Parse(string json) {
  if(json==null||json.Length>65536)throw new InvalidDataException("Invalid update information.");
  var m=Core.Json.Deserialize<UpdateManifest>(json);Version version;
  if(m==null||m.schema!=1||!Version.TryParse(m.version,out version)||version.Major<1||version.Build!=-1||m.build<=0||
     m.tag!="v"+m.version+"-b"+m.build||m.installer!="KoreanAIR_AC8_ModPack_"+m.version+"_Setup.exe"||
     m.size<1024||m.size>MaximumInstaller||m.sha256==null||!Regex.IsMatch(m.sha256,"^[a-f0-9]{64}$"))
   throw new InvalidDataException("Invalid update information.");
  return m;
 }
 public static bool IsNewer(UpdateManifest m) {
  var current=new Version(Core.Brand.Substring("KoreanAIR_AC8_ModPack_".Length));
  int comparison=new Version(m.version).CompareTo(current);
  return comparison>0||(comparison==0&&m.build>Core.ReleaseBuild);
 }
 public static string InstallerUrl(UpdateManifest m) { Parse(Core.Json.Serialize(m));return "https://github.com/"+Repository+"/releases/download/"+m.tag+"/"+m.installer; }
 static HttpWebResponse Response(string url,int timeout) {
  ServicePointManager.SecurityProtocol|=SecurityProtocolType.Tls12;
  var request=(HttpWebRequest)WebRequest.Create(url);request.Timeout=timeout;request.ReadWriteTimeout=timeout;
  request.UserAgent="KoreanAIR-AC8-ModPack/"+Core.ReleaseBuild;request.CachePolicy=new RequestCachePolicy(RequestCacheLevel.NoCacheNoStore);
  request.AllowAutoRedirect=true;request.MaximumAutomaticRedirections=5;
  var response=(HttpWebResponse)request.GetResponse();
  string host=response.ResponseUri.Host;
  if(response.ResponseUri.Scheme!="https"||(host!="github.com"&&!host.EndsWith(".githubusercontent.com",StringComparison.OrdinalIgnoreCase))) {
   response.Dispose();throw new InvalidDataException("Unexpected update download location.");
  }
  return response;
 }
 public static UpdateManifest Fetch(CancellationToken cancel) {
  using(var response=Response(Feed,7000))using(var stream=response.GetResponseStream())using(var bytes=new MemoryStream()) {
   var buffer=new byte[4096];int read;
   while((read=stream.Read(buffer,0,buffer.Length))>0){cancel.ThrowIfCancellationRequested();if(bytes.Length+read>65536)throw new InvalidDataException("Invalid update information.");bytes.Write(buffer,0,read);}
   return Parse(Utf8.GetString(bytes.ToArray()));
  }
 }
 public static string Download(UpdateManifest manifest,Action<int> progress,CancellationToken cancel) {
  string url=InstallerUrl(manifest);
  string directory=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),Core.Folder,"Updates",Guid.NewGuid().ToString("N"));
  Directory.CreateDirectory(directory);string partial=Path.Combine(directory,"download.part"),path=Path.Combine(directory,manifest.installer);
  try {
   using(var response=Response(url,30000))using(var source=response.GetResponseStream())using(var output=new FileStream(partial,FileMode.CreateNew,FileAccess.Write,FileShare.None)) {
    if(response.ContentLength>0&&response.ContentLength!=manifest.size)throw new InvalidDataException("Update download verification failed.");
    var buffer=new byte[65536];long total=0;int read,last=-1;
    while((read=source.Read(buffer,0,buffer.Length))>0) {
     cancel.ThrowIfCancellationRequested();total+=read;if(total>manifest.size)throw new InvalidDataException("Update download verification failed.");output.Write(buffer,0,read);
     int percent=(int)(100*total/manifest.size);if(percent!=last){last=percent;if(progress!=null)progress(percent);}
    }
    if(total!=manifest.size)throw new InvalidDataException("Update download verification failed.");
   }
   VerifyDownload(manifest,partial);File.Move(partial,path);return path;
  } catch { if(File.Exists(partial))File.Delete(partial);if(File.Exists(path))File.Delete(path);if(!Directory.EnumerateFileSystemEntries(directory).Any())Directory.Delete(directory);throw; }
 }
 public static void VerifyDownload(UpdateManifest manifest,string path) {
  if(!File.Exists(path)||new FileInfo(path).Length!=manifest.size||Core.HashFile(path)!=manifest.sha256)throw new InvalidDataException("Update download verification failed.");
  using(var b=new BinaryReader(File.OpenRead(path))) {
   if(b.ReadUInt16()!=0x5a4d)throw new InvalidDataException("Invalid update installer.");b.BaseStream.Position=0x3c;int pe=b.ReadInt32();
   if(pe<64||pe>b.BaseStream.Length-26)throw new InvalidDataException("Invalid update installer.");b.BaseStream.Position=pe;
   if(b.ReadUInt32()!=0x4550||b.ReadUInt16()!=0x8664)throw new InvalidDataException("Invalid update installer.");
  }
  var identity=FileVersionInfo.GetVersionInfo(path);
  if(identity.ProductName!="KoreanAIR AC8 Mod Pack"||identity.ProductVersion!=manifest.version+"+b"+manifest.build||identity.FileMajorPart!=new Version(manifest.version).Major||identity.FileMinorPart!=new Version(manifest.version).Minor)
   throw new InvalidDataException("Invalid update installer.");
 }
 public static void StartInstaller(string root,UpdateManifest manifest,string path) {
  if(Core.Running(root))throw new Exception("Close ACE COMBAT 8 first.");
  VerifyDownload(manifest,path);
  var parent=Process.GetCurrentProcess();
  Process.Start(new ProcessStartInfo(path,"--apply-update \""+Path.GetFullPath(root)+"\" "+parent.Id+" "+parent.StartTime.ToUniversalTime().Ticks){UseShellExecute=true,WorkingDirectory=Path.GetDirectoryName(path),WindowStyle=ProcessWindowStyle.Hidden});
 }
 public static void ApplyInstaller(string root,string pidText,string ticksText,Assembly installer) {
  try {
   WaitForLauncherExit(root,pidText,ticksText);
   using(var payload=installer.GetManifestResourceStream("Payload.zip"))Core.UpdatePreservingState(root,payload,installer.Location);
   RecordResult(new{success=true,version=Core.Brand,build=Core.ReleaseBuild});
  } catch(Exception ex) {
   RecordResult(new{success=false,message=ex.Message});
   System.Windows.Forms.MessageBox.Show(new UiLanguage().Error(ex),Core.Brand,System.Windows.Forms.MessageBoxButtons.OK,System.Windows.Forms.MessageBoxIcon.Error);
   try{var previous=Core.ReadState(root);string launcher=previous.files.First(f=>f.path.StartsWith("KoreanAIR_AC8_ModPack_",StringComparison.OrdinalIgnoreCase)&&f.path.EndsWith(".exe",StringComparison.OrdinalIgnoreCase)).path;Process.Start(new ProcessStartInfo(Core.Safe(root,launcher)){WorkingDirectory=root,UseShellExecute=true});}catch{}
   throw;
  }
  Process.Start(new ProcessStartInfo(Core.Safe(root,Core.Brand+".exe")){WorkingDirectory=root,UseShellExecute=true});
 }
 static void RecordResult(object result) {try{Core.Text(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),Core.Folder,"Updates","last-result.json"),Core.Json.Serialize(result));}catch{} }
 public static void WaitForLauncherExit(string root,string pidText,string ticksText) {
  int pid;long ticks;if(!Int32.TryParse(pidText,out pid)||pid<=0||!Int64.TryParse(ticksText,out ticks)||ticks<=0)throw new Exception("Invalid update request.");
  Process parent;try{parent=Process.GetProcessById(pid);}catch(ArgumentException){return;}
  using(parent) {
   try {
    if(parent.StartTime.ToUniversalTime().Ticks!=ticks)throw new Exception("Invalid update request.");
    var installed=Core.ReadState(root);if(installed==null)throw new Exception("Run the installer first.");
    string expected=installed.files.First(f=>f.path.StartsWith("KoreanAIR_AC8_ModPack_",StringComparison.OrdinalIgnoreCase)&&f.path.EndsWith(".exe",StringComparison.OrdinalIgnoreCase)).path;
    if(!String.Equals(parent.MainModule.FileName,Core.Safe(root,expected),StringComparison.OrdinalIgnoreCase))throw new Exception("Invalid update request.");
    if(!parent.WaitForExit(20000))throw new Exception("Close the launcher before applying the update.");
   } catch(InvalidOperationException){if(!AlreadyExited(parent))throw;}
   catch(System.ComponentModel.Win32Exception){if(!AlreadyExited(parent))throw;}
  }
 }
 static bool AlreadyExited(Process parent) {
  try{return parent.HasExited;}catch {try{using(var current=Process.GetProcessById(parent.Id))return current.HasExited;}catch(ArgumentException){return true;}}
 }
}
}
