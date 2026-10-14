using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.IO.MemoryMappedFiles;
using System.Runtime.InteropServices;
using System.Security.Principal;
using System.Text;
using System.Threading;
using System.Windows.Forms;

namespace KoreanAIR {
// A private mouse-only collector runs in the existing launcher process. RAW
// registration is process-scoped, so it cannot replace the game's registration.
internal static class MouseInputWorker {
 internal const int Bytes=128,Magic=0x4B414D31,Version=1;
 internal const int MagicAt=0,VersionAt=4,GamePidAt=8,ReadyAt=12,StopAt=16,RequestedAt=20,RequestEpochAt=24,WorkerPidAt=28;
 internal const int CreationAt=32,NativeAliveAt=40,SequenceAt=48,ForegroundEpochAt=52,SnapshotRequestAt=56,AllowedAt=60;
 internal const int XAt=64,YAt=72,HeartbeatAt=80,LastMotionAt=88,RawPacketsAt=96,MovingPacketsAt=104;
 internal static string Name(int pid,string nonce) {return "Local\\KoreanAIR_AC8_Mouse_"+pid.ToString(CultureInfo.InvariantCulture)+"_"+nonce;}
 internal static bool ValidNonce(string nonce) {Guid parsed;return nonce!=null&&nonce.Length==32&&Guid.TryParseExact(nonce,"N",out parsed)&&parsed!=Guid.Empty;}
 [DllImport("kernel32.dll")] internal static extern ulong GetTickCount64();
 [DllImport("kernel32.dll",SetLastError=true)] static extern IntPtr OpenProcess(uint access,bool inherit,int pid);
 [DllImport("kernel32.dll",SetLastError=true,CharSet=CharSet.Unicode)] static extern bool QueryFullProcessImageName(IntPtr process,uint flags,StringBuilder path,ref uint size);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool ProcessIdToSessionId(uint pid,out uint session);
 [DllImport("kernel32.dll")] static extern uint WaitForSingleObject(IntPtr handle,uint timeout);
 [DllImport("kernel32.dll",SetLastError=true)] static extern bool GetProcessTimes(IntPtr process,out long creation,out long exit,out long kernel,out long user);
 [DllImport("advapi32.dll",SetLastError=true)] static extern bool OpenProcessToken(IntPtr process,uint access,out IntPtr token);
 [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr handle);
 [DllImport("user32.dll")] static extern IntPtr GetForegroundWindow();
 [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr window,out uint pid);
 [StructLayout(LayoutKind.Sequential)] internal struct RawDevice {internal ushort Page,Usage;internal uint Flags;internal IntPtr Window;}
 [DllImport("user32.dll",SetLastError=true)] static extern bool RegisterRawInputDevices([In]RawDevice[] devices,uint number,uint size);
 [DllImport("user32.dll",SetLastError=true)] static extern uint GetRawInputData(IntPtr input,uint command,IntPtr buffer,ref uint size,uint header);
 static bool SameUser(IntPtr process) {
  IntPtr token;if(!OpenProcessToken(process,8,out token))return false;
  try {using(var owner=new WindowsIdentity(token))using(var current=WindowsIdentity.GetCurrent())return owner.User!=null&&owner.User.Equals(current.User);}
  finally {CloseHandle(token);}
 }
 internal static int Run(string[] args) {
  if(args==null||args.Length!=3||args[0]!="--mouse-input-worker")return 2;
  int pid;if(!Int32.TryParse(args[1],NumberStyles.None,CultureInfo.InvariantCulture,out pid)||pid<=0||!ValidNonce(args[2]))return 2;
  MemoryMappedViewAccessor view=null;
  try {
   string name=Name(pid,args[2]);bool created;
   var security=new System.Security.AccessControl.MutexSecurity();security.SetAccessRuleProtection(true,false);
   using(var identity=WindowsIdentity.GetCurrent())security.AddAccessRule(new System.Security.AccessControl.MutexAccessRule(
    identity.User,System.Security.AccessControl.MutexRights.FullControl,System.Security.AccessControl.AccessControlType.Allow));
   using(var guard=new Mutex(true,name+"_guard",out created,security)) {
    if(!created)return 3;
    try {
     // Metadata and liveness only: limited query + synchronization permissions.
     // No PROCESS_VM_READ, module enumeration, or game memory access.
     IntPtr game=OpenProcess(0x00101000,false,pid);if(game==IntPtr.Zero)return 4;
     try {
      uint gameSession,currentSession;
      using(var current=Process.GetCurrentProcess()) {
       if(WaitForSingleObject(game,0)!=0x102||!ProcessIdToSessionId((uint)pid,out gameSession)||
          !ProcessIdToSessionId((uint)current.Id,out currentSession)||gameSession!=currentSession||!SameUser(game))return 4;
      }
      var path=new StringBuilder(32768);uint length=(uint)path.Capacity;
      if(!QueryFullProcessImageName(game,0,path,ref length)||
         !String.Equals(Path.GetFileName(path.ToString()),"AceCombat8.exe",StringComparison.OrdinalIgnoreCase))return 4;
      long creation,exit,kernel,user;if(!GetProcessTimes(game,out creation,out exit,out kernel,out user))return 4;
      using(var mapping=MemoryMappedFile.OpenExisting(name,MemoryMappedFileRights.ReadWrite))
      using(var wake=EventWaitHandle.OpenExisting(name+"_wake",System.Security.AccessControl.EventWaitHandleRights.Modify)) {
       using(view=mapping.CreateViewAccessor(0,Bytes,MemoryMappedFileAccess.ReadWrite)) {
        if(view.Capacity!=Bytes||view.ReadInt32(MagicAt)!=Magic||view.ReadInt32(VersionAt)!=Version||view.ReadInt32(GamePidAt)!=pid||view.ReadInt64(CreationAt)!=creation)return 5;
        using(var context=new ApplicationContext())using(var collector=new Collector(game,pid,view,wake,context)) {
         if(!collector.Start())return 6;
         Application.Run(context);return collector.Failed?7:0;
        }
       }
      }
     } finally {CloseHandle(game);}
    } finally {guard.ReleaseMutex();}
   }
  } catch {
   if(view!=null)try {view.Write(ReadyAt,2);}catch{}
   return 1;
  }
 }
 sealed class Collector:NativeWindow,IDisposable {
  readonly IntPtr game;readonly int gamePid;readonly MemoryMappedViewAccessor view;readonly EventWaitHandle wake;readonly ApplicationContext context;
  readonly System.Windows.Forms.Timer timer=new System.Windows.Forms.Timer();readonly byte[] data=new byte[64];GCHandle pinned;
  int seq,epoch,requestEpoch=-1;bool allowed,stopped,registered;
  long x,y,rawPackets,movingPackets,lastMotion;internal bool Failed;
  internal Collector(IntPtr game,int gamePid,MemoryMappedViewAccessor view,EventWaitHandle wake,ApplicationContext context) {
   this.game=game;this.gamePid=gamePid;this.view=view;this.wake=wake;this.context=context;
   timer.Interval=50;timer.Tick+=(s,e)=>{try {if(Alive())Publish(false,0,0);}catch {Stop(true);}};
  }
  internal bool Start() {
   CreateHandle(new CreateParams{Caption="KoreanAIR AC8 mouse input",Parent=new IntPtr(-3)});
   pinned=GCHandle.Alloc(data,GCHandleType.Pinned);
   registered=RegisterRawInputDevices(new[]{new RawDevice{Page=1,Usage=2,Flags=0x100,Window=Handle}},1,(uint)Marshal.SizeOf(typeof(RawDevice)));
   if(!registered){view.Write(ReadyAt,2);return false;}
   using(var current=Process.GetCurrentProcess())view.Write(WorkerPidAt,current.Id);
   if(!Alive())return false;
   Publish(false,0,0);Thread.MemoryBarrier();view.Write(ReadyAt,1);wake.Set();timer.Start();return true;
  }
  bool Alive() {
   if(stopped)return false;
   ulong now=GetTickCount64();long parent=view.ReadInt64(NativeAliveAt);
   if(view.ReadInt32(StopAt)!=0||WaitForSingleObject(game,0)!=0x102||parent<=0||now<(ulong)parent||now-(ulong)parent>5000) {Stop(false);return false;}
   return true;
  }
  bool State(out int requestedEpoch) {
   int before=view.ReadInt32(RequestEpochAt);Thread.MemoryBarrier();int request=view.ReadInt32(RequestedAt);Thread.MemoryBarrier();
   int after=view.ReadInt32(RequestEpochAt);requestedEpoch=after;
   if(before!=after||request!=1)return false;
   uint foreground;GetWindowThreadProcessId(GetForegroundWindow(),out foreground);
   return foreground==(uint)gamePid;
  }
  void Publish(bool packet,int dx,int dy) {
   int nextRequest;bool next=State(out nextRequest)&&!stopped;
   if(next!=allowed||nextRequest!=requestEpoch){epoch=unchecked(epoch+1);allowed=next;requestEpoch=nextRequest;x=y=0;}
   ulong now=GetTickCount64();
   if(packet&&allowed) {rawPackets=unchecked(rawPackets+1);if(dx!=0||dy!=0){x=unchecked(x+dx);y=unchecked(y+dy);movingPackets=unchecked(movingPackets+1);lastMotion=(long)now;}}
   view.Write(SequenceAt,unchecked(seq+1));Thread.MemoryBarrier();
   view.Write(ForegroundEpochAt,epoch);view.Write(SnapshotRequestAt,requestEpoch);view.Write(AllowedAt,allowed?1:0);
   view.Write(XAt,x);view.Write(YAt,y);view.Write(HeartbeatAt,(long)now);view.Write(LastMotionAt,lastMotion);
   view.Write(RawPacketsAt,rawPackets);view.Write(MovingPacketsAt,movingPackets);Thread.MemoryBarrier();
   seq=unchecked(seq+2);view.Write(SequenceAt,seq);wake.Set();
  }
  protected override void WndProc(ref Message message) {
   if(message.Msg==0xFF&&!stopped)try {
    // Process lifetime is checked by the 50ms timer. The hot path uses the
    // existing mapping and foreground PID only, with no process queries.
    if(view.ReadInt32(StopAt)==0) {
     int requestedEpoch;
     if(State(out requestedEpoch)) {
      uint size=(uint)data.Length;uint header=(uint)(8+IntPtr.Size*2);
      uint read=GetRawInputData(message.LParam,0x10000003,pinned.AddrOfPinnedObject(),ref size,header);
      if(read!=UInt32.MaxValue&&read>=header+24&&BitConverter.ToInt32(data,0)==0&&
         (BitConverter.ToUInt16(data,(int)header)&1)==0) {
       Publish(true,BitConverter.ToInt32(data,(int)header+12),BitConverter.ToInt32(data,(int)header+16));
      }
     } else Publish(false,0,0);
    }
   } catch {Stop(true);}
   base.WndProc(ref message);
  }
  void Stop(bool failed) {
   if(stopped)return;stopped=true;Failed=failed;timer.Stop();
   try {allowed=false;Publish(false,0,0);view.Write(ReadyAt,failed?2:3);wake.Set();}catch{}
   context.ExitThread();
  }
  public void Dispose() {
   timer.Stop();timer.Dispose();
   if(registered)RegisterRawInputDevices(new[]{new RawDevice{Page=1,Usage=2,Flags=1,Window=IntPtr.Zero}},1,(uint)Marshal.SizeOf(typeof(RawDevice)));
   if(Handle!=IntPtr.Zero)DestroyHandle();if(pinned.IsAllocated)pinned.Free();
  }
 }
}
}
