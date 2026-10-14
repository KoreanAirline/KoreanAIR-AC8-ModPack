using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Drawing;
using System.Windows.Forms;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Web.Script.Serialization;

public static class LiveFrameGenerationAudit {
 static List<string> checks=new List<string>();static List<string> errors=new List<string>();
 static Assembly assembly;static Type core;static string root;
 static void Check(bool value,string name){if(!value)throw new Exception(name);checks.Add(name);}
 static object Call(string name,params object[] args){return core.GetMethod(name).Invoke(null,args);}
 static Control Find(Control p,string name){if(p.Name==name)return p;foreach(Control c in p.Controls){var hit=Find(c,name);if(hit!=null)return hit;}return null;}
 static byte[] Bytes(string path){return File.Exists(path)?File.ReadAllBytes(path):null;}
 static bool Equal(byte[] a,byte[] b){return a==null?b==null:b!=null&&a.SequenceEqual(b);}
 static string Hash(string path){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(File.ReadAllBytes(path))).Replace("-","").ToLowerInvariant();}
 static object State(){return Call("ReadState",root);}
 static object Lease(object state){return state.GetType().GetField("frameGeneration").GetValue(state);}
 public static int Run(string[] args){
  root=Path.GetFullPath(args[0]);string output=Path.GetFullPath(args[1]);Directory.CreateDirectory(output);
  string engine=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"BANDAI NAMCO Entertainment/ACE COMBAT 8/Saved/Config/Windows/Engine.ini");
  string gus=Path.Combine(Path.GetDirectoryName(engine),"GameUserSettings.ini");
  byte[] gusBefore=Bytes(gus);bool success=false;string error=null;bool? oldManaged=null;byte[] engineBefore=null;FileAttributes attrs=FileAttributes.Normal;
  string exe=Path.Combine(root,"KoreanAIR_AC8_ModPack_1.4.exe");
  try{
   assembly=Assembly.LoadFrom(exe);core=assembly.GetType("KoreanAIR.Core",true);Check(!(bool)Call("Running",root),"game closed before settings writes");
   var oldLease=Lease(State());if(oldLease!=null){oldManaged=(bool)oldLease.GetType().GetField("enabled").GetValue(oldLease);Call("RestoreFrameGeneration",root);}
   engineBefore=Bytes(engine);if(engineBefore!=null)attrs=File.GetAttributes(engine);
   Application.EnableVisualStyles();
   using(var form=(Form)Activator.CreateInstance(assembly.GetType("Launcher"),new object[]{root})){
    form.GetType().GetField("Dialog",BindingFlags.Instance|BindingFlags.NonPublic).SetValue(form,new Action<string,MessageBoxIcon>((text,icon)=>{if(icon==MessageBoxIcon.Error)errors.Add(text);}));
    form.GetType().GetField("CheckUpdatesOnOpen").SetValue(form,false);form.ShowInTaskbar=false;form.StartPosition=FormStartPosition.Manual;form.Location=new Point(-32000,-32000);form.Show();Application.DoEvents();
    var tabs=(TabControl)Find(form,"settingsTabs");tabs.SelectedTab=tabs.TabPages["Frame generation"];
    var choice=(ComboBox)Find(form,"frameGenerationChoice");var save=(Button)Find(form,"saveFrameGeneration");var restore=(Button)Find(form,"restoreFrameGeneration");
    foreach(bool korean in new[]{false,true}){
     ((ComboBox)Find(form,"uiLanguage")).SelectedIndex=korean?1:0;Application.DoEvents();string lang=korean?"ko":"en";
     Check(save.Text==(korean?"프레임 생성 저장":"Save frame generation"),lang+" actual save label");
     choice.SelectedIndex=0;save.PerformClick();Application.DoEvents();Check(errors.Count==0&&(bool)Call("FrameGenerationRequested",root),lang+" actual ON save");
     Check(File.ReadAllText(engine).Contains("r.Streamline.InitializePlugin=1")&&File.ReadAllText(engine).Contains("r.Streamline.DLSSG.Enable=1"),lang+" startup keys written");
     using(var bitmap=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(bitmap,new Rectangle(0,0,form.Width,form.Height));bitmap.Save(Path.Combine(output,"frame_generation_"+lang+".png"));}
     choice.SelectedIndex=1;save.PerformClick();Application.DoEvents();Check(errors.Count==0&&!(bool)Call("FrameGenerationRequested",root),lang+" actual OFF save");
     restore.PerformClick();Application.DoEvents();Check(errors.Count==0&&Equal(engineBefore,Bytes(engine)),lang+" exact original Engine.ini restored");
     Check(engineBefore==null||File.GetAttributes(engine)==attrs,lang+" original attributes restored");Check(Equal(gusBefore,Bytes(gus)),lang+" all game menu settings preserved");
    }
   }
   success=true;
  }catch(Exception ex){error=ex.ToString();}
  finally{
   try{if(core!=null){Call("RestoreFrameGeneration",root);if(oldManaged.HasValue)Call("SetFrameGeneration",root,oldManaged.Value);}}catch(Exception ex){success=false;error=(error??"")+"\nRestoration: "+ex;}
  }
  bool finalOn=false;
  if(success&&args.Length>2&&args[2]=="--enable")try{Call("SetFrameGeneration",root,true);finalOn=(bool)Call("FrameGenerationRequested",root);Check(finalOn,"final authorized FG ON request saved");}catch(Exception ex){success=false;error=ex.ToString();}
  var report=new{passed=success,checks=checks,errors=errors,error=error,tested_launcher_sha256=Hash(exe),final_fg_request=finalOn?"on":"original",mission_piloted=false};
  File.WriteAllText(Path.Combine(output,"live_frame_generation.json"),new JavaScriptSerializer().Serialize(report));Console.WriteLine("Live FG checks="+checks.Count+" passed="+success);return success?0:1;
 }
}
