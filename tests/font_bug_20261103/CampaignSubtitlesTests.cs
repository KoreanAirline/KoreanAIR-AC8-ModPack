using System;
using System.IO;
using System.IO.Compression;
using System.Collections.Generic;
using System.Text;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Web.Script.Serialization;
using KoreanAIR;
class CampaignSubtitlesTests {
 static int checks;
 static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
 static byte[] B(string value){return Utf8.GetBytes(value);}
 static string Hash(byte[] bytes){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
 static void Check(bool value,string label){checks++;if(!value)throw new Exception("FAIL: "+label);}
 static void Refuse(Action action,string label){try{action();}catch(InvalidDataException){checks++;return;}throw new Exception("Did not reject: "+label);}
 static byte[] Gzip(string json){using(var stream=new MemoryStream()){using(var gzip=new GZipStream(stream,CompressionMode.Compress,true)){byte[] plain=B(json);gzip.Write(plain,0,plain.Length);}return stream.ToArray();}}
 static string Patch(string key,string en,string ko){return new JavaScriptSerializer().Serialize(new{schema=1,rows=new[]{new{key=key,en=en,ko=ko}}});}
 static void Main(string[] args){
  string root=args[0],folder=args[1];byte[] patch=File.ReadAllBytes(args[2]);var clock=Stopwatch.StartNew();
  string fingerprint=CampaignSubtitles.Fingerprint(root,patch);var result=CampaignSubtitles.Build(root,patch);
  Check(result.Fingerprint==fingerprint,"build/fingerprint use same current stock and patch");
  Check(result.Applied==33411&&result.Changed==30737&&result.Skipped==1,"actual current-stock row counts");
  string path=Path.Combine(folder,"csharp_current_stock_campaign_P.pak");File.WriteAllBytes(path,result.Pak);
  byte[] generatedDat=new byte[BitConverter.ToInt64(result.Pak,8)];Buffer.BlockCopy(result.Pak,53,generatedDat,0,generatedDat.Length);
  byte[] plain=CampaignSubtitles.InflateZlib(CampaignSubtitles.Crypt(generatedDat,generatedDat.Length+6),16*1024*1024);
  File.WriteAllBytes(Path.Combine(folder,"csharp_current_CP_G.bin"),plain);
  Check(CampaignSubtitles.SplitTable(plain).Count==46594,"all current strings retained");
  var english=new List<byte[]>{B("Current menu \ue123 {Value}"),B("Hello <A> {Name}"),B("Below")};
  var korean=new List<byte[]>{B("현재 메뉴 \ue123 {Value}"),B("안녕 <A> {Name}"),B("아래")};
  var keys=new List<CampaignSubtitles.KeyRecord>{new CampaignSubtitles.KeyRecord{Key="Menu",Index=0},new CampaignSubtitles.KeyRecord{Key="Msg_Greeting",Index=1},new CampaignSubtitles.KeyRecord{Key="Msg_Below",Index=2}};
  var rows=CampaignSubtitles.ParsePatch(Gzip(Patch("Msg_Greeting","Hello <A> {Name}","반가워 <A> {Name}")));
  var applied=CampaignSubtitles.Apply(english,korean,keys,rows);
  Check(applied.Applied==1&&applied.Changed==1&&Object.ReferenceEquals(applied.Values[0],korean[0])&&Object.ReferenceEquals(applied.Values[2],korean[2]),"untouched menu/control bytes retained by reference");
  Check(Utf8.GetString(applied.Values[1])=="반가워 <A> {Name}","unique stable key uses current index");
  var movedKeys=new List<CampaignSubtitles.KeyRecord>{new CampaignSubtitles.KeyRecord{Key="Msg_Greeting",Index=2}};
  var moved=CampaignSubtitles.Apply(new List<byte[]>{B("extra"),B("extra"),english[1]},korean,movedKeys,rows);
  Check(moved.Changed==1&&Utf8.GetString(moved.Values[2])==rows[0].Korean,"remapping uses new stable-key position");
  foreach(int mode in new[]{0,1,2,3,4}){
   var varied=new List<CampaignSubtitles.KeyRecord>(keys);var en=new List<byte[]>(english);
   if(mode==0)varied.RemoveAt(1);if(mode==1)varied.Add(new CampaignSubtitles.KeyRecord{Key="Msg_Greeting",Index=1});if(mode==2)varied.Add(new CampaignSubtitles.KeyRecord{Key="AliasedMenu",Index=1});if(mode==3)varied[1]=new CampaignSubtitles.KeyRecord{Key="Msg_Greeting",Index=500};if(mode==4)en[1]=B("Changed source");
   var skipped=CampaignSubtitles.Apply(en,korean,varied,rows);Check(skipped.Skipped==1&&skipped.Changed==0&&Object.ReferenceEquals(skipped.Values[1],korean[1]),"unsafe key/source mapping skips "+mode);
  }
  Refuse(()=>CampaignSubtitles.ParsePatch(Gzip(Patch("Menu","Hello","번역"))),"non-dialogue key");
  Refuse(()=>CampaignSubtitles.ParsePatch(Gzip(Patch("Msg_A","<A>","번역"))),"control token mismatch");
  Refuse(()=>CampaignSubtitles.ParsePatch(Gzip(Patch("Msg_A"," ","번역"))),"blank English");
  Refuse(()=>CampaignSubtitles.ParsePatch(Gzip("{\"schema\":2,\"rows\":[]}")),"unknown patch schema");
  Refuse(()=>CampaignSubtitles.ParsePatch(Gzip("{\"schema\":1,\"rows\":[{\"key\":\"Msg_A\",\"en\":\"x\",\"ko\":\"y\",\"id\":0}]}")),"source numeric index forbidden");
  Refuse(()=>CampaignSubtitles.ParsePatch(Gzip("{\"schema\":1,\"rows\":[{\"key\":\"Msg_A\",\"en\":\"x\",\"ko\":\"y\"},{\"key\":\"Msg_A\",\"en\":\"x\",\"ko\":\"z\"}]}")),"duplicate patch key");
  Refuse(()=>CampaignSubtitles.ParseKeys(new byte[]{255,255,255,127}),"oversized keymap count");
  Refuse(()=>CampaignSubtitles.SplitTable(B("no terminator")),"unterminated DAT");
  byte[] invalid=new byte[]{0x78,0x9c,1,0,0,0};Refuse(()=>CampaignSubtitles.InflateZlib(invalid,1),"invalid DAT wrapper/checksum");
  byte[] corrupt=(byte[])patch.Clone();corrupt[corrupt.Length-8]^=1;Refuse(()=>CampaignSubtitles.ParsePatch(corrupt),"gzip checksum corruption");
  byte[] oversized=(byte[])patch.Clone();Buffer.BlockCopy(BitConverter.GetBytes(0xffffffffu),0,oversized,oversized.Length-4,4);Refuse(()=>CampaignSubtitles.ParsePatch(oversized),"gzip declared size guard");
  byte[] trailing=new byte[patch.Length+1];Buffer.BlockCopy(patch,0,trailing,0,patch.Length-8);trailing[patch.Length-8]=0x4a;Buffer.BlockCopy(patch,patch.Length-8,trailing,patch.Length-7,8);Refuse(()=>CampaignSubtitles.ParsePatch(trailing),"trailing gzip deflate bytes");
  string fakeRoot=Path.Combine(folder,"fixture_current_stock_"+Guid.NewGuid().ToString("N")),fakePaks=Path.Combine(fakeRoot,"Game","Content","Paks");Directory.CreateDirectory(fakePaks);
  File.WriteAllBytes(Path.Combine(fakePaks,"pakchunk0-Windows.pak"),new byte[1]);
  File.WriteAllBytes(Path.Combine(fakePaks,"pakchunk10-Windows.pak"),new byte[1]);
  Refuse(()=>CampaignSubtitles.Fingerprint(fakeRoot,patch),"missing official archive refuses cached identity");
  File.WriteAllBytes(Path.Combine(fakePaks,"pakchunk20-Windows.pak"),new byte[1]);
  Refuse(()=>CampaignSubtitles.Fingerprint(fakeRoot,patch),"changed stock length refuses cached identity");
  Refuse(()=>CampaignSubtitles.Build(fakeRoot,patch),"changed stock fails build without stale output");
  File.WriteAllBytes(Path.Combine(fakePaks,"pakchunk30-Windows.pak"),new byte[1]);
  Refuse(()=>CampaignSubtitles.Fingerprint(fakeRoot,patch),"future official archive refuses cache");
  Refuse(()=>CampaignSubtitles.Fingerprint(root,new byte[4*1024*1024+1]),"compressed patch size bound");
  clock.Stop();var report=new{passed=true,checks=checks,elapsed_ms=clock.ElapsedMilliseconds,applied=result.Applied,changed=result.Changed,skipped=result.Skipped,current_strings=46594,plain_sha256=Hash(plain),pak_sha256=Hash(result.Pak),pak_bytes=result.Pak.Length,fingerprint=result.Fingerprint,game_installation_modified=false};
  File.WriteAllText(Path.Combine(folder,"csharp_current_stock_results.json"),new JavaScriptSerializer().Serialize(report),new UTF8Encoding(false));Console.WriteLine("PASS: "+checks+" current stock and synthetic dialogue overlay checks; "+clock.ElapsedMilliseconds+"ms.");
 }
}
