using System;
using System.IO;
using System.Linq;
using System.Drawing;
using System.Reflection;
using System.Globalization;
using System.Collections.Generic;
using System.Windows.Forms;
using System.Web.Script.Serialization;

// A settings-only fixture: no installer payload, game binary, real game folder,
// network request or game launch is needed to exercise the production launcher.
class ZoomUiAudit {
 static Assembly assembly;
 static string fixture,destination,config,statePath;
 static readonly List<object> checks=new List<object>();
 static readonly List<string> failures=new List<string>();
 static readonly BindingFlags instance=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
 static void Check(string name,bool passed,string detail=""){checks.Add(new{name=name,passed=passed,detail=detail});if(!passed)failures.Add(name+": "+detail);}
 static Control Find(Control c,string name){if(c.Name==name)return c;foreach(Control child in c.Controls){var found=Find(child,name);if(found!=null)return found;}return null;}
 static IEnumerable<Control> All(Control c){yield return c;foreach(Control child in c.Controls)foreach(Control nested in All(child))yield return nested;}
 static void Layout(Form f){f.PerformLayout();Application.DoEvents();f.PerformLayout();Application.DoEvents();}
 static void Language(Form f,string language){((ComboBox)Find(f,"uiLanguage")).SelectedIndex=language=="ko"?1:0;Layout(f);}
 static int Code(object key){return (int)key.GetType().GetField("Code").GetValue(key);}
 static int Code(Form f,string action){return Code(((ComboBox)Find(f,"key_"+action)).SelectedItem);}
 static void Choose(Form f,string action,int code){var box=(ComboBox)Find(f,"key_"+action);box.SelectedItem=box.Items.Cast<object>().First(x=>Code(x)==code);}
 static void Commit(NumericUpDown n){n.GetType().GetMethod("Commit").Invoke(n,null);}
 static Dictionary<string,string> Read(string path,string section){return (Dictionary<string,string>)assembly.GetType("KoreanAIR.Core").GetMethod("ReadIni").Invoke(null,new object[]{path,section});}
 static Form Create(List<string> dialogs,float scale=1){
  var f=(Form)Activator.CreateInstance(assembly.GetType("Launcher"),new object[]{fixture});
  f.GetType().GetField("CheckUpdatesOnOpen").SetValue(f,false);
  f.GetType().GetField("Dialog",instance).SetValue(f,new Action<string,MessageBoxIcon>((s,i)=>dialogs.Add(s)));
  f.ShowInTaskbar=false;f.StartPosition=FormStartPosition.Manual;f.Location=new Point(-32000,-32000);f.AutoScaleMode=AutoScaleMode.None;
  if(scale!=1){var controls=All(f).ToArray();var fonts=controls.Select(c=>c.Font).ToArray();f.Scale(new SizeF(scale,scale));for(int i=0;i<controls.Length;i++)controls[i].Font=new Font(fonts[i].FontFamily,fonts[i].Size*scale,fonts[i].Style);}
  f.ClientSize=new Size((int)(800*scale),(int)(610*scale));f.Show();((TabControl)Find(f,"settingsTabs")).SelectedIndex=1;Layout(f);return f;
 }
 static void CaptureKey(Form owner,Keys key){
  using(var timer=new Timer{Interval=20}){
   timer.Tick+=(s,e)=>{var modal=Application.OpenForms.Cast<Form>().FirstOrDefault(f=>f!=owner);if(modal==null)return;timer.Stop();typeof(Control).GetMethod("OnKeyDown",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(modal,new object[]{new KeyEventArgs(key)});};
   timer.Start();((Button)Find(owner,"capture_zoom")).PerformClick();
  }
 }
 static void CaptureMouse(Form owner,MouseButtons button,bool tryLeft){
  using(var timer=new Timer{Interval=20}){
   timer.Tick+=(s,e)=>{var modal=Application.OpenForms.Cast<Form>().FirstOrDefault(f=>f!=owner);if(modal==null)return;timer.Stop();var hint=modal.Controls.OfType<Label>().Single();var mouse=typeof(Control).GetMethod("OnMouseDown",BindingFlags.Instance|BindingFlags.NonPublic);if(tryLeft){mouse.Invoke(hint,new object[]{new MouseEventArgs(MouseButtons.Left,1,25,25,0)});Check("left_mouse_capture_ignored",modal.DialogResult==DialogResult.None);}mouse.Invoke(hint,new object[]{new MouseEventArgs(button,1,25,25,0)});};
   timer.Start();((Button)Find(owner,"capture_zoom")).PerformClick();
  }
 }
 static void Reject(Form f,List<string> dialogs,int code,string caption,string name){
  var box=(ComboBox)Find(f,"key_zoom");var key=Activator.CreateInstance(assembly.GetType("ModKey"),new object[]{code,caption});box.Items.Add(key);box.SelectedItem=key;
  string before=File.ReadAllText(config);int count=dialogs.Count;((Button)Find(f,"saveControls")).PerformClick();Check(name,dialogs.Count==count+1&&File.ReadAllText(config)==before);box.Items.Remove(key);Choose(f,"zoom",2);
 }
 static void Functional(){
  const string legacy="; preserve this comment\r\n[control]\r\nsensitivity=0.057\r\nlook_sensitivity=0.067\r\ncontrol_extra=keep\r\n[keys]\r\nfree_look=18\r\nhud_toggle=118\r\nsteering_toggle=119\r\nrecenter=120\r\nreload=121\r\nkeys_extra=keep\r\n[hud]\r\ncolor=80FF00\r\nsize=23\r\n[custom]\r\nvalue=keep\r\n";
  File.WriteAllText(config,legacy);var dialogs=new List<string>();
  using(var f=Create(dialogs)){
   var enabled=(CheckBox)Find(f,"zoomEnabled");var number=(NumericUpDown)Find(f,"zoomRatio");var slider=(TrackBar)Find(f,"zoomRatioSlider");var box=(ComboBox)Find(f,"key_zoom");var save=(Button)Find(f,"saveControls");
   Check("legacy_missing_zoom_defaults",enabled.Checked&&number.Value==2&&Code(f,"zoom")==2);
   Check("open_does_not_rewrite_legacy_settings",File.ReadAllText(config)==legacy);
   Check("zoom_range_and_fine_step",number.Minimum==1&&number.Maximum==8&&number.Increment==.01M&&number.DecimalPlaces==2);
   number.Text="2.37";Commit(number);number.UpButton();Check("numeric_fine_step",number.Value==2.38M);slider.Value++;Check("slider_fine_step_and_sync",number.Value==2.39M&&slider.Value==139);
   number.Text="0.5";Commit(number);Check("zoom_lower_limit",number.Value==1);number.Text="99";Commit(number);Check("zoom_upper_limit",number.Value==8);
   foreach(int code in new[]{2,4,5,6})Check("zoom_mouse_option_"+code,box.Items.Cast<object>().Any(x=>Code(x)==code));
   foreach(string action in new[]{"free_look","hud_toggle","steering_toggle","recenter","reload"}){var codes=((ComboBox)Find(f,"key_"+action)).Items.Cast<object>().Select(Code).ToArray();Check("existing_action_side_buttons_"+action,codes.Contains(5)&&codes.Contains(6)&&!codes.Any(x=>new[]{1,2,4}.Contains(x)));}
   foreach(int code in new[]{1,65,68,69,81,83,87,27,13,9,91,92})Check("zoom_reserved_excluded_"+code,!box.Items.Cast<object>().Any(x=>Code(x)==code));
   Language(f,"en");var help=(ToolTip)f.GetType().GetField("help",instance).GetValue(f);Check("english_zoom_defaults_tooltip",help.GetToolTip(number).Contains("2×")&&help.GetToolTip(enabled).Contains("Click Right mouse button")&&help.GetToolTip(enabled).Contains("click again")&&help.GetToolTip(enabled).Contains("140 ms"));
   enabled.Checked=false;Choose(f,"zoom",71);number.Text="2.87";Language(f,"ko");Language(f,"en");Language(f,"ko");
   Check("language_preserves_unsaved_zoom",!enabled.Checked&&Code(f,"zoom")==71&&number.Text=="2.87",number.Text);
   Check("korean_zoom_labels_tooltips",enabled.Text.Contains("확대")&&help.GetToolTip(number).Contains("2배")&&box.Items.Cast<object>().First(x=>Code(x)==2).ToString().Contains("오른쪽"));
   File.AppendAllText(config,"[zoom]\r\nzoom_extra=keep\r\n");save.PerformClick();
   var zoom=Read(config,"zoom");var keys=Read(config,"keys");Check("zoom_save_disabled_exact_ratio_custom_key",zoom["enabled"]=="0"&&zoom["ratio"]=="2.87"&&keys["zoom"]=="71");
   Check("zoom_save_preserves_all_other_sections",Read(config,"control")["control_extra"]=="keep"&&Read(config,"control")["sensitivity"]=="0.057"&&keys["keys_extra"]=="keep"&&Read(config,"hud")["color"]=="80FF00"&&Read(config,"hud")["size"]=="23"&&Read(config,"custom")["value"]=="keep"&&zoom["zoom_extra"]=="keep"&&File.ReadAllText(config).Contains("; preserve this comment"));
   var status=(Label)f.GetType().GetField("message",instance).GetValue(f);Check("zoom_saved_auto_apply_status",status.Text.Contains("확대")&&status.Text.Contains("자동"));
   using(var reopened=Create(new List<string>()))Check("zoom_settings_reopen",!((CheckBox)Find(reopened,"zoomEnabled")).Checked&&((NumericUpDown)Find(reopened,"zoomRatio")).Value==2.87M&&Code(reopened,"zoom")==71);
   string before=File.ReadAllText(config);int count=dialogs.Count;Choose(f,"zoom",18);save.PerformClick();Check("zoom_duplicate_other_action_rejected",dialogs.Count==count+1&&File.ReadAllText(config)==before);Choose(f,"zoom",2);
   Reject(f,dialogs,65,"Reserved A","zoom_reserved_save_rejected");Reject(f,dialogs,1,"Left mouse button","left_mouse_save_rejected");
   Language(f,"en");CaptureMouse(f,MouseButtons.Right,true);Check("capture_right_mouse",Code(f,"zoom")==2);CaptureMouse(f,MouseButtons.Middle,false);Check("capture_middle_mouse",Code(f,"zoom")==4);CaptureMouse(f,MouseButtons.XButton1,false);Check("capture_side_mouse_back",Code(f,"zoom")==5);CaptureMouse(f,MouseButtons.XButton2,false);Check("capture_side_mouse_forward",Code(f,"zoom")==6);CaptureKey(f,Keys.G);Check("capture_keyboard_for_zoom",Code(f,"zoom")==71);CaptureKey(f,Keys.Escape);Check("capture_cancel_preserves_key",Code(f,"zoom")==71);
   enabled.Checked=true;Choose(f,"zoom",4);save.PerformClick();Check("zoom_mouse_binding_saved",Read(config,"keys")["zoom"]=="4"&&Read(config,"zoom")["enabled"]=="1");
  }
  string saved=File.ReadAllText(config);
  foreach(string invalid in new[]{"[zoom]\r\nenabled=1\r\nratio=oops\r\n[keys]\r\nzoom=999\r\n","[zoom]\r\nratio=99\r\n","[zoom]\r\nratio=0.5\r\n"}){
   File.WriteAllText(config,invalid);using(var f=Create(new List<string>())){decimal expected=invalid.Contains("oops")?2:invalid.Contains("99")?8:1;Check("invalid_zoom_fallback_"+expected,((NumericUpDown)Find(f,"zoomRatio")).Value==expected&&Code(f,"zoom")==2);Check("invalid_open_does_not_write_"+expected,File.ReadAllText(config)==invalid);}
  }
  File.WriteAllText(config,saved);
 }
 static void Layouts(){
  foreach(float scale in new[]{1f,1.5f})using(var f=Create(new List<string>(),scale))foreach(string language in new[]{"en","ko"}){
   Language(f,language);var tabs=(TabControl)Find(f,"settingsTabs");var page=tabs.SelectedTab;var row=Find(f,"zoomRatioRow");var number=Find(f,"zoomRatio");var slider=Find(f,"zoomRatioSlider");var label=row.Controls.OfType<Label>().Single();string prefix="zoom_"+language+"_"+(int)(scale*100);
   Check(prefix+"_ratio_no_overlap",!number.Bounds.IntersectsWith(slider.Bounds)&&!label.Bounds.IntersectsWith(number.Bounds)&&!label.Bounds.IntersectsWith(slider.Bounds));
   foreach(string name in new[]{"zoomEnabled","zoomRatio","key_zoom","capture_zoom","saveControls"}){var c=Find(f,name);page.ScrollControlIntoView(c);Layout(f);var bounds=c.RectangleToScreen(c.ClientRectangle);var visible=page.RectangleToScreen(page.ClientRectangle);Check(prefix+"_reachable_"+name,bounds.Left>=visible.Left&&bounds.Right<=visible.Right&&bounds.Top>=visible.Top&&bounds.Bottom<=visible.Bottom,bounds+" / "+visible);}
   var box=(ComboBox)Find(f,"key_zoom");int longest=box.Items.Cast<object>().Where(x=>new[]{2,4,5,6}.Contains(Code(x))).Max(x=>TextRenderer.MeasureText(x.ToString(),box.Font).Width);Check(prefix+"_mouse_names_fit",box.Width>=longest+25*scale,box.Width+" / "+longest);
   page.AutoScrollPosition=new Point(0,0);Layout(f);using(var bitmap=new Bitmap(f.Width,f.Height)){f.DrawToBitmap(bitmap,new Rectangle(0,0,f.Width,f.Height));bitmap.Save(Path.Combine(destination,prefix+".png"));}
  }
 }
 [STAThread] static int Main(string[] args){
  if(args.Length!=2)return 2;destination=Path.GetFullPath(args[1]);Directory.CreateDirectory(destination);fixture=Path.Combine(destination,"fixture");Directory.CreateDirectory(fixture);config=Path.Combine(fixture,"Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/config.ini");Directory.CreateDirectory(Path.GetDirectoryName(config));statePath=Path.Combine(fixture,"KoreanAIR_AC8_ModPack/installed.json");Directory.CreateDirectory(Path.GetDirectoryName(statePath));
  string preference=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"KoreanAIR_AC8_ModPack/language.txt");byte[] preferenceBefore=File.Exists(preference)?File.ReadAllBytes(preference):null;
  try{System.Threading.Thread.CurrentThread.CurrentCulture=CultureInfo.InvariantCulture;Application.EnableVisualStyles();assembly=Assembly.LoadFile(Path.GetFullPath(args[0]));string currentVersion=((string)assembly.GetType("KoreanAIR.Core").GetField("Brand").GetRawConstantValue()).Substring("KoreanAIR_AC8_ModPack_".Length);var json=new JavaScriptSerializer();File.WriteAllText(statePath,json.Serialize(new{version=currentVersion,build=0,root=fixture,campaign=false,mouse=true,display=false,suspended=false,files=new object[0]}));string untouched=Path.Combine(fixture,"Game/Binaries/Win64/UE4SS/Mods/AC8MouseAim/display.ini");File.WriteAllText(untouched,"[display]\r\nenabled=0\r\nfov=101.7\r\n");byte[] displayBefore=File.ReadAllBytes(untouched);Functional();Layouts();Check("zoom_save_preserves_display_ini",displayBefore.SequenceEqual(File.ReadAllBytes(untouched)));string state=File.ReadAllText(statePath);File.WriteAllText(statePath,state.Replace("\"mouse\":true","\"mouse\":false").Replace("\"display\":false","\"display\":true"));using(var f=Create(new List<string>()))Check("zoom_requires_mouse_flight_module",Find(f,"zoomEnabled")==null&&Find(f,"zoomRatio")==null&&Find(f,"key_zoom")==null);File.WriteAllText(statePath,state);}
  catch(Exception ex){Check("audit_exception",false,ex.ToString());}
  finally{if(preferenceBefore!=null){Directory.CreateDirectory(Path.GetDirectoryName(preference));File.WriteAllBytes(preference,preferenceBefore);}else if(File.Exists(preference))File.Delete(preference);Check("language_preference_restored",preferenceBefore==null?!File.Exists(preference):preferenceBefore.SequenceEqual(File.ReadAllBytes(preference)));File.WriteAllText(Path.Combine(destination,"results.json"),new JavaScriptSerializer().Serialize(new{passed=failures.Count==0,checks=checks.Count,failures=failures,results=checks,fixture=fixture,tested_launcher_sha256=System.BitConverter.ToString(System.Security.Cryptography.SHA256.Create().ComputeHash(File.ReadAllBytes(Path.GetFullPath(args[0])))).Replace("-","").ToLowerInvariant()}));}
  Console.WriteLine("Zoom UI checks: "+checks.Count+"; failures: "+failures.Count);foreach(string failure in failures)Console.WriteLine(failure);return failures.Count==0?0:1;
 }
}
