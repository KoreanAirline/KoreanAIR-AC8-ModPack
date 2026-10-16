using System;
using System.IO;
using System.Linq;
using System.Drawing;
using System.Reflection;
using System.Globalization;
using System.Collections.Generic;
using System.Windows.Forms;
using KoreanAIR;

// Exercise the production launcher against settings-only fixtures.
public static class SideButtonUiAudit {
 static readonly string[] actions={"free_look","hud_toggle","steering_toggle","recenter","reload","zoom"};
 static readonly int[] defaults={18,118,119,120,121,2};
 static readonly List<string> checks=new List<string>();
 static readonly BindingFlags hidden=BindingFlags.Instance|BindingFlags.NonPublic;
 static string destination,fixture,config;
 static void Check(bool passed,string name){if(!passed)throw new Exception(name);checks.Add(name);}
 static Control Find(Control c,string name){if(c.Name==name)return c;foreach(Control child in c.Controls){var found=Find(child,name);if(found!=null)return found;}return null;}
 static ComboBox Box(Form f,string action){return (ComboBox)Find(f,"key_"+action);}
 static int Code(Form f,string action){return ((ModKey)Box(f,action).SelectedItem).Code;}
 static void Choose(Form f,string action,int code){var box=Box(f,action);box.SelectedItem=box.Items.Cast<ModKey>().Single(x=>x.Code==code);}
 static void Reset(Form f){for(int i=0;i<actions.Length;i++)Choose(f,actions[i],defaults[i]);}
 static void Language(Form f,string language){((UiLanguage)typeof(Launcher).GetField("ui",hidden).GetValue(f)).Change(language,false);f.PerformLayout();Application.DoEvents();}
 static Launcher Create(List<string> dialogs){
  var form=new Launcher(fixture);form.CheckUpdatesOnOpen=false;form.Dialog=(text,icon)=>dialogs.Add(text);form.HotkeyMouseButtons=()=>MouseButtons.None;form.ShowInTaskbar=false;form.StartPosition=FormStartPosition.Manual;form.Location=new Point(-32000,-32000);form.Show();
  var tabs=(TabControl)Find(form,"settingsTabs");tabs.SelectedTab=tabs.TabPages.Cast<TabPage>().Single(x=>x.Name=="Controls");Language(form,"en");return form;
 }
 static void Capture(Form owner,string action,MouseButtons button){
  bool interacted=false;Exception failure=null;
  using(var timer=new Timer{Interval=30}){
   timer.Tick+=(s,e)=>{var modal=Application.OpenForms.Cast<Form>().SingleOrDefault(x=>x!=owner);if(modal==null)return;timer.Stop();try{var hint=modal.Controls.OfType<Label>().Single();var down=typeof(Control).GetMethod("OnMouseDown",hidden);int previous=Code(owner,action);
     down.Invoke(hint,new object[]{new MouseEventArgs(MouseButtons.Left,1,25,25,0)});Check(modal.DialogResult==DialogResult.None&&Code(owner,action)==previous,action+" opening/left click is ignored");
     if(action!="zoom"){down.Invoke(hint,new object[]{new MouseEventArgs(MouseButtons.Right,1,25,25,0)});Check(modal.DialogResult==DialogResult.None&&Code(owner,action)==previous,action+" keeps right mouse reserved");}
     down.Invoke(hint,new object[]{new MouseEventArgs(button,1,25,25,0)});Check(Code(owner,action)==ModKey.MouseCode(button),action+" mouse-down event selects "+button+"; actual "+Code(owner,action));interacted=true;
    }catch(Exception ex){failure=ex;modal.DialogResult=DialogResult.Cancel;}
   };
   timer.Start();((Button)Find(owner,"capture_"+action)).PerformClick();
  }
  if(failure!=null)throw new Exception(action+" modal capture callback failed",failure);Check(interacted,action+" modal capture interaction completed "+button);
 }
 static void CaptureCancel(Form owner,string action){
  using(var timer=new Timer{Interval=30}){timer.Tick+=(s,e)=>{var modal=Application.OpenForms.Cast<Form>().SingleOrDefault(x=>x!=owner);if(modal==null)return;timer.Stop();typeof(Control).GetMethod("OnKeyDown",hidden).Invoke(modal,new object[]{new KeyEventArgs(Keys.Escape)});};timer.Start();((Button)Find(owner,"capture_"+action)).PerformClick();}
 }
 static void CaptureGate(){
  Check(ModKey.MouseCode(MouseButtons.XButton1)==5&&ModKey.MouseCode(MouseButtons.XButton2)==6,"Windows side-button virtual-key mapping");
  Check(ModKey.MouseCode(MouseButtons.Left)==0,"left mouse never becomes a binding");
  foreach(var opening in new[]{MouseButtons.Left,MouseButtons.Right,MouseButtons.Middle,MouseButtons.XButton1,MouseButtons.XButton2,MouseButtons.Left|MouseButtons.XButton1}){
   var capture=new ModMouseCapture(opening);Check(capture.Press(MouseButtons.XButton1)==0&&capture.Press(MouseButtons.XButton2)==0,"held opening mouse requires release "+opening);capture.Observe(opening);Check(capture.Press(MouseButtons.XButton1)==0,"another press before release ignored "+opening);capture.Observe(MouseButtons.None);Check(capture.Press(MouseButtons.Left)==0&&capture.Press(MouseButtons.XButton1)==5&&capture.Press(MouseButtons.XButton2)==6,"fresh side press accepted after release "+opening);
  }
  var ready=new ModMouseCapture(MouseButtons.None);Check(ready.Press(MouseButtons.XButton1)==5&&ready.Press(MouseButtons.Right)==2&&ready.Press(MouseButtons.Middle)==4,"fresh mouse capture keeps existing zoom bindings");
  Check(ModKey.Normalize(160)==16&&ModKey.Normalize(163)==17&&ModKey.Normalize(165)==18,"keyboard modifier normalization retained");
 }
 static void Functional(){
  const string legacy="; keep owner settings\r\n[control]\r\nsensitivity=0.057\r\nlook_sensitivity=0.067\r\ncontrol_extra=keep\r\n[keys]\r\nfree_look=18\r\nhud_toggle=118\r\nsteering_toggle=119\r\nrecenter=120\r\nreload=121\r\nzoom=2\r\nkeys_extra=keep\r\n[zoom]\r\nenabled=1\r\nratio=2.37\r\nzoom_extra=keep\r\n[hud]\r\nsize=23\r\n[custom]\r\nvalue=keep\r\n";
  File.WriteAllText(config,legacy);var dialogs=new List<string>();
  using(var form=Create(dialogs)){
   Check(File.ReadAllText(config)==legacy,"opening preserves existing settings bytes");
   foreach(string action in actions){
    var codes=Box(form,action).Items.Cast<ModKey>().Select(x=>x.Code).ToArray();Check(codes.Contains(5)&&codes.Contains(6),action+" offers both side buttons");Check(codes.Contains(18)&&codes.Contains(71)&&codes.Contains(118),action+" retains keyboard options");Check(!codes.Any(x=>new[]{1,65,68,69,81,83,87,27,13,9,91,92}.Contains(x)),action+" retains reserved controls");
    if(action!="zoom")Check(!codes.Contains(2)&&!codes.Contains(4),action+" retains existing primary mouse restrictions");
    foreach(int side in new[]{5,6}){
     Reset(form);Choose(form,action,side);Language(form,"ko");Check(Code(form,action)==side&&Box(form,action).SelectedItem.ToString().Contains("마우스"),action+" Korean caption preserves unsaved Mouse "+side);Language(form,"en");Check(Code(form,action)==side&&Box(form,action).SelectedItem.ToString().Contains("Mouse "+(side-1)),action+" English caption preserves unsaved Mouse "+side);
     int before=dialogs.Count;((Button)Find(form,"saveControls")).PerformClick();var saved=Core.ReadIni(config,"keys");Check(dialogs.Count==before&&saved[action]==side.ToString(CultureInfo.InvariantCulture),action+" saves side virtual key "+side);for(int i=0;i<actions.Length;i++)if(actions[i]!=action)Check(saved[actions[i]]==defaults[i].ToString(CultureInfo.InvariantCulture),action+" save preserves other binding "+actions[i]+" "+side);
     using(var reopened=new Launcher(fixture))Check(Code(reopened,action)==side,action+" reopens side virtual key "+side);
     Check(Core.ReadIni(config,"keys")["keys_extra"]=="keep"&&Core.ReadIni(config,"control")["control_extra"]=="keep"&&Core.ReadIni(config,"zoom")["zoom_extra"]=="keep"&&Core.ReadIni(config,"zoom")["ratio"]=="2.37"&&Core.ReadIni(config,"hud")["size"]=="23"&&Core.ReadIni(config,"custom")["value"]=="keep"&&File.ReadAllText(config).Contains("; keep owner settings"),action+" side save preserves unrelated settings "+side);
    }
    Capture(form,action,MouseButtons.XButton1);Check(Code(form,action)==5,action+" captures Mouse 4");Capture(form,action,MouseButtons.XButton2);Check(Code(form,action)==6,action+" captures Mouse 5");CaptureCancel(form,action);Check(Code(form,action)==6,action+" cancel preserves selected side button");
   }
   foreach(int side in new[]{5,6}){Reset(form);Choose(form,"free_look",side);Choose(form,"zoom",side);string before=File.ReadAllText(config);int count=dialogs.Count;((Button)Find(form,"saveControls")).PerformClick();Check(dialogs.Count==count+1&&File.ReadAllText(config)==before,"duplicate side-button assignment rejected without writing "+side);}
   Reset(form);Choose(form,"free_look",5);Choose(form,"zoom",6);int errors=dialogs.Count;((Button)Find(form,"saveControls")).PerformClick();Check(dialogs.Count==errors&&Core.ReadIni(config,"keys")["free_look"]=="5"&&Core.ReadIni(config,"keys")["zoom"]=="6","independent free-look and zoom side-button settings save together");
   foreach(string language in new[]{"en","ko"}){Language(form,language);foreach(string action in actions){var box=Box(form,action);int widest=box.Items.Cast<ModKey>().Where(x=>x.Code==5||x.Code==6).Max(x=>TextRenderer.MeasureText(x.ToString(),box.Font).Width);Check(box.Width>=widest+25,language+" side-button captions fit "+action);}}
  }
 }
 public static int Run(string[] args){
  destination=Path.GetFullPath(args[0]);fixture=Path.Combine(destination,"fixture");Directory.CreateDirectory(fixture);config=Core.Config(fixture,"config.ini");Directory.CreateDirectory(Path.GetDirectoryName(config));Core.Text(Core.Safe(fixture,Core.Folder+"/installed.json"),Core.Json.Serialize(new State{root=fixture,mouse=true,build=Core.ReleaseBuild}));
  try{System.Threading.Thread.CurrentThread.CurrentCulture=CultureInfo.InvariantCulture;Application.EnableVisualStyles();CaptureGate();Functional();File.WriteAllText(Path.Combine(destination,"results.json"),Core.Json.Serialize(new{passed=true,checks=checks.Count,results=checks}));Console.WriteLine("PASS side-button launcher: "+checks.Count+" checks.");return 0;}
  catch(Exception ex){File.WriteAllText(Path.Combine(destination,"results.json"),Core.Json.Serialize(new{passed=false,checks=checks.Count,error=ex.ToString(),results=checks}));Console.WriteLine(ex.ToString());return 1;}
 }
}
