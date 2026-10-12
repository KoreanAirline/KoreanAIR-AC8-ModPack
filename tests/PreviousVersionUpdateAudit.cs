using System;using System.IO;using System.Reflection;using System.Threading;using System.Threading.Tasks;using System.Diagnostics;using System.Drawing;using System.Windows.Forms;using System.Web.Script.Serialization;
class PreviousVersionUpdateAudit{
static Control Find(Control c,string name){if(c.Name==name)return c;foreach(Control x in c.Controls){var r=Find(x,name);if(r!=null)return r;}return null;}
[STAThread]static int Main(string[] a){try{
var asm=Assembly.LoadFrom(Path.GetFullPath(a[0]));var update=asm.GetType("KoreanAIR.UpdateCore");var manifest=update.GetMethod("Fetch").Invoke(null,new object[]{CancellationToken.None});var mt=manifest.GetType();
if((string)mt.GetField("version").GetValue(manifest)!="1.3"||(long)mt.GetField("build").GetValue(manifest)!=2026101301L||!(bool)update.GetMethod("IsNewer").Invoke(null,new[]{manifest}))throw new Exception("Older launcher did not recognize release1.3.");
Application.EnableVisualStyles();string title;
using(var f=(Form)Activator.CreateInstance(asm.GetType("Launcher"),new object[]{Path.GetFullPath(a[1])})){
f.ShowInTaskbar=false;f.StartPosition=FormStartPosition.Manual;f.Location=new Point(-32000,-32000);f.Show();Application.DoEvents();var work=(Task)f.GetType().GetField("UpdateWork",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(f);if(work==null)throw new Exception("No automatic check.");var timer=Stopwatch.StartNew();while(!work.IsCompleted&&timer.ElapsedMilliseconds<30000){Application.DoEvents();Thread.Sleep(25);}Application.DoEvents();Thread.Sleep(100);Application.DoEvents();title=Find(f,"updateTitle").Text;if(!title.Contains("1.3"))throw new Exception("Update banner absent: "+title);}
File.WriteAllText(a[2],new JavaScriptSerializer().Serialize(new{passed=true,previous_version="1.3",previous_build=2026101204L,latest_version="1.3",latest_build=2026101301L,opening_check=true,banner=title,applied=false}));Console.WriteLine("PASS previous1.3 launcher recognizes1.3 and shows update banner on opening.");return 0;
}catch(Exception ex){Console.WriteLine(ex);return 1;}}
}
