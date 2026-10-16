using System;
using System.IO;
using System.Diagnostics;
using System.Threading;
using System.Web.Script.Serialization;

// The parent is installed only in a synthetic fixture. The monitor closes only
// a process whose executable path exactly matches that fixture's launcher.
class UpdateHandoffProcess {
 static readonly JavaScriptSerializer Json=new JavaScriptSerializer();
 static int Main(string[] args) {
  try {
   if(args.Length==4&&args[0]=="parent") {
    string root=Path.GetFullPath(args[1]),setup=Path.GetFullPath(args[2]);
    var parent=Process.GetCurrentProcess();
    var child=Process.Start(new ProcessStartInfo(setup,"--apply-update \""+root+"\" "+parent.Id+" "+parent.StartTime.ToUniversalTime().Ticks){UseShellExecute=true,WindowStyle=ProcessWindowStyle.Hidden,WorkingDirectory=Path.GetDirectoryName(setup)});
    File.WriteAllText(Path.Combine(root,"handoff-parent.json"),Json.Serialize(new{parentPid=parent.Id,installerPid=child.Id,delayMs=Int32.Parse(args[3])}));
    Thread.Sleep(Int32.Parse(args[3]));return 0;
   }
   if(args.Length==3&&args[0]=="monitor") {
    string expected=Path.GetFullPath(args[1]);
    if(expected.IndexOf(Path.DirectorySeparatorChar+"tests"+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)<0||expected.IndexOf(Path.DirectorySeparatorChar+"fixtures"+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)<0)
     throw new Exception("Monitor is restricted to the tests/fixtures directory.");
    DateTime deadline=DateTime.UtcNow.AddSeconds(40);
    while(DateTime.UtcNow<deadline) {
     foreach(var process in Process.GetProcesses()) {
      using(process) {
       try {
        if(!process.ProcessName.StartsWith("KoreanAIR_AC8_ModPack",StringComparison.OrdinalIgnoreCase))continue;
        var module=process.MainModule;
        if(module==null||!String.Equals(module.FileName,expected,StringComparison.OrdinalIgnoreCase))continue;
        process.Refresh();if(process.MainWindowHandle==IntPtr.Zero)continue;
        IntPtr retainedHandle=process.Handle;if(retainedHandle==IntPtr.Zero)continue;
        int pid=process.Id;bool closeRequested=process.CloseMainWindow();
        bool exited=closeRequested&&process.WaitForExit(10000);
        File.WriteAllText(args[2],Json.Serialize(new{path=expected,pid=pid,visible=true,closeRequested=closeRequested,exited=exited,exitCode=exited?process.ExitCode:-1}));
        return exited?0:1;
       } catch(InvalidOperationException){}catch(System.ComponentModel.Win32Exception){}
      }
     }
     Thread.Sleep(25);
    }
    throw new Exception("Updated fixture launcher did not show a window.");
   }
   return 2;
  } catch(Exception ex) {Console.Error.WriteLine(ex.Message);return 1;}
 }
}
