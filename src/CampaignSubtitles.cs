using System;
using System.IO;
using System.IO.Compression;
using System.Text;
using System.Text.RegularExpressions;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Web.Script.Serialization;

namespace KoreanAIR {
// Per-launch, current-stock dialogue overlay. No archive or game file is written
// here. Unknown stock identities throw; callers must use original subtitles and
// remove this pack's previous generated overlay rather than mount stale bytes.
public static class CampaignSubtitles {
#if CAMPAIGN_SUBTITLES_TEST
 public static Func<string,byte[],Result> TestBuild;
 public static Func<string,byte[],string> TestFingerprint;
#endif
 public sealed class Result {
  public byte[] Pak;
  public string Status,Fingerprint;
  public int Applied,Changed,Skipped;
 }
 internal sealed class Row {internal string Key,English,Korean;}
 internal sealed class KeyRecord {internal string Key;internal int Index;}
 internal sealed class AppliedData {internal List<byte[]> Values;internal int Applied,Changed,Skipped;}
 sealed class Archive {
  internal string Name,IndexHash,FooterHash;
  internal long Length,IndexOffset;internal int IndexBytes;
  internal Archive(string name,long length,long offset,int count,string index,string footer){Name=name;Length=length;IndexOffset=offset;IndexBytes=count;IndexHash=index;FooterHash=footer;}
 }
 sealed class Entry {
  internal long Offset;internal int Size,Seed;internal string BodyHash,PlainHash,Sha1;
  internal Entry(long offset,int size,int seed,string body,string plain,string sha1){Offset=offset;Size=size;Seed=seed;BodyHash=body;PlainHash=plain;Sha1=sha1;}
 }
 const int MaxPlain=16*1024*1024,MaxPatch=4*1024*1024,MaxStrings=200000;
 static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
 static readonly Archive[] Archives={
  new Archive("pakchunk0-Windows.pak",10116334081L,10111561716L,1926608,"5f726576f7a4099420308d1d885399aec38dbe4bab070b85caa7f637eecb2ae4","8b100b9424058fb6b9c0bb6295707fef2508bb129f87a50ba9932238e583e4ce"),
  new Archive("pakchunk10-Windows.pak",11210597483L,11209865806L,702624,"fda44d8547c1899ee00345cceae9f3539fb80254c2ddf6475e9a407536c88097","0baba25226ffd6df7263455e75f6ecdc4646f5343e55f3a127856d67351bc6c2"),
  new Archive("pakchunk20-Windows.pak",21597956392L,21596562331L,1376224,"34d70ae576d179ed5f40673634f02fe720a5ffb99fd44cad3c382d4abe80a4d3","bee5031169e1623079ebb13be278ea0b5116c59fc761c712b9aba5ca168ff801")};
 static readonly Entry English=new Entry(35348480,483074,1,"6d95e30242309ad30534df8b529818e6377823144bbb4b07b6b7c4a3af57b857","1c96ab842dac35ec5ba019da343eaf1623f591938f55cb96b048c5bf78c9d6da","1258c2f6c22b581bf339d69ca254cbd456aeca8b");
 static readonly Entry Korean=new Entry(38029312,471360,6,"fe024865afda982afd3e048739757fc266a141d0a55a425f79b52af87fbc5c1e","6ecb5109c943fdc90bcefe5098025a8b8d0ab32aa5b7b0646012e383c827bc5f","aec15faed5c492676af4bc50cb922108c065145b");
 static readonly Entry Keys=new Entry(36319232,178361,0,"9f5cd813f2986d980903a9cd91a98f54b41334ec58ea045ccf9c268ce4a28535","ddcc1da29c648733744b1b1bf9e0d0c8d8c36c10ff36424174bef8324e933663","57bae5c0a8b5479828b80ac45bd3834529eef423");
 static void Need(bool condition,string message){if(!condition)throw new InvalidDataException(message);}
 static string Hex(byte[] bytes){return BitConverter.ToString(bytes).Replace("-","").ToLowerInvariant();}
 static string Hash(byte[] bytes){using(var h=SHA256.Create())return Hex(h.ComputeHash(bytes));}
 static byte[] Sha1(byte[] bytes){using(var h=SHA1.Create())return h.ComputeHash(bytes);}
 static bool Equal(byte[] a,byte[] b){if(a.Length!=b.Length)return false;int x=0;for(int i=0;i<a.Length;i++)x|=a[i]^b[i];return x==0;}
 static byte[] Read(FileStream stream,long position,int count){Need(position>=0&&count>=0&&position<=stream.Length-count,"Invalid stock read bounds.");stream.Position=position;byte[] bytes=new byte[count];int done=0;while(done<count){int n=stream.Read(bytes,done,count-done);Need(n>0,"Truncated stock archive.");done+=n;}return bytes;}
 static FileStream[] OpenStock(string root){
  string folder=Path.Combine(Path.GetFullPath(root),"Game","Content","Paks");
  var found=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
  foreach(string path in Directory.EnumerateFiles(folder,"pakchunk*-Windows.pak",SearchOption.TopDirectoryOnly)){
   string name=Path.GetFileName(path);if(!Regex.IsMatch(name,@"^pakchunk\d+-Windows\.pak$",RegexOptions.IgnoreCase))continue;
   Need(found.Add(name)&&found.Count<=3,"Unrecognized official archive set; using original subtitles.");
  }
  Need(found.Count==3,"Unrecognized official archive set; using original subtitles.");
  var streams=new FileStream[3];
  try {for(int i=0;i<3;i++){Need(found.Contains(Archives[i].Name),"Unrecognized official archive set; using original subtitles.");streams[i]=new FileStream(Path.Combine(folder,Archives[i].Name),FileMode.Open,FileAccess.Read,FileShare.Read);VerifyArchive(streams[i],Archives[i]);}return streams;}
  catch {foreach(var stream in streams)if(stream!=null)stream.Dispose();throw;}
 }
 static void VerifyArchive(FileStream stream,Archive spec){
  Need(stream.Length==spec.Length,"Stock archive changed; using original subtitles.");
  byte[] footer=Read(stream,stream.Length-512,512);
  Need(Hash(footer)==spec.FooterHash,"Stock archive footer changed; using original subtitles.");
  int at=-1;for(int i=0;i<=footer.Length-44;i++)if(BitConverter.ToUInt32(footer,i)==0x5a6f12e1)at=i;
  Need(at>=17&&BitConverter.ToInt32(footer,at+4)==11,"Unsupported stock archive format.");
  long offset=BitConverter.ToInt64(footer,at+8),size=BitConverter.ToInt64(footer,at+16);
  Need(offset==spec.IndexOffset&&size==spec.IndexBytes&&size>0&&size<=32*1024*1024&&offset<=stream.Length-221-size,"Invalid stock archive index.");
  Need(Hash(Read(stream,offset,(int)size))==spec.IndexHash,"Stock archive index changed; using original subtitles.");
 }
 static void Close(FileStream[] streams){foreach(var stream in streams)stream.Dispose();}
 static string Identity(byte[] patch){
  Need(patch!=null&&patch.Length>18&&patch.Length<=MaxPatch,"Invalid campaign dialogue patch size.");
  var text=new StringBuilder("current-stock-dialogue-v1|").Append(Hash(patch));foreach(var a in Archives)text.Append('|').Append(a.Name).Append('|').Append(a.IndexHash).Append('|').Append(a.FooterHash);return Hash(Utf8.GetBytes(text.ToString()));
 }
 public static string Fingerprint(string root,byte[] patchGzip){
#if CAMPAIGN_SUBTITLES_TEST
  if(TestFingerprint!=null)return TestFingerprint(root,patchGzip);
#endif
  string value=Identity(patchGzip);var files=OpenStock(root);try{return value;}finally{Close(files);}}
 public static Result Build(string root,byte[] patchGzip){
#if CAMPAIGN_SUBTITLES_TEST
  if(TestBuild!=null)return TestBuild(root,patchGzip);
#endif
  string fingerprint=Identity(patchGzip);var rows=ParsePatch(patchGzip);var files=OpenStock(root);
  try {
   var english=SplitTable(ReadDat(files[0],English));var korean=SplitTable(ReadDat(files[0],Korean));var keys=ParseKeys(ReadDat(files[0],Keys));
   Need(english.Count==46594&&korean.Count==46594&&keys.Count==44746,"Current stock table identity differs.");
   var applied=Apply(english,korean,keys,rows);byte[] dat=EncodeDat(applied.Values);byte[] packed=Pack(dat);
   return new Result{Pak=packed,Fingerprint=fingerprint,Applied=applied.Applied,Changed=applied.Changed,Skipped=applied.Skipped,Status="Current stock subtitles with campaign dialogue translation ("+applied.Applied+" applied, "+applied.Skipped+" source changes preserved)."};
  }finally{Close(files);}
 }
 static byte[] ReadDat(FileStream stream,Entry expected){
  byte[] header=Read(stream,expected.Offset,53);
  Need(BitConverter.ToInt64(header,0)==0&&BitConverter.ToInt64(header,8)==expected.Size&&BitConverter.ToInt64(header,16)==expected.Size&&BitConverter.ToUInt32(header,24)==0,"Stock DAT metadata changed.");
  for(int i=48;i<53;i++)Need(header[i]==0,"Stock DAT compression/encryption changed.");
  byte[] checksum=new byte[20];Buffer.BlockCopy(header,28,checksum,0,20);Need(Hex(checksum)==expected.Sha1,"Stock DAT entry identity changed.");
  byte[] body=Read(stream,expected.Offset+53,expected.Size);Need(Hash(body)==expected.BodyHash&&Equal(Sha1(body),checksum),"Stock DAT bytes changed.");
  byte[] plain=InflateZlib(Crypt(body,body.Length+expected.Seed),MaxPlain);Need(Hash(plain)==expected.PlainHash,"Stock DAT plaintext changed.");return plain;
 }
 internal static byte[] Crypt(byte[] bytes,int seed){byte[] result=new byte[bytes.Length];int a=0,b=seed&255;for(int i=0;i<bytes.Length;i++){a=(((~((a*8)^a)>>7)&1)|(a*2))&255;b=(b*5+1)&255;result[i]=(byte)(bytes[i]^((a+b)&255));}return result;}
 static uint Adler(byte[] bytes){uint a=1,b=0;foreach(byte value in bytes){a=(a+value)%65521;b=(b+a)%65521;}return(b<<16)|a;}
 static uint Crc(byte[] bytes){uint crc=0xffffffff;foreach(byte value in bytes){crc^=value;for(int i=0;i<8;i++)crc=(crc>>1)^((crc&1)!=0?0xedb88320u:0);}return~crc;}
 // Prevent DeflateStream's input read-ahead from hiding trailing bytes. These
 // bounded streams are decoded only while building/caching, never during play.
 sealed class ExactDeflateInput:MemoryStream {
  internal ExactDeflateInput(byte[] data,int offset,int count):base(data,offset,count,false){}
  public override int Read(byte[] buffer,int offset,int count){return base.Read(buffer,offset,Math.Min(count,1));}
 }
 static byte[] InflateRaw(byte[] bytes,int offset,int count,int limit){
  Need(limit>0&&limit<=MaxPlain&&offset>=0&&count>0&&offset<=bytes.Length-count,"Invalid compressed data bounds.");
  using(var input=new ExactDeflateInput(bytes,offset,count))using(var inflater=new DeflateStream(input,CompressionMode.Decompress))using(var output=new MemoryStream()){
   byte[] buffer=new byte[8192];for(;;){int n=inflater.Read(buffer,0,buffer.Length);if(n==0)break;Need(output.Length+n<=limit,"Decompressed data exceeds limit.");output.Write(buffer,0,n);}Need(input.Position==input.Length,"Trailing compressed data is not allowed.");return output.ToArray();
  }
 }
 internal static byte[] InflateZlib(byte[] bytes,int limit){
  Need(bytes!=null&&bytes.Length>=6&&(bytes[0]&15)==8&&(bytes[0]>>4)<=7&&((bytes[0]<<8)|bytes[1])%31==0&&(bytes[1]&32)==0,"Invalid DAT zlib wrapper.");
  byte[] plain=InflateRaw(bytes,2,bytes.Length-6,limit);uint expected=((uint)bytes[bytes.Length-4]<<24)|((uint)bytes[bytes.Length-3]<<16)|((uint)bytes[bytes.Length-2]<<8)|bytes[bytes.Length-1];Need(Adler(plain)==expected,"DAT Adler-32 mismatch.");return plain;
 }
 static byte[] InflatePatch(byte[] bytes){
  Need(bytes!=null&&bytes.Length>18&&bytes.Length<=MaxPatch&&bytes[0]==31&&bytes[1]==139&&bytes[2]==8&&bytes[3]==0,"Invalid campaign patch gzip wrapper.");
  uint size=BitConverter.ToUInt32(bytes,bytes.Length-4);Need(size>0&&size<=MaxPlain,"Campaign patch expands beyond limit.");byte[] plain=InflateRaw(bytes,10,bytes.Length-18,MaxPlain);
  Need(plain.Length==size&&Crc(plain)==BitConverter.ToUInt32(bytes,bytes.Length-8),"Campaign patch gzip checksum mismatch.");return plain;
 }
 internal static List<Row> ParsePatch(byte[] gzip){
  string text=Utf8.GetString(InflatePatch(gzip));var serializer=new JavaScriptSerializer{MaxJsonLength=MaxPlain,RecursionLimit=16};var root=serializer.DeserializeObject(text)as Dictionary<string,object>;
  Need(root!=null&&root.Count==2&&root.ContainsKey("schema")&&root["schema"]is int&&(int)root["schema"]==1&&root.ContainsKey("rows"),"Invalid campaign patch schema.");
  var values=root["rows"]as object[];Need(values!=null&&values.Length>0&&values.Length<=40000,"Invalid dialogue row count.");var result=new List<Row>();var keys=new HashSet<string>(StringComparer.Ordinal);
  foreach(var value in values){var row=value as Dictionary<string,object>;Need(row!=null&&row.Count==3&&row.ContainsKey("key")&&row.ContainsKey("en")&&row.ContainsKey("ko"),"Invalid dialogue row schema.");
   var key=row["key"]as string;var en=row["en"]as string;var ko=row["ko"]as string;
   Need(!String.IsNullOrWhiteSpace(key)&&key.Length<=10000&&key.IndexOf('\0')<0&&keys.Add(key)&&Regex.IsMatch(key,@"^(Msg_|v\d+_|Vo_|BattleSituationExplanation_Subtitle_)"),"Invalid or duplicate dialogue key.");
   Need(!String.IsNullOrWhiteSpace(en)&&!String.IsNullOrWhiteSpace(ko)&&en.Length<=65536&&ko.Length<=65536&&en.IndexOf('\0')<0&&ko.IndexOf('\0')<0,"Invalid dialogue text.");
   Utf8.GetBytes(key);Utf8.GetBytes(en);Utf8.GetBytes(ko);Need(Controls(en)==Controls(ko),"Dialogue control tokens changed.");result.Add(new Row{Key=key,English=en,Korean=ko});
  }return result;
 }
 static string Controls(string text){var list=new List<string>();foreach(Match token in Regex.Matches(text,@"<[^<>\n]+>|</>|\{[^{}\n]+\}"))list.Add(token.Value);for(int i=0;i<text.Length;i++){int value=Char.ConvertToUtf32(text,i);if(value>65535)i++;if((value>=0xe000&&value<=0xf8ff)||(value>=0xf0000&&value<=0xffffd)||(value>=0x100000&&value<=0x10fffd))list.Add(Char.ConvertFromUtf32(value));}list.Sort(StringComparer.Ordinal);return String.Join("\0",list.ToArray());}
 internal static List<byte[]> SplitTable(byte[] plain){
  Need(plain!=null&&plain.Length>0&&plain.Length<=MaxPlain&&plain[plain.Length-1]==0,"Invalid DAT string table.");var result=new List<byte[]>();int start=0;
  for(int i=0;i<plain.Length;i++)if(plain[i]==0){byte[] value=new byte[i-start];Buffer.BlockCopy(plain,start,value,0,value.Length);Utf8.GetString(value);result.Add(value);Need(result.Count<=MaxStrings,"Too many DAT strings.");start=i+1;}return result;
 }
 sealed class KeyReader {
  readonly byte[] bytes;int position,nodes;internal readonly List<KeyRecord> Result=new List<KeyRecord>();
  internal KeyReader(byte[] data){Need(data!=null&&data.Length>0&&data.Length<=MaxPlain,"Invalid keymap size.");bytes=data;}
  int Int(){Need(position<=bytes.Length-4,"Truncated keymap integer.");int value=BitConverter.ToInt32(bytes,position);position+=4;return value;}
  void Nodes(int count,string prefix,int depth){Need(count>=0&&count<=100000&&depth<=100,"Invalid keymap trie bounds.");for(int i=0;i<count;i++){Need(++nodes<=200000,"Keymap node limit exceeded.");int size=Int();Need(size>=0&&size<=10000&&position<=bytes.Length-size,"Invalid keymap prefix.");string key=prefix+Utf8.GetString(bytes,position,size);position+=size;Need(key.Length<=10000,"Keymap key exceeds limit.");int index=Int(),children=Int();Need(index>=-1,"Invalid keymap index.");if(index>=0)Result.Add(new KeyRecord{Key=key,Index=index});Nodes(children,key,depth+1);}}
  internal List<KeyRecord> Parse(){Nodes(Int(),"",0);Need(position==bytes.Length,"Unconsumed keymap bytes.");return Result;}
 }
 internal static List<KeyRecord> ParseKeys(byte[] plain){return new KeyReader(plain).Parse();}
 internal static AppliedData Apply(List<byte[]> english,List<byte[]> korean,List<KeyRecord> keys,List<Row> rows){
  Need(english!=null&&korean!=null&&english.Count==korean.Count&&korean.Count>0&&korean.Count<=MaxStrings,"Current table lengths differ.");
  var byKey=new Dictionary<string,List<int>>(StringComparer.Ordinal);var indexCounts=new Dictionary<int,int>();
  foreach(var record in keys){List<int> list;if(!byKey.TryGetValue(record.Key,out list)){list=new List<int>();byKey.Add(record.Key,list);}list.Add(record.Index);int count;indexCounts.TryGetValue(record.Index,out count);indexCounts[record.Index]=count+1;}
  var result=new AppliedData{Values=new List<byte[]>(korean)};
  foreach(var row in rows){List<int> list;int index;if(!byKey.TryGetValue(row.Key,out list)||list.Count!=1||(index=list[0])<0||index>=korean.Count||indexCounts[index]!=1||!Equal(english[index],Utf8.GetBytes(row.English))){result.Skipped++;continue;}
   byte[] replacement=Utf8.GetBytes(row.Korean);result.Applied++;if(!Equal(result.Values[index],replacement)){result.Values[index]=replacement;result.Changed++;}
  }return result;
 }
 internal static byte[] EncodeDat(List<byte[]> values){
  using(var plain=new MemoryStream()){foreach(var value in values){Need(plain.Length+value.Length+1<=MaxPlain,"Generated DAT exceeds limit.");Utf8.GetString(value);foreach(byte b in value)Need(b!=0,"String contains NUL.");plain.Write(value,0,value.Length);plain.WriteByte(0);}byte[] data=plain.ToArray();using(var zlib=new MemoryStream()){zlib.WriteByte(0x78);zlib.WriteByte(0x9c);using(var raw=new MemoryStream()){using(var compressor=new DeflateStream(raw,CompressionMode.Compress,true))compressor.Write(data,0,data.Length);byte[] compressed=raw.ToArray();zlib.Write(compressed,0,compressed.Length);}uint adler=Adler(data);zlib.WriteByte((byte)(adler>>24));zlib.WriteByte((byte)(adler>>16));zlib.WriteByte((byte)(adler>>8));zlib.WriteByte((byte)adler);byte[] packed=zlib.ToArray();Need(Equal(InflateZlib(packed,MaxPlain),data),"Generated DAT round trip differs.");return Crypt(packed,packed.Length+6);}}
 }
 static void FString(BinaryWriter writer,string text){byte[] bytes=Utf8.GetBytes(text);writer.Write(bytes.Length+1);writer.Write(bytes);writer.Write((byte)0);}
 static void PakEntry(BinaryWriter writer,long offset,byte[] dat){writer.Write(offset);writer.Write((long)dat.Length);writer.Write((long)dat.Length);writer.Write(0u);writer.Write(Sha1(dat));writer.Write((byte)0);writer.Write(0u);}
 internal static byte[] Pack(byte[] dat){
  Need(dat!=null&&dat.Length>0&&dat.Length<=4*1024*1024,"Invalid overlay DAT size.");string[] paths={"Game/Content/Localization/GameData/CP_G.dat","Live/Content/Localization/GameData/CP_G.dat"};
  using(var body=new MemoryStream())using(var writer=new BinaryWriter(body)){long[] offsets=new long[2];for(int i=0;i<2;i++){offsets[i]=body.Length;PakEntry(writer,0,dat);writer.Write(dat);}byte[] index;
   using(var stream=new MemoryStream())using(var iw=new BinaryWriter(stream)){FString(iw,"../../../");iw.Write(2);for(int i=0;i<2;i++){FString(iw,paths[i]);PakEntry(iw,offsets[i],dat);}index=stream.ToArray();}
   long at=body.Length;writer.Write(index);writer.Write(new byte[17]);writer.Write(0x5a6f12e1u);writer.Write(8);writer.Write(at);writer.Write((long)index.Length);writer.Write(Sha1(index));writer.Write(new byte[160]);Need(body.Length<=8*1024*1024,"Generated overlay exceeds limit.");return body.ToArray();
  }
 }
}
}
