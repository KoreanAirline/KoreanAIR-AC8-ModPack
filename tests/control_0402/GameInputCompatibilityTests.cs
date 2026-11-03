using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Web.Script.Serialization;
using KoreanAIR;

public static class GameInputCompatibilityTests {
 sealed class Kind {
  public string Name; public Kind[] Children;
  public Kind(string name,params Kind[] children){Name=name;Children=children;}
 }
 sealed class Options {
  public string Up="LeftShift",Up2="None",Down="LeftControl",Down2="None",Combo="None",Combo2="None";
  public bool Wide,Duplicate,WrongType,Missing,WrongFlags,DeepType;
  public int SavedVersion=8;public string Class="/Script/Live.LiveSystemSaveGame";
 }
 static List<object> results=new List<object>();
 static int assertions;
 static void Need(bool value,string message){assertions++;if(!value)throw new Exception(message);}
 static void FString(BinaryWriter w,string text,bool wide){
  if(wide){w.Write(-(text.Length+1));w.Write(Encoding.Unicode.GetBytes(text+"\0"));}
  else{byte[] bytes=Encoding.UTF8.GetBytes(text+"\0");w.Write(bytes.Length);w.Write(bytes);}
 }
 static byte[] Bytes(Action<BinaryWriter> write){using(var memory=new MemoryStream()){using(var w=new BinaryWriter(memory,Encoding.UTF8,true))write(w);return memory.ToArray();}}
 static byte[] StringValue(string text,bool wide){return Bytes(delegate(BinaryWriter w){FString(w,text,wide);});}
 static Kind EnumKind(){return new Kind("EnumProperty",new Kind("EOptionsKeys",new Kind("/Script/Live")),new Kind("ByteProperty"));}
 static void Type(BinaryWriter w,Kind type,bool wide){FString(w,type.Name,wide);w.Write(type.Children.Length);foreach(var child in type.Children)Type(w,child,wide);}
 static void Property(BinaryWriter w,string name,Kind kind,byte[] value,bool wide,byte flags){FString(w,name,wide);Type(w,kind,wide);w.Write(value.Length);w.Write(flags);w.Write(value);}
 static void IntProperty(BinaryWriter w,string name,int value,bool wide){Property(w,name,new Kind("IntProperty"),BitConverter.GetBytes(value),wide,0);}
 static uint Crc(byte[] data){uint crc=0x41916ebdU^0xffffffffU;foreach(byte b in data){crc^=b;for(int bit=0;bit<8;bit++)crc=(crc>>1)^((crc&1)!=0?0xedb88320U:0U);}return crc^0xffffffffU;}
 static byte[] Save(Options options){
  byte[] packed=Bytes(delegate(BinaryWriter w){
   IntProperty(w,"Version",0,options.Wide);
   Kind controllerType=new Kind("StructProperty",new Kind("Key",new Kind("/Script/InputCore")));
   if(options.DeepType)for(int depth=0;depth<10;depth++)controllerType=new Kind("StructProperty",controllerType);
   Property(w,"YawLeftKey_Controller",controllerType,Bytes(delegate(BinaryWriter nested){Property(nested,"KeyName",new Kind("NameProperty"),StringValue("Gamepad_LeftShoulder",options.Wide),options.Wide,0);FString(nested,"None",options.Wide);}),options.Wide,0);
   string[] names={"ThrottleUpKey","ThrottleUpKey2","ThrottleDownKey","ThrottleDownKey2","ThrottleUpDownKey","ThrottleUpDownKey2"};
   string[] values={options.Up,options.Up2,options.Down,options.Down2,options.Combo,options.Combo2};
   for(int i=0;i<names.Length;i++){
    if(options.Missing&&i==5)continue;
    Kind kind=options.WrongType&&i==4?new Kind("StrProperty"):EnumKind();
    Property(w,names[i],kind,StringValue("EOptionsKeys::"+values[i],options.Wide),options.Wide,(byte)(options.WrongFlags&&i==4?8:0));
   }
   if(options.Duplicate)Property(w,"ThrottleUpDownKey",EnumKind(),StringValue("EOptionsKeys::LeftShift",options.Wide),options.Wide,0);
   Property(w,"bIsMouseEnable",new Kind("BoolProperty"),new byte[0],options.Wide,16);FString(w,"None",options.Wide);
   // Separate streams retain duplicate field names, as real System saves do.
   for(int i=1;i<8;i++){IntProperty(w,i==3||i==4?"ControlType":"ProbeField"+i,i,options.Wide);FString(w,"None",options.Wide);}
  });
  return Bytes(delegate(BinaryWriter w){
   w.Write(Encoding.ASCII.GetBytes("GVAS"));w.Write(3);w.Write(522);w.Write(1012);w.Write((ushort)5);w.Write((ushort)4);w.Write((ushort)3);w.Write(0);FString(w,"UE5",options.Wide);w.Write(3);w.Write(93);
   for(int i=0;i<93;i++){w.Write(i+1);w.Write(new byte[12]);w.Write(i);}
   FString(w,options.Class,options.Wide);w.Write((byte)0);
   IntProperty(w,"SavedVersion",options.SavedVersion,options.Wide);
   Property(w,"PackedData",new Kind("ArrayProperty",new Kind("ByteProperty")),Bytes(delegate(BinaryWriter p){p.Write(packed.Length);p.Write(packed);}),options.Wide,0);
   Property(w,"Checksum",new Kind("UInt32Property"),BitConverter.GetBytes(Crc(packed)),options.Wide,0);FString(w,"None",options.Wide);w.Write(0);
  });
 }
 static string Hash(byte[] bytes){using(var h=SHA256.Create())return BitConverter.ToString(h.ComputeHash(bytes)).Replace("-","").ToLowerInvariant();}
 static void Check(string name,Options options,bool known,bool conflict,string expectedKey){CheckBytes(name,Save(options),known,conflict,expectedKey);}
 static void CheckBytes(string name,byte[] bytes,bool known,bool conflict,string expectedKey){
  byte[] before=(byte[])bytes.Clone();var r=GameInputCompatibility.InspectBytes(bytes);
  Need(r!=null,name+": null result");Need(r.Known==known,name+": unexpected Known ("+r.Reason+")");Need(r.Conflict==conflict,name+": unexpected Conflict");
  if(expectedKey!=null)Need(r.SharedKey==expectedKey,name+": unexpected SharedKey "+r.SharedKey);
  Need(Hash(bytes)==Hash(before),name+": caller input changed");
  if(conflict){Need(r.Conflicts!=null&&r.Conflicts.Count>0,name+": no conflict records");Need(r.Conflicts[0].Actions.Length>=2,name+": action identities missing");Need(r.Conflicts[0].Fields.Length>=2,name+": field identities missing");}
  results.Add(new {test=name,passed=true,known=r.Known,conflict=r.Conflict,key=r.SharedKey});
 }
 static void SyntheticTests(string temporary){
  Check("none_combo_clear",new Options(),true,false,null);
  Check("primary_accelerate_duplicate",new Options{Combo="LeftShift"},true,true,"LeftShift");
  Check("primary_decelerate_duplicate",new Options{Combo="LeftControl"},true,true,"LeftControl");
  Check("primary_combo_secondary_accelerate",new Options{Up="W",Up2="LeftShift",Combo="LeftShift"},true,true,"LeftShift");
  Check("secondary_combo_primary_decelerate",new Options{Combo2="LeftControl"},true,true,"LeftControl");
  Check("secondary_combo_secondary_decelerate",new Options{Down2="X",Combo2="X"},true,true,"X");
  Check("unique_combo_retained",new Options{Combo="SpaceBar",Combo2="Tab"},true,false,null);
  Check("none_not_duplicate",new Options{Up="None",Up2="None",Down="None",Down2="None"},true,false,null);
  Check("up_down_shared_without_combo",new Options{Up="W",Down="W"},true,false,null);
  Check("utf16_header_names_and_values",new Options{Wide=true,Combo="LeftShift"},true,true,"LeftShift");
  Check("unknown_saved_version",new Options{SavedVersion=9,Combo="LeftShift"},false,false,null);
  Check("wrong_class",new Options{Class="/Script/Live.LiveCampaignSaveGame",Combo="LeftShift"},false,false,null);
  Check("duplicate_target_property",new Options{Duplicate=true,Combo="LeftShift"},false,false,null);
  Check("wrong_target_type",new Options{WrongType=true,Combo="LeftShift"},false,false,null);
  Check("missing_target_property",new Options{Missing=true,Combo="LeftShift"},false,false,null);
  Check("wrong_target_flags",new Options{WrongFlags=true,Combo="LeftShift"},false,false,null);
  Check("unknown_enum_value",new Options{Combo="NotARealGameKey"},false,false,null);
  Check("enum_num_sentinel",new Options{Combo="Num"},false,false,null);
  Check("bounded_nested_type_depth",new Options{DeepType=true,Combo="LeftShift"},false,false,null);
  byte[] valid=Save(new Options{Combo="LeftShift"});
  foreach(int n in new[]{0,3,27,100,valid.Length-1}){byte[] shortBytes=new byte[n];Buffer.BlockCopy(valid,0,shortBytes,0,n);CheckBytes("truncated_"+n,shortBytes,false,false,null);}
  byte[] bad=(byte[])valid.Clone();byte[] key=Encoding.UTF8.GetBytes("EOptionsKeys::LeftShift");int found=Find(bad,key);Need(found>=0,"fixture key missing");bad[found+key.Length-1]^=1;CheckBytes("crc_mismatch",bad,false,false,null);
  bad=(byte[])valid.Clone();bad[4]=4;CheckBytes("unknown_gvas_version",bad,false,false,null);
  bad=(byte[])valid.Clone();bad[12]=0xff;CheckBytes("unknown_package_version",bad,false,false,null);
  bad=(byte[])valid.Clone();bad[16]=6;CheckBytes("unknown_engine_version",bad,false,false,null);
  CheckBytes("over_limit_bytes",new byte[1024*1024+1],false,false,null);
  string path=Path.Combine(temporary,"System.sav");File.WriteAllBytes(path,valid);string sourceHash=Hash(File.ReadAllBytes(path));
  using(var shared=new FileStream(path,FileMode.Open,FileAccess.ReadWrite,FileShare.ReadWrite)){
   var r=GameInputCompatibility.Inspect(path);Need(r.Known&&r.Conflict,"shared_readwrite inspection failed: "+r.Reason);Need(r.SourceSha256==sourceHash,"source hash missing");
  }
  Need(Hash(File.ReadAllBytes(path))==sourceHash,"read-only file inspection changed input");results.Add(new{test="shared_readwrite_file",passed=true});
  DateTime modified=File.GetLastWriteTimeUtc(path);bool hookCalled=false;
  GameInputCompatibility.TestAfterSnapshot=delegate(string ignored){hookCalled=true;byte[] changed=(byte[])valid.Clone();changed[changed.Length-1]^=1;File.WriteAllBytes(path,changed);File.SetLastWriteTimeUtc(path,modified);};
  try{var r=GameInputCompatibility.Inspect(path);Need(hookCalled,"change hook was not invoked");Need(!r.Known&&!r.Conflict,"same-length change was not skipped");}
  finally{GameInputCompatibility.TestAfterSnapshot=null;}
  results.Add(new{test="concurrent_same_length_restored_timestamp",passed=true});
  var missing=GameInputCompatibility.Inspect(Path.Combine(temporary,"missing.sav"));Need(!missing.Known&&!missing.Conflict,"missing file should be unknown");results.Add(new{test="missing_file",passed=true});
  File.WriteAllBytes(path,new byte[1024*1024+1]);var oversized=GameInputCompatibility.Inspect(path);Need(!oversized.Known&&!oversized.Conflict,"oversized file should be unknown");results.Add(new{test="over_limit_file",passed=true});
 }
 static int Find(byte[] bytes,byte[] needle){for(int i=0;i<=bytes.Length-needle.Length;i++){int j=0;while(j<needle.Length&&bytes[i+j]==needle[j])j++;if(j==needle.Length)return i;}return -1;}
 static void RealFixture(string label,string path,bool expectedKnown,bool? expectedConflict){
  if(!File.Exists(path)){results.Add(new{test=label,skipped=true});return;}
  byte[] before=File.ReadAllBytes(path);var r=GameInputCompatibility.Inspect(path);Need(r.Known==expectedKnown,label+": unexpected schema recognition ("+r.Reason+")");if(expectedConflict.HasValue)Need(r.Conflict==expectedConflict.Value,label+": unexpected conflict result");Need(Hash(File.ReadAllBytes(path))==Hash(before),label+": fixture changed");
  results.Add(new{test=label,passed=true,known=r.Known,conflict=r.Conflict,key=r.SharedKey,sha256_before=Hash(before),sha256_after=Hash(File.ReadAllBytes(path)),bytes=before.Length});
 }
 public static int Main(string[] args){
  string temporary=Path.Combine(Path.GetTempPath(),"KoreanAIR_InputCompatibility_"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(temporary);int exit=0;string error=null;
  try{SyntheticTests(temporary);for(int i=0;i<args.Length;i++)RealFixture("real_fixture_"+i,args[i],i!=2,i==1?(bool?)false:null);}catch(Exception ex){exit=1;error=ex.GetType().Name+": "+ex.Message;}finally{try{Directory.Delete(temporary,true);}catch{}}
  Console.WriteLine(new JavaScriptSerializer().Serialize(new{passed=exit==0,assertions=assertions,tests=results,error=error,save_writes_by_detector=false,private_fixture_bytes_persisted=false}));return exit;
 }
}
