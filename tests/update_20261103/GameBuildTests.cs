using System;using System.IO;using KoreanAIR;
class GameBuildTests {
 static int count;
 static void Check(bool ok,string what){count++;if(!ok)throw new Exception(what);}
 static void Main(string[] args){
  string root=Path.Combine(Path.GetTempPath(),"ac8build_"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(Path.Combine(root,"Game/Binaries/Win64"));
  File.WriteAllBytes(Path.Combine(root,"start_protected_game.exe"),new byte[0]);string path=Path.Combine(root,"Game/Binaries/Win64/AceCombat8.exe");
  foreach(var row in new[]{new uint[]{0x6ad2d0a7,0x215a2000,1},new uint[]{0x6aa0e27d,0x2195a000,0},new uint[]{0x6ad2d0a7,0x2195a000,0},new uint[]{0x6aa0e27d,0x215a2000,0},new uint[]{0,0,0}}){
   var bytes=new byte[512];using(var w=new BinaryWriter(new MemoryStream(bytes))){w.Write((ushort)0x5a4d);w.BaseStream.Position=0x3c;w.Write(128);w.BaseStream.Position=128;w.Write(0x4550);w.Write((ushort)0x8664);w.BaseStream.Position=152;w.Write((ushort)0x20b);w.BaseStream.Position=136;w.Write(row[0]);w.BaseStream.Position=208;w.Write(row[1]);}File.WriteAllBytes(path,bytes);
   bool accepted=true;try{Core.VerifyGame(root);}catch{accepted=false;}Check(accepted==(row[1]>=0x1000),"valid future game build is not blocked");Check(Core.IsTestedGame(root)==(row[2]!=0),"separate tested-build advisory");Check(Directory.GetFiles(root,"*",SearchOption.AllDirectories).Length==2,"read-only admission");
  }
  Core.VerifyGame(args[0]);Check(true,"current actual updated executable accepted");Console.WriteLine("PASS game build admission: "+count+" checks; valid unknown versions allowed with separate advisory; actual updated EXE accepted; no installed files changed.");
 }
}
