using System;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using KoreanAIR;

// Exercise the production provider by reflection. All resources are tiny
// synthetic fixtures; downloads, installation and game processes are excluded.
class ReleasePayloadAudit {
 static readonly List<object> checks=new List<object>();
 static string fixtures;
 static Type provider;
 static void Check(string name,bool ok){checks.Add(new{name=name,passed=ok});if(!ok)throw new Exception(name);}
 static object Call(string name,params object[] args){try{return provider.GetMethod(name,BindingFlags.Public|BindingFlags.Static).Invoke(null,args);}catch(TargetInvocationException ex){throw ex.InnerException;}}
 static Assembly Fixture(string name){return Assembly.LoadFile(Path.GetFullPath(Path.Combine(fixtures,name,name+".dll")));}
 static Stream Payload(Assembly a){return (Stream)Call("OpenPayload",a,null,CancellationToken.None,false);}
 static Stream Manifest(Assembly a){return (Stream)Call("OpenManifest",a);}
 static byte[] Bytes(Stream stream){using(var bytes=new MemoryStream()){stream.CopyTo(bytes);return bytes.ToArray();}}
 static void Reject(string name,Action operation){bool rejected=false;try{operation();}catch(Exception ex){rejected=!(ex is NullReferenceException)&&!(ex is MissingMethodException);}Check(name,rejected);}
 static void AssertManifest(Assembly a,byte[] expected,string label){
  using(var stream=Manifest(a)){
   Check(label+"_manifest_stream_readable",stream!=null&&stream.CanRead);
   var data=Bytes(stream);
   // The API may expose manifest JSON or a manifest-only ZIP for Core's
   // existing inspection overload. Both must carry the exact embedded bytes.
   if(data.Length>2&&data[0]==0x50&&data[1]==0x4b){using(var z=new ZipArchive(new MemoryStream(data),ZipArchiveMode.Read)){Check(label+"_manifest_zip_contains_manifest",z.GetEntry("manifest.json")!=null);if(label!="legacy")Check(label+"_manifest_zip_has_only_manifest",z.Entries.Count==1);using(var item=z.GetEntry("manifest.json").Open())data=Bytes(item);}}
   Check(label+"_manifest_exact_resource",data.SequenceEqual(expected));
  }
 }
 static void LocalCases(){
  var a=Fixture("valid");var expected=File.ReadAllBytes(Path.Combine(fixtures,"payload.expected.zip"));
  string local=Path.Combine(fixtures,"valid","Payload.zip");
  var descriptor=Call("ReadDescriptor",a);Check("descriptor_resource_read",descriptor!=null);
  var d=descriptor.GetType();Check("descriptor_fixed_filename",(string)d.GetField("filename").GetValue(descriptor)=="Payload.zip");
  Check("descriptor_current_build",(long)d.GetField("build").GetValue(descriptor)==Core.ReleaseBuild);
  using(var payload=Payload(a)){
   Check("local_stream_at_zero",payload!=null&&payload.CanRead&&payload.Position==0&&payload.Length==expected.Length);
   Check("verified_local_payload_exact",Bytes(payload).SequenceEqual(expected));
   using(var reader=File.OpenRead(local))Check("verified_local_allows_second_reader",reader.Length==expected.Length);
   bool locked=false;try{using(var writer=new FileStream(local,FileMode.Open,FileAccess.Write,FileShare.ReadWrite)){}}catch(IOException){locked=true;}
   Check("returned_file_lock_prevents_verify_reopen_race",locked);
   Check("locked_stream_still_reads_identical_bytes",payload.Seek(0,SeekOrigin.Begin)==0&&Bytes(payload).SequenceEqual(expected));
  }
  using(var writer=new FileStream(local,FileMode.Open,FileAccess.Write,FileShare.ReadWrite))Check("disposing_payload_releases_local_lock",writer.CanWrite);
  AssertManifest(a,File.ReadAllBytes(Path.Combine(fixtures,"manifest.expected.json")),"new");
  using(var cached=Payload(Fixture("cached")))Check("copied_installer_without_sibling_uses_verified_SHA_cache_offline",Bytes(cached).SequenceEqual(expected));
  string cacheHash=(string)d.GetField("sha256").GetValue(descriptor);
  string cachedPath=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),Core.Folder,"Payloads",cacheHash,"Payload.zip");
  Check("verified_sibling_warms_exact_SHA_cache",File.ReadAllBytes(cachedPath).SequenceEqual(expected));
  var damaged=(byte[])expected.Clone();damaged[damaged.Length-1]^=1;File.WriteAllBytes(cachedPath,damaged);
  Reject("damaged_cache_without_sibling_refused_offline",()=>{using(var p=Payload(Fixture("cached"))){} });
  Check("damaged_cache_refusal_does_not_overwrite_unverified_bytes",File.ReadAllBytes(cachedPath).SequenceEqual(damaged));
  using(var repaired=Payload(Fixture("valid")))Check("verified_sibling_repairs_own_damaged_SHA_cache",Bytes(repaired).SequenceEqual(expected));
  Check("repaired_cache_exact_verified_bytes",File.ReadAllBytes(cachedPath).SequenceEqual(expected));
  using(var repaired=Payload(Fixture("cached")))Check("copied_installer_reads_repaired_cache_offline",Bytes(repaired).SequenceEqual(expected));
  foreach(string kind in new[]{"tampered","truncated","oversized","missing"}){
   a=Fixture(kind);var elapsed=System.Diagnostics.Stopwatch.StartNew();
   Reject(kind+"_payload_rejected_without_download",()=>{using(var p=Payload(a)){} });
   Check(kind+"_offline_failure_prompt",elapsed.ElapsedMilliseconds<3000);
   AssertManifest(a,File.ReadAllBytes(Path.Combine(fixtures,"manifest.expected.json")),kind);
  }
  var missing=Call("ReadDescriptor",Fixture("missing"));var missingHash=(string)missing.GetType().GetField("sha256").GetValue(missing);
  string missingCache=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),Core.Folder,"Payloads",missingHash);
  Check("offline_missing_payload_does_not_create_cache_directory",!Directory.Exists(missingCache));
 }
 static void DescriptorCases(){
  foreach(string kind in new[]{"bad_schema","bad_version","bad_build","bad_tag","bad_filename","bad_path","bad_hash","bad_size","bad_manifest_hash","bad_url","foreign_repo","unpinned_url"})
   Reject(kind+"_descriptor_refused",()=>Call("ReadDescriptor",Fixture(kind)));
  Reject("mismatched_manifest_resource_refused",()=>{using(var p=Manifest(Fixture("mismatched_manifest"))){} });
 }
 static void LegacyCases(){
  var a=Fixture("legacy");var expected=File.ReadAllBytes(Path.Combine(fixtures,"payload.expected.zip"));
  Check("legacy_descriptor_absent_accepted",Call("ReadDescriptor",a)==null);
  using(var p=Payload(a))Check("legacy_embedded_payload_exact_without_sibling",Bytes(p).SequenceEqual(expected));
  AssertManifest(a,File.ReadAllBytes(Path.Combine(fixtures,"manifest.expected.json")),"legacy");
  Reject("no_resource_refuses_without_download",()=>{using(var p=Payload(Fixture("empty"))){} });
 }
 static int Main(string[] args){
  if(args.Length!=2)return 2;fixtures=Path.GetFullPath(args[0]);bool passed=false;string error=null;
  try{provider=typeof(Core).Assembly.GetType("KoreanAIR.ReleasePayload",true);LocalCases();DescriptorCases();LegacyCases();Check("network_stub_never_called",typeof(Core).Assembly.GetType("KoreanAIR.UpdateCore",true).GetField("NetworkAttempts").GetValue(null).Equals(0));passed=true;}catch(Exception ex){error=ex.ToString();}
  File.WriteAllText(args[1],new JavaScriptSerializer().Serialize(new{passed=passed,checks=checks,error=error,scope="Exact extracted ReleasePayload/descriptor/Core.Safe/Core.Hash source with minimal constants/serializer and a network stub that throws. Reflection and synthetic local/cache/resource fixtures only. Every OpenPayload call uses allowDownload=false; no installer/game invocation."}));
  Console.WriteLine("Release payload provider checks="+checks.Count+" passed="+passed+(error==null?"":"\n"+error));return passed?0:1;
 }
}
