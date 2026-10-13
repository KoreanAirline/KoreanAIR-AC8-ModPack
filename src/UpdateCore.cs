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
using System.IO.Compression;
using System.Security.Cryptography;

namespace KoreanAIR {
public sealed class InstallerPayloadDescriptor {
 public int schema; public string version; public long build; public string tag;
 public string filename; public string sha256; public long size; public string url; public string manifest_sha256;
}
// The installer contains release metadata only. Installation files remain a
// normal ZIP beside it, or are fetched from that exact release and verified.
public static class ReleasePayload {
 const long MaximumPayload=512L*1024*1024;
 static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
 static byte[] Resource(Assembly installer,string name,int maximum) {
  using(var stream=installer.GetManifestResourceStream(name)) {
   if(stream==null)return null;
   using(var bytes=new MemoryStream()) {
    var buffer=new byte[4096];int read;
    while((read=stream.Read(buffer,0,buffer.Length))>0) {
     if(bytes.Length+read>maximum)throw new InvalidDataException("Payload integrity check failed: "+name);
     bytes.Write(buffer,0,read);
    }
    return bytes.ToArray();
   }
  }
 }
 public static InstallerPayloadDescriptor ReadDescriptor(Assembly installer) {
  var bytes=Resource(installer,"PayloadDescriptor.json",8192);
  if(bytes==null)return null;
  InstallerPayloadDescriptor m;
  try {m=Core.Json.Deserialize<InstallerPayloadDescriptor>(Utf8.GetString(bytes));}
  catch {throw new InvalidDataException("Payload integrity check failed: PayloadDescriptor.json");}
  string version=Core.Brand.Substring("KoreanAIR_AC8_ModPack_".Length);
  string tag="v"+version+"-b"+Core.ReleaseBuild;
  string url="https://github.com/"+UpdateCore.Repository+"/releases/download/"+tag+"/Payload.zip";
  if(m==null||m.schema!=1||m.version!=version||m.build!=Core.ReleaseBuild||m.tag!=tag||
     m.filename!="Payload.zip"||m.url!=url||m.size<128||m.size>MaximumPayload||
     m.sha256==null||!Regex.IsMatch(m.sha256,"^[a-f0-9]{64}$")||
     m.manifest_sha256==null||!Regex.IsMatch(m.manifest_sha256,"^[a-f0-9]{64}$"))
   throw new InvalidDataException("Payload integrity check failed: PayloadDescriptor.json");
  return m;
 }
 public static Stream OpenManifest(Assembly installer) {
  var descriptor=ReadDescriptor(installer);
  if(descriptor==null) {
   var legacy=installer.GetManifestResourceStream("Payload.zip");
   if(legacy==null)throw new FileNotFoundException("Missing payload file: PayloadDescriptor.json");
   return legacy;
  }
  var bytes=Resource(installer,"PayloadManifest.json",1024*1024);
  if(bytes==null)throw new FileNotFoundException("Missing payload file: PayloadManifest.json");
  if(Core.Hash(bytes)!=descriptor.manifest_sha256)throw new InvalidDataException("Payload integrity check failed: PayloadManifest.json");
  // Reuse Core's existing loader compatibility checks without opening the
  // full payload or contacting the network during UI construction/preflight.
  var result=new MemoryStream();
  using(var zip=new ZipArchive(result,ZipArchiveMode.Create,true)) {
   using(var entry=zip.CreateEntry("manifest.json",CompressionLevel.NoCompression).Open())entry.Write(bytes,0,bytes.Length);
  }
  result.Position=0;return result;
 }
 static Stream OpenVerified(string path,InstallerPayloadDescriptor descriptor) {
  var stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read);
  try {
   if(stream.Length!=descriptor.size)throw new InvalidDataException("Payload integrity check failed: Payload.zip");
   string hash;
   using(var sha=SHA256.Create())hash=BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();
   if(hash!=descriptor.sha256)throw new InvalidDataException("Payload integrity check failed: Payload.zip");
   stream.Position=0;return stream;
  } catch {stream.Dispose();throw;}
 }
 static void CommitCache(string partial,string cached,InstallerPayloadDescriptor descriptor) {
  using(var verified=OpenVerified(partial,descriptor)){}
  for(int attempt=0;attempt<2;++attempt) {
   if(File.Exists(cached)) {
    try {using(var verified=OpenVerified(cached,descriptor)){}return;}
    catch(InvalidDataException) { /* Replace only this release's damaged cache. */ }
    try {File.Replace(partial,cached,null);return;}
    catch(FileNotFoundException) {if(File.Exists(partial)&&!File.Exists(cached))continue;throw;}
   } else {
    try {File.Move(partial,cached);return;}
    catch(IOException) {if(File.Exists(partial)&&File.Exists(cached))continue;throw;}
   }
  }
  throw new IOException("Payload integrity check failed: Payload.zip");
 }
 static void CacheLocal(Stream source,string application,string relative,InstallerPayloadDescriptor descriptor,CancellationToken cancel) {
  string cached=Core.Safe(application,relative+descriptor.filename);
  if(File.Exists(cached)) {
   try {using(var verified=OpenVerified(cached,descriptor)){}return;}
   catch(InvalidDataException) { /* A verified sibling can repair our cache. */ }
  }
  Directory.CreateDirectory(Path.GetDirectoryName(cached));
  string partial=Core.Safe(application,relative+"download-"+Guid.NewGuid().ToString("N")+".part");
  try {
   using(var output=new FileStream(partial,FileMode.CreateNew,FileAccess.Write,FileShare.None)) {
    var buffer=new byte[65536];int read;
    while((read=source.Read(buffer,0,buffer.Length))>0){cancel.ThrowIfCancellationRequested();output.Write(buffer,0,read);}
   }
   cancel.ThrowIfCancellationRequested();CommitCache(partial,cached,descriptor);
  } finally {source.Position=0;try{if(File.Exists(partial))File.Delete(partial);}catch{}}
 }
 public static Stream OpenPayload(Assembly installer,Action<int> progress,CancellationToken cancel,bool allowDownload=true) {
  cancel.ThrowIfCancellationRequested();
  var descriptor=ReadDescriptor(installer);
  if(descriptor==null) {
   var legacy=installer.GetManifestResourceStream("Payload.zip");
   if(legacy==null)throw new FileNotFoundException("Missing payload file: PayloadDescriptor.json");
   return legacy;
  }
  string application=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),Core.Folder);
  string relative="Payloads/"+descriptor.sha256+"/";
  string sibling=Core.Safe(Path.GetDirectoryName(Path.GetFullPath(installer.Location)),descriptor.filename);
  if(File.Exists(sibling)) {
   var local=OpenVerified(sibling,descriptor);
   try {CacheLocal(local,application,relative,descriptor,cancel);return local;}
   catch {local.Dispose();throw;}
  }
  string cached=Core.Safe(application,relative+descriptor.filename);
  if(File.Exists(cached)) {
   try {return OpenVerified(cached,descriptor);}
   catch(InvalidDataException) {if(!allowDownload)throw;}
  }
  if(!allowDownload)throw new FileNotFoundException("Missing payload file: Payload.zip");
  Directory.CreateDirectory(Path.GetDirectoryName(cached));
  string partial=Core.Safe(application,relative+"download-"+Guid.NewGuid().ToString("N")+".part");
  try {
   using(var response=UpdateCore.Response(descriptor.url,30000))using(var source=response.GetResponseStream())
   using(var output=new FileStream(partial,FileMode.CreateNew,FileAccess.Write,FileShare.None)) {
    if(response.ContentLength>0&&response.ContentLength!=descriptor.size)throw new InvalidDataException("Payload integrity check failed: Payload.zip");
    var buffer=new byte[65536];long total=0;int read,last=-1;
    if(progress!=null)progress(0);
    while((read=source.Read(buffer,0,buffer.Length))>0) {
     cancel.ThrowIfCancellationRequested();total+=read;
     if(total>descriptor.size)throw new InvalidDataException("Payload integrity check failed: Payload.zip");
     output.Write(buffer,0,read);int percent=(int)(100*total/descriptor.size);
     if(percent!=last){last=percent;if(progress!=null)progress(percent);}
    }
    if(total!=descriptor.size)throw new InvalidDataException("Payload integrity check failed: Payload.zip");
   }
   cancel.ThrowIfCancellationRequested();CommitCache(partial,cached,descriptor);
   return OpenVerified(cached,descriptor);
  } finally {try{if(File.Exists(partial))File.Delete(partial);}catch{}}
 }
}
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
 internal static HttpWebResponse Response(string url,int timeout) {
  ServicePointManager.SecurityProtocol|=SecurityProtocolType.Tls12;
  var address=new Uri(url,UriKind.Absolute);
  for(int redirects=0;redirects<=5;++redirects) {
   string host=address.Host;
   if(address.Scheme!="https"||address.Port!=443||address.UserInfo.Length!=0||
      (host!="github.com"&&!host.EndsWith(".githubusercontent.com",StringComparison.OrdinalIgnoreCase)))
    throw new InvalidDataException("Unexpected update download location.");
   var request=(HttpWebRequest)WebRequest.Create(address);request.Timeout=timeout;request.ReadWriteTimeout=timeout;
   request.UserAgent="KoreanAIR-AC8-ModPack/"+Core.ReleaseBuild;request.CachePolicy=new RequestCachePolicy(RequestCacheLevel.NoCacheNoStore);
   request.AllowAutoRedirect=false;
   var response=(HttpWebResponse)request.GetResponse();int code=(int)response.StatusCode;
   if(code==301||code==302||code==303||code==307||code==308) {
    string location=response.Headers["Location"];response.Dispose();
    if(String.IsNullOrEmpty(location))throw new InvalidDataException("Unexpected update download location.");
    address=new Uri(address,location);continue;
   }
   if(code!=200){response.Dispose();throw new InvalidDataException("Unexpected update download location.");}
   return response;
  }
  throw new InvalidDataException("Unexpected update download location.");
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
   Core.VerifyGame(root);if(Core.Running(root))throw new Exception("Close ACE COMBAT 8 first.");
   if(Core.ReadState(root)==null)throw new Exception("Run the installer first.");
   using(var payload=ReleasePayload.OpenPayload(installer,null,CancellationToken.None))Core.UpdatePreservingState(root,payload,installer.Location);
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
