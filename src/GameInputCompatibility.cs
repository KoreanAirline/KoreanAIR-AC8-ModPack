using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace KoreanAIR {
// A bounded, read-only check of the game's saved throttle bindings. Unknown
// formats and changing files produce no conflict result. This class never
// changes a save, starts a process, or decides whether the game may launch.
public static class GameInputCompatibility {
 public sealed class BindingConflict {
  public string Key;
  public string[] Actions,Fields;
 }
 public sealed class Result {
  public bool Known {get; internal set;}
  public string Reason,SourceSha256;
  public readonly List<BindingConflict> Conflicts=new List<BindingConflict>();
  public bool Conflict {get{return Known&&Conflicts.Count>0;}}
  public string SharedKey {get{return Conflict?Conflicts[0].Key:null;}}
 }
 public static string SystemPath {get{return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"BANDAI NAMCO Entertainment","ACE COMBAT 8","Saved","SaveGames","System.sav");}}
 const int MaxBytes=1024*1024,MaxStringCharacters=4096,MaxProperties=512,MaxStreams=8;
 const uint ChecksumSeed=0x41916ebd;
 static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
 static readonly UnicodeEncoding Utf16=new UnicodeEncoding(false,false,true);
 static readonly uint[] CrcTable=MakeCrcTable();
 static readonly string[] KeyFields={"ThrottleUpKey","ThrottleUpKey2","ThrottleDownKey","ThrottleDownKey2","ThrottleUpDownKey","ThrottleUpDownKey2"};
 // Observed EOptionsKeys values in the supported game; Num is the enum's
 // count sentinel, not an assignable key. Unknown future values skip advice.
 static readonly HashSet<string> SupportedKeys=new HashSet<string>((
  "A A_AccentGrave Add Ampersand Apostrophe Asterix Atmark B BackSpace Backslash C C_Cedille CapsLock Caret Colon Comma D Decimal Delete Divide Dollar Down E E_AccentAigu E_AccentGrave Eight End Enter Equals Escape Exclamation F F1 F10 F11 F12 F2 F3 F4 F5 F6 F7 F8 F9 Five Four G H Home Hyphen I Insert J K L Left LeftAlt LeftBracket LeftCommand LeftControl LeftMouseButton LeftParantheses LeftShift M MiddleMouseButton MouseAxisLookAtX MouseAxisLookAtY MouseAxisStickX MouseAxisStickY MouseScrollDown MouseScrollUp MouseWheelAxis Multiply N Nine None NumLock NumPadEight NumPadFive NumPadFour NumPadNine NumPadOne NumPadSeven NumPadSix NumPadThree NumPadTwo NumPadZero O One P PageDown PageUp Pause Period Q Quote R Right RightAlt RightBracket RightCommand RightControl RightMouseButton RightParantheses RightShift S Scan0029 Scan0056 ScrollLock Section Semicolon Seven Six Slash SpaceBar Subtract T Tab Three ThumbMouseButton ThumbMouseButton2 Tilde Two U Underscore Up V W X Y Yen Z Zero"
 ).Split(' '),StringComparer.Ordinal);
#if GAME_INPUT_COMPATIBILITY_TEST
 internal static Action<string> TestAfterSnapshot;
#endif
 sealed class FormatError : Exception {internal FormatError(string message):base(message){}}
 static void Need(bool ok,string message){if(!ok)throw new FormatError(message);}
 static Result Unknown(string reason){return new Result{Known=false,Reason=reason};}
 static string Hash(byte[] bytes){using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
 static bool Same(byte[] a,byte[] b){if(a.Length!=b.Length)return false;int difference=0;for(int i=0;i<a.Length;i++)difference|=a[i]^b[i];return difference==0;}

 sealed class Snapshot {
  internal byte[] Bytes;internal long Length,WriteTicks,CreationTicks;
 }
 static Snapshot ReadShared(string path){
  var before=new FileInfo(path);before.Refresh();
  Need(before.Exists&&before.Length>0&&before.Length<=MaxBytes,"Save unavailable or too large.");
  long length=before.Length,write=before.LastWriteTimeUtc.Ticks,creation=before.CreationTimeUtc.Ticks;
  var bytes=new byte[(int)length];
  using(var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite|FileShare.Delete)){
   Need(file.Length==length,"Save changed during inspection.");
   int at=0;while(at<bytes.Length){int count=file.Read(bytes,at,bytes.Length-at);Need(count>0,"Save changed during inspection.");at+=count;}
   Need(file.ReadByte()==-1&&file.Length==length,"Save changed during inspection.");
  }
  var after=new FileInfo(path);after.Refresh();
  Need(after.Exists&&after.Length==length&&after.LastWriteTimeUtc.Ticks==write&&after.CreationTimeUtc.Ticks==creation,"Save changed during inspection.");
  return new Snapshot{Bytes=bytes,Length=length,WriteTicks=write,CreationTicks=creation};
 }
 public static Result Inspect(string path){
  try{
   if(String.IsNullOrEmpty(path))return Unknown("Save unavailable.");
   Snapshot first=ReadShared(path);
#if GAME_INPUT_COMPATIBILITY_TEST
   var afterSnapshot=TestAfterSnapshot;if(afterSnapshot!=null)afterSnapshot(path);
#endif
   Result result=Parse(first.Bytes);
   // Reopen the path as well as checking metadata: atomic replacement or a
   // same-length write during parsing must not yield stale advice, even if
   // the writer restores the original timestamps.
   Snapshot second=ReadShared(path);
   Need(first.Length==second.Length&&first.WriteTicks==second.WriteTicks&&first.CreationTicks==second.CreationTicks&&Same(first.Bytes,second.Bytes),"Save changed during inspection.");
   return result;
  }catch(FormatError ex){return Unknown(ex.Message);}
  catch(Exception){return Unknown("Save inspection unavailable.");}
 }
 public static Result InspectBytes(byte[] bytes){
  try{
   Need(bytes!=null&&bytes.Length>0&&bytes.Length<=MaxBytes,"Save unavailable or too large.");
   return Parse((byte[])bytes.Clone());
  }catch(FormatError ex){return Unknown(ex.Message);}
  catch(Exception){return Unknown("Unsupported or incomplete save.");}
 }

 sealed class Reader {
  internal readonly byte[] Data;internal readonly int End;internal int Position;
  internal Reader(byte[] data,int start,int end){Need(start>=0&&end>=start&&end<=data.Length,"Invalid save bounds.");Data=data;Position=start;End=end;}
  internal void Require(int count){Need(count>=0&&Position<=End-count,"Truncated save.");}
  internal byte Byte(){Require(1);return Data[Position++];}
  internal ushort U16(){Require(2);ushort value=(ushort)(Data[Position]|Data[Position+1]<<8);Position+=2;return value;}
  internal uint U32(){Require(4);uint value=(uint)Data[Position]|(uint)Data[Position+1]<<8|(uint)Data[Position+2]<<16|(uint)Data[Position+3]<<24;Position+=4;return value;}
  internal int I32(){return unchecked((int)U32());}
  internal void Skip(int count){Require(count);Position+=count;}
  internal string FString(){
   int count=I32();Need(count>=-MaxStringCharacters&&count<=MaxStringCharacters,"Unsupported string length.");
   if(count==0)return String.Empty;
   bool wide=count<0;int units=wide?-count:count,size=wide?units*2:units;Require(size);
   Need(Data[Position+size-1]==0&&(!wide||Data[Position+size-2]==0),"Unterminated save string.");
   string text=wide?Utf16.GetString(Data,Position,size-2):Utf8.GetString(Data,Position,size-1);
   Need(text.IndexOf('\0')<0,"Embedded save string terminator.");Position+=size;return text;
  }
 }
 sealed class TypeNode {internal string Name;internal readonly List<TypeNode> Parameters=new List<TypeNode>();}
 sealed class Property {internal string Name,Value;internal TypeNode Type;internal int Start,Size;internal byte Flags;}
 static TypeNode ReadType(Reader reader,int depth){
  Need(depth<8,"Save type nesting too deep.");
  var node=new TypeNode{Name=reader.FString()};Need(node.Name.Length>0&&node.Name.Length<=128,"Invalid property type.");
  int count=reader.I32();Need(count>=0&&count<=8,"Invalid property type parameters.");
  for(int i=0;i<count;i++)node.Parameters.Add(ReadType(reader,depth+1));return node;
 }
 static bool Leaf(TypeNode type,string name){return type.Name==name&&type.Parameters.Count==0;}
 static bool Scoped(TypeNode type,string name,string scope){return type.Name==name&&type.Parameters.Count==1&&Leaf(type.Parameters[0],scope);}
 static bool OptionsKey(TypeNode type){return type.Name=="EnumProperty"&&type.Parameters.Count==2&&Scoped(type.Parameters[0],"EOptionsKeys","/Script/Live")&&Leaf(type.Parameters[1],"ByteProperty");}
 static List<Property> ReadStream(Reader reader,int depth=0){
  Need(depth<8,"Save property nesting too deep.");
  var records=new List<Property>();var names=new HashSet<string>(StringComparer.Ordinal);
  for(int count=0;count<MaxProperties;count++){
   string name=reader.FString();if(name=="None")return records;
   Need(name.Length>0&&name.Length<=128&&names.Add(name),"Ambiguous property name.");
   TypeNode type=ReadType(reader,0);uint size=reader.U32();Need(size<=MaxBytes,"Invalid property size.");byte flags=reader.Byte();
   Need(flags==0||flags==8||flags==16,"Unsupported property flags.");reader.Require((int)size);
   var record=new Property{Name=name,Type=type,Start=reader.Position,Size=(int)size,Flags=flags};
   ValidateValue(reader.Data,record,depth);records.Add(record);reader.Skip(record.Size);
  }
  throw new FormatError("Too many save properties.");
 }
 static void ValidateValue(byte[] bytes,Property property,int depth){
  TypeNode type=property.Type;string kind=type.Name;int size=property.Size;
  var value=new Reader(bytes,property.Start,property.Start+size);
  if(kind=="BoolProperty"){Need(Leaf(type,kind)&&size==0&&(property.Flags==0||property.Flags==16),"Invalid boolean property.");return;}
  Need(property.Flags==0||kind=="StructProperty"&&property.Flags==8,"Unsupported value flags.");
  if(kind=="IntProperty"||kind=="UInt32Property"||kind=="FloatProperty")Need(Leaf(type,kind)&&size==4,"Invalid scalar property.");
  else if(kind=="UInt64Property"||kind=="Int64Property"||kind=="DoubleProperty")Need(Leaf(type,kind)&&size==8,"Invalid scalar property.");
  else if(kind=="ByteProperty")Need(Leaf(type,kind)&&size==1,"Invalid byte property.");
  else if(kind=="NameProperty"||kind=="StrProperty"){
   Need(Leaf(type,kind),"Invalid string property type.");property.Value=value.FString();Need(value.Position==value.End,"Invalid string property size.");
  }else if(kind=="EnumProperty"){
   Need(type.Parameters.Count==2&&type.Parameters[0].Parameters.Count==1&&type.Parameters[0].Parameters[0].Parameters.Count==0&&Leaf(type.Parameters[1],"ByteProperty"),"Invalid enum property type.");
   property.Value=value.FString();Need(value.Position==value.End,"Invalid enum property size.");
  }else if(kind=="ArrayProperty"){
   Need(type.Parameters.Count==1&&Leaf(type.Parameters[0],"ByteProperty")&&size>=4,"Unsupported save array.");int count=value.I32();Need(count==size-4,"Invalid save array size.");
  }else if(kind=="StructProperty"){
   // System keyboard/controller keys use the tagged FKey structure. Do not
   // treat unknown/native structs as known controls layouts.
   Need(type.Parameters.Count==1&&Scoped(type.Parameters[0],"Key","/Script/InputCore")&&property.Flags==0,"Unsupported save struct.");
   List<Property> fields=ReadStream(value,depth+1);Need(value.Position==value.End&&fields.Count==1&&fields[0].Name=="KeyName"&&Leaf(fields[0].Type,"NameProperty"),"Invalid key structure.");
  }else throw new FormatError("Unsupported property value type.");
 }
 static Property Required(List<Property> fields,string name){Property found=null;foreach(var field in fields)if(field.Name==name){Need(found==null,"Ambiguous controls schema.");found=field;}Need(found!=null,"Incomplete controls schema.");return found;}
 static int IntValue(byte[] bytes,Property field){return new Reader(bytes,field.Start,field.Start+field.Size).I32();}
 static bool KeyValue(string value){
  const string prefix="EOptionsKeys::";if(value==null||!value.StartsWith(prefix,StringComparison.Ordinal)||value.Length<=prefix.Length||value.Length>128)return false;
  return SupportedKeys.Contains(value.Substring(prefix.Length));
 }
 static Result Parse(byte[] bytes){
  Need(bytes.Length<=MaxBytes,"Save too large.");var reader=new Reader(bytes,0,bytes.Length);
  Need(reader.U32()==0x53415647&&reader.I32()==3&&reader.I32()==522&&reader.I32()==1012,"Unsupported save header.");
  Need(reader.U16()==5&&reader.U16()==4&&reader.U16()==3&&reader.U32()==0&&reader.FString()=="UE5","Unsupported save engine.");
  Need(reader.I32()==3,"Unsupported custom version format.");int custom=reader.I32();Need(custom==93,"Unsupported custom version table.");reader.Skip(custom*20);
  Need(reader.FString()=="/Script/Live.LiveSystemSaveGame"&&reader.Byte()==0,"Unsupported save class.");
  List<Property> outer=ReadStream(reader);Need(outer.Count==3&&outer[0].Name=="SavedVersion"&&outer[1].Name=="PackedData"&&outer[2].Name=="Checksum","Unsupported outer save schema.");
  Need(reader.End-reader.Position==4&&reader.U32()==0,"Invalid save terminator.");
  Property version=outer[0],packed=outer[1],checksum=outer[2];
  Need(Leaf(version.Type,"IntProperty")&&version.Size==4&&version.Flags==0&&IntValue(bytes,version)==8,"Unsupported system save version.");
  Need(packed.Type.Name=="ArrayProperty"&&packed.Type.Parameters.Count==1&&Leaf(packed.Type.Parameters[0],"ByteProperty")&&packed.Flags==0,"Unsupported packed data.");
  Need(Leaf(checksum.Type,"UInt32Property")&&checksum.Size==4&&checksum.Flags==0,"Unsupported save checksum.");
  uint actual=new Reader(bytes,checksum.Start,checksum.Start+4).U32();Need(actual==Crc(bytes,packed.Start+4,packed.Size-4),"Save checksum mismatch.");
  var payload=new Reader(bytes,packed.Start+4,packed.Start+packed.Size);List<Property> controls=null;int streams=0;
  while(payload.Position<payload.End){
   Need(streams<MaxStreams,"Too many save property streams.");List<Property> fields=ReadStream(payload);bool hasKey=false;
   foreach(var field in fields)foreach(string name in KeyFields)if(field.Name==name)hasKey=true;
   if(hasKey){Need(controls==null&&streams==0,"Ambiguous controls stream.");controls=fields;}streams++;
  }
  Need(payload.Position==payload.End&&streams==MaxStreams&&controls!=null,"Unsupported system data layout.");
  Property controlsVersion=Required(controls,"Version");Need(Leaf(controlsVersion.Type,"IntProperty")&&controlsVersion.Size==4&&controlsVersion.Flags==0&&IntValue(bytes,controlsVersion)==0,"Unsupported controls version.");
  var keys=new Property[KeyFields.Length];
  for(int i=0;i<keys.Length;i++){keys[i]=Required(controls,KeyFields[i]);Need(OptionsKey(keys[i].Type)&&keys[i].Flags==0&&KeyValue(keys[i].Value),"Unsupported throttle key.");}
  var result=new Result{Known=true,Reason="Verified system throttle settings.",SourceSha256=Hash(bytes)};
  for(int combo=4;combo<6;combo++){
   string key=keys[combo].Value;if(key=="EOptionsKeys::None")continue;
   var matchedFields=new List<string>();var actions=new List<string>();matchedFields.Add(keys[combo].Name);actions.Add("Accelerate + Decelerate");
   for(int direction=0;direction<4;direction++)if(keys[direction].Value==key){matchedFields.Add(keys[direction].Name);string action=direction<2?"Accelerate":"Decelerate";if(!actions.Contains(action))actions.Add(action);}
   if(matchedFields.Count==1)continue;
   BindingConflict existing=null;foreach(var conflict in result.Conflicts)if(conflict.Key==key.Substring("EOptionsKeys::".Length))existing=conflict;
   if(existing==null)result.Conflicts.Add(new BindingConflict{Key=key.Substring("EOptionsKeys::".Length),Actions=actions.ToArray(),Fields=matchedFields.ToArray()});
   else{var merged=new List<string>(existing.Fields);foreach(string name in matchedFields)if(!merged.Contains(name))merged.Add(name);existing.Fields=merged.ToArray();}
  }
  return result;
 }
 static uint[] MakeCrcTable(){var table=new uint[256];for(uint i=0;i<256;i++){uint value=i;for(int bit=0;bit<8;bit++)value=(value>>1)^((value&1)!=0?0xedb88320U:0U);table[i]=value;}return table;}
 static uint Crc(byte[] bytes,int start,int count){uint value=ChecksumSeed^0xffffffffU;for(int i=start;i<start+count;i++)value=(value>>8)^CrcTable[(value^bytes[i])&255];return value^0xffffffffU;}
}
}
