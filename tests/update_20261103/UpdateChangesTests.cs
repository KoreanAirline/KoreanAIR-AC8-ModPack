using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Drawing;
using System.Reflection;
using System.Windows.Forms;
using KoreanAIR;
static class UpdateChangesTests {
 static int checks;static List<object> results=new List<object>();
 static void Check(bool ok,string name){results.Add(new{name=name,passed=ok});if(!ok)throw new Exception(name);++checks;}
 static Control Find(Control c,string name){if(c.Name==name)return c;foreach(Control child in c.Controls){var found=Find(child,name);if(found!=null)return found;}return null;}
 static UpdateManifest Current() {string version=Core.Brand.Substring("KoreanAIR_AC8_ModPack_".Length);return new UpdateManifest{schema=1,version=version,build=Core.ReleaseBuild,tag="v"+version+"-b"+Core.ReleaseBuild,installer=Core.Brand+"_Setup.exe",size=1024,sha256=new string('0',64)};}
 [STAThread]static int Main(string[] args) {
  string output=Path.GetFullPath(args[0]),root=Path.Combine(Path.GetTempPath(),"ac8notes_"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(output);Directory.CreateDirectory(Path.Combine(root,Core.Folder));
  bool passed=false;string error=null;
  try {
   var current=Current();var legacy=UpdateCore.Parse(Core.Json.Serialize(current));Check(legacy.notes_en==null&&legacy.notes_ko==null,"existing schema1 feed without notes remains valid");
   var notes=Current();notes.notes_en="English changes\nLiteral <script>text</script>";notes.notes_ko="한국어 변경 내역";
   var parsed=UpdateCore.Parse(Core.Json.Serialize(notes));Check(UpdateCore.Notes(parsed,true)==notes.notes_ko&&UpdateCore.Notes(parsed,false)==notes.notes_en,"optional bilingual notes remain literal plain text");
   parsed.notes_ko=null;Check(UpdateCore.Notes(parsed,true)==notes.notes_en,"missing local-language notes fall back to provided text");
   foreach(string bad in new[]{new string('x',8001),"bad\u0001notes"}) {
    var m=Current();m.notes_en=bad;bool rejected=false;try{UpdateCore.Parse(Core.Json.Serialize(m));}catch(InvalidDataException){rejected=true;}Check(rejected,"invalid notes rejected: "+(bad.Length>8000?"length":"control character"));
   }
   string version=Core.Brand.Substring("KoreanAIR_AC8_ModPack_".Length);
   Core.Text(Path.Combine(root,Core.Folder,"installed.json"),Core.Json.Serialize(new State{root=root,version=version,build=Core.ReleaseBuild,previousVersion="2.3",previousBuild=2026101902,mouse=true,display=true,files=new List<FileState>()}));
   Application.EnableVisualStyles();using(var form=new Launcher(root)) {
    form.CheckUpdatesOnOpen=false;form.ShowInTaskbar=false;form.StartPosition=FormStartPosition.Manual;form.Location=new Point(-32000,-32000);form.Size=new Size(1024,800);form.Show();Application.DoEvents();
    var ui=(UiLanguage)typeof(Launcher).GetField("ui",BindingFlags.NonPublic|BindingFlags.Instance).GetValue(form);
    ui.Change("en",false);form.ShowUpdate(current);Application.DoEvents();
    string title=Find(form,"updateTitle").Text;
    Check(title.Contains("2.3")&&title.Contains("2026101902")&&title.Contains(Core.ReleaseBuild.ToString())&&title.Contains("→"),"completed update shows previous and current build");
    Check(Find(form,"updateChanges").Visible&&Find(form,"updateChanges").Enabled,"changes button remains available after update");
    Check(form.UpdateChangesText().Contains(UpdateCore.CurrentReleaseNotes(false)),"installed build notes use trusted compiled English text");
    var future=Current();future.build++;future.tag="v"+future.version+"-b"+future.build;future.notes_en="A specific next-build change";future.notes_ko="다음 빌드의 특정 변경";
    form.ShowUpdate(future);Application.DoEvents();title=Find(form,"updateTitle").Text;
    Check(title.Contains(Core.ReleaseBuild.ToString())&&title.Contains(future.build.ToString())&&title.Contains("→"),"available patch shows current-to-target build transition");
    Check(form.UpdateChangesText().Contains(future.notes_en),"available update shows its matching notes");
    ui.Change("ko",false);Application.DoEvents();Check(Find(form,"updateChanges").Text=="업데이트 내역"&&form.UpdateChangesText().Contains(future.notes_ko),"language switch updates button and pending release notes");
    future.notes_en=future.notes_ko=null;form.ShowUpdate(future);Check(form.UpdateChangesText().Contains("포함되어 있지"),"unknown future notes do not reuse current build notes");
    form.ShowUpdate(current);form.Size=new Size(800,610);Application.DoEvents();
    Check(Find(form,"updateChanges").Right<=Find(form,"updateBanner").Width&&Find(form,"updateAction").Right<=Find(form,"updateBanner").Width,"both actions fit minimum launcher width");
    using(var image=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(image,new Rectangle(0,0,image.Width,image.Height));image.Save(Path.Combine(output,"update_changes_minimum_ko.png"));}
   }
   passed=true;
  }catch(Exception ex){error=ex.GetType().FullName+": "+ex.Message;}
  File.WriteAllText(Path.Combine(output,"update_changes_results.json"),Core.Json.Serialize(new{passed=passed,checks=checks,results=results,error=error}));
  Console.WriteLine("Update change checks="+checks+" passed="+passed);if(error!=null)Console.WriteLine(error);return passed?0:1;
 }
}
