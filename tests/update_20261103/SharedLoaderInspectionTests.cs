using System;
using System.IO;
using KoreanAIR;
static class SharedLoaderInspectionTests {
 static void Check(bool condition,string name) {if(!condition)throw new Exception(name);Console.WriteLine("PASS: "+name);}
 static void Put(string root,string relative,byte[] bytes) {string p=Core.Safe(root,relative);Directory.CreateDirectory(Path.GetDirectoryName(p));File.WriteAllBytes(p,bytes);}
 static int Main(string[] args) {
  string root=Path.GetFullPath(args[0]),source=Path.GetFullPath(args[1]);Directory.CreateDirectory(root);
  Check(!SharedLoader.Inspect(root,true).Present,"missing loader does not opt in");
  Put(root,SharedLoader.Main,new byte[]{1,2,3});
  Check(!SharedLoader.Inspect(root,true).Recognized,"unknown DLL preserved and refused");
  Put(root,SharedLoader.Main,File.ReadAllBytes(Path.Combine(source,"ue4ss/Mods/IoStoreLoaderMod/dlls/main.dll")));
  Check(!SharedLoader.Inspect(root,true).RuntimeCompatible,"known loader without exact shared runtime refused");
  Put(root,"Game/Binaries/Win64/UE4SS/UE4SS.dll",File.ReadAllBytes(Path.Combine(source,"ue4ss/UE4SS.dll")));
  Put(root,"Game/Binaries/Win64/dwmapi.dll",File.ReadAllBytes(Path.Combine(source,"dwmapi.dll")));
  Check(!SharedLoader.Inspect(root,false).CanProvideCampaign,"known runtime cannot override disabled UE4SS mod");
  var accepted=SharedLoader.Inspect(root,true);
  Check(accepted.CanProvideCampaign&&accepted.Kind==SharedLoader.Provider,"exact loader and runtime recognized without modification");
  string order=SharedLoader.Root+"loadorder.txt";
  Put(root,order,System.Text.Encoding.UTF8.GetBytes("# keep\r\n+Falken_addon\r\n-KoreanAIRCampaign\r\n+KoreanAIRCampaign\r\n"));
  string before=Core.HashFile(Core.Safe(root,order));
  Check(!SharedLoader.Inspect(root,true).CanProvideCampaign,"first matching disabled entry wins; duplicate cannot bypass");
  Check(Core.HashFile(Core.Safe(root,order))==before,"inspection preserves external load order byte for byte");
  Put(root,order,System.Text.Encoding.UTF8.GetBytes("-Falken_addon\n+ koreanAIRcampaign \n"));
  Check(SharedLoader.Inspect(root,true).CanProvideCampaign,"case-insensitive enabled own entry preserves unrelated disabled mod");
  Put(root,order,System.Text.Encoding.UTF8.GetBytes("-KoreanAIRCampaignBackup\n+Falken_addon\n"));
  Check(SharedLoader.Inspect(root,true).CanProvideCampaign,"lookalike names cannot disable own unlisted folder");
  Put(root,order,new byte[262145]);bool rejected=false;
  try{SharedLoader.Inspect(root,true);}catch(IOException){rejected=true;}
  Check(rejected,"oversized load order fails without rewriting it");
  Put(root,order,new byte[0]);Put(root,"Game/Binaries/Win64/dwmapi.dll",new byte[]{4});
  Check(!SharedLoader.Inspect(root,true).CanProvideCampaign,"substituted shared proxy invalidates provider");
  return 0;
 }
}
