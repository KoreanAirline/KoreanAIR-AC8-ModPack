using System;
using System.IO;
using System.Reflection;
using System.Windows.Forms;
using System.Drawing;
using System.Threading.Tasks;
using System.Runtime.InteropServices;
using System.Threading;
using KoreanAIR;
class Setup : Form {
 bool busy;
 readonly UiLanguage ui=new UiLanguage();
 readonly TextBox path=new TextBox{Name="gamePath",Dock=DockStyle.Fill};
 readonly CheckBox campaign=new CheckBox{Name="campaign",AutoSize=true},mouse=new CheckBox{Name="mouse",AutoSize=true},display=new CheckBox{Name="display",AutoSize=true};
 readonly Label status=new Label{Name="installStatus",AutoSize=true,Dock=DockStyle.Fill};
 readonly Label loaderStatus=new Label{Name="campaignLoaderCompatibility",AutoSize=true,Dock=DockStyle.Fill,ForeColor=Color.DarkOrange,Visible=false};
 readonly Button install=new Button{Name="installPack"},remove=new Button{Name="uninstallPack"};
 readonly Button browse=new Button{Name="browseGame"};
 internal Action<string,MessageBoxIcon> Dialog;
 internal Func<string,DialogResult> ConfirmCoexistence;
 internal Task PendingWork;
 [DllImport("user32.dll")]static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);
 [STAThread]static int Main(string[] args) {
  try {
   if(args.Length>0&&args[0]!="--ui-root") {
    if(args[0]=="--apply-update"&&args.Length==4) { UpdateCore.ApplyInstaller(args[1],args[2],args[3],Assembly.GetExecutingAssembly()); }
    else if(args[0]=="--install"&&args.Length==5) {
     bool cp=args[2]=="1",m=args[3]=="1",d=args[4]=="1";
     if(!cp&&!m&&!d)Core.Uninstall(args[1]);
     else {Core.VerifyGame(args[1]);if(Core.Running(args[1]))throw new Exception("Close ACE COMBAT 8 before changing installed modules.");
      using(var p=ReleasePayload.OpenPayload(Assembly.GetExecutingAssembly(),null,CancellationToken.None))Core.Install(args[1],cp,m,d,p,Assembly.GetExecutingAssembly().Location);}
    }
    else if(args[0]=="--uninstall"&&args.Length==2)Core.Uninstall(args[1]);else throw new Exception("Invalid command line.");return 0;
   }
   try{SetThreadDpiAwarenessContext(new IntPtr(-4));}catch{}
   Application.EnableVisualStyles();Application.Run(new Setup(args.Length==2&&args[0]=="--ui-root"?args[1]:null));return 0;
  }catch(Exception e){if(args.Length>0){Console.Error.WriteLine(e.Message);try{File.WriteAllText(Path.Combine(Path.GetTempPath(),"KoreanAIR_AC8_Setup_error.txt"),e.ToString());}catch{}}else MessageBox.Show(new UiLanguage().Error(e),Core.Brand,MessageBoxButtons.OK,MessageBoxIcon.Error);return 1;}
 }
 public Setup(string preferred) {
  UiWindow.SetBrandIcon(this);
  AutoScaleDimensions=new SizeF(96,96);AutoScaleMode=AutoScaleMode.Dpi;Font=new Font("Segoe UI",10);
  ClientSize=new Size(740,500);MinimumSize=new Size(680,480);MaximizeBox=false;StartPosition=FormStartPosition.CenterScreen;
  Dialog=(text,icon)=>MessageBox.Show(this,text,Core.Brand,MessageBoxButtons.OK,icon);
  ConfirmCoexistence=text=>MessageBox.Show(this,text,Core.Brand,MessageBoxButtons.YesNo,MessageBoxIcon.Warning,MessageBoxDefaultButton.Button2);
  ui.Bind(this,Core.Brand+" — Setup",Core.Brand+" — 설치");
  var main=new TableLayoutPanel{Dock=DockStyle.Fill,Padding=new Padding(24),AutoScroll=true,ColumnCount=1};main.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));Controls.Add(main);
  var header=new TableLayoutPanel{AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,Dock=DockStyle.Top,ColumnCount=2,Margin=new Padding(0,0,0,24)};
  header.RowCount=1;header.RowStyles.Add(new RowStyle(SizeType.AutoSize));
  header.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));header.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,150));
  var title=new Label{AutoSize=true,Dock=DockStyle.Fill,Font=new Font("Segoe UI",19,FontStyle.Bold),Margin=new Padding(0,12,8,0)};ui.Bind(title,"Choose your modules","설치할 기능 선택");header.Controls.Add(title,0,0);
  var language=new TableLayoutPanel{AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,Dock=DockStyle.Top,ColumnCount=1,Margin=new Padding(0)};
  language.RowCount=2;language.RowStyles.Add(new RowStyle(SizeType.AutoSize));language.RowStyles.Add(new RowStyle(SizeType.AutoSize));
  language.Controls.Add(new Label{Text="Language / 언어",AutoSize=true,Margin=new Padding(0)},0,0);language.Controls.Add(ui.Selector(),0,1);header.Controls.Add(language,1,0);Row(main,header);
  var folder=new Label{AutoSize=true,Margin=new Padding(0,0,0,6)};ui.Bind(folder,"Game folder","게임 폴더");Row(main,folder);
  var directory=new TableLayoutPanel{AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,ColumnCount=2,Margin=new Padding(0,0,0,20)};directory.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));directory.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,110));
  directory.RowCount=1;directory.RowStyles.Add(new RowStyle(SizeType.AutoSize));
  path.Text=String.IsNullOrEmpty(preferred)?Core.DetectGame():preferred;path.Margin=new Padding(0,4,8,4);directory.Controls.Add(path,0,0);
  ui.Bind(browse,"Browse…","찾아보기…");browse.AutoSize=true;browse.AutoSizeMode=AutoSizeMode.GrowAndShrink;browse.Dock=DockStyle.Top;browse.Height=34;browse.MinimumSize=new Size(0,34);browse.Margin=new Padding(0);directory.Controls.Add(browse,1,0);Row(main,directory);
  browse.Click+=(s,e)=>{using(var f=new FolderBrowserDialog()){f.Description=ui.T("Select the ACE COMBAT 8 game folder.","ACE COMBAT 8 게임 폴더를 선택하세요.");f.SelectedPath=path.Text;if(f.ShowDialog(this)==DialogResult.OK){path.Text=f.SelectedPath;LoadState(true);}}};
  ui.Bind(campaign,"Korean campaign subtitles","캠페인 한국어 자막");ui.Bind(mouse,"Mouse flight controls","마우스 비행 조종");ui.Bind(display,"Triple monitor span and FOV","트리플 모니터·FOV");mouse.Checked=true;
  foreach(var c in new[]{campaign,mouse,display}){c.Margin=new Padding(0,5,0,15);Row(main,c);}
  loaderStatus.Margin=new Padding(0,0,0,12);Row(main,loaderStatus);
  var note=new Label{AutoSize=true,Margin=new Padding(0,8,0,18)};ui.Bind(note,"Modules run in offline play. Select none to remove the pack.\nYour game, saves and unrelated mods are preserved.","모드는 오프라인 플레이에서 사용합니다. 모든 기능을 해제하면 모드를 제거합니다.\n게임 원본, 세이브, 다른 모드의 파일은 보존합니다.");Row(main,note);
  var buttons=new FlowLayoutPanel{AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,WrapContents=true,Margin=new Padding(0,0,0,12)};
  ui.Bind(install,"Install / Update","설치·업데이트");ui.Bind(remove,"Uninstall","모드 제거");
  foreach(var b in new[]{install,remove}){b.AutoSize=true;b.AutoSizeMode=AutoSizeMode.GrowAndShrink;b.MinimumSize=new Size(165,40);b.Padding=new Padding(10,4,10,4);b.Margin=new Padding(0,0,12,5);buttons.Controls.Add(b);}Row(main,buttons);
  Row(main,status);Status("Ready","준비됨");
  install.Click+=(s,e)=>{PendingWork=Work(false);};remove.Click+=(s,e)=>{PendingWork=Work(true);};path.Leave+=(s,e)=>LoadState(true);LoadState(true);
  FormClosing+=(s,e)=>{if(busy)e.Cancel=true;};
  Shown+=(s,e)=>UiWindow.Fit(this);ResizeEnd+=(s,e)=>UiWindow.Fit(this);
 }
 void Row(TableLayoutPanel parent,Control control){control.Dock=DockStyle.Top;int row=parent.RowCount++;parent.RowStyles.Add(new RowStyle(SizeType.AutoSize));parent.Controls.Add(control,0,row);}
 void Status(string en,string ko){ui.Bind(status,en,ko);}
 void LoadState(bool updateStatus){try{var s=Core.ReadState(path.Text);if(s!=null){campaign.Checked=s.campaign;mouse.Checked=s.mouse;display.Checked=s.display;if(updateStatus)Status("Existing installation detected","기존 설치를 확인했습니다.");}using(var p=ReleasePayload.OpenManifest(Assembly.GetExecutingAssembly())){loaderStatus.Visible=Core.InspectCampaignLoader(path.Text,p).ForeignLoader;}ui.Bind(loaderStatus,"Another mod uses Game/Binaries/Win64/dinput8.dll. Keep Korean campaign subtitles OFF to preserve it while installing Mouse/Screen. In-game coexistence is unverified.","다른 모드가 Game/Binaries/Win64/dinput8.dll을 사용합니다. 해당 파일을 보존하려면 캠페인 한국어 자막을 끄고 마우스·화면 기능을 설치하세요. 실제 게임에서의 동시 사용은 검증되지 않았습니다.");}catch{loaderStatus.Visible=false;}}
 void PayloadProgress(int percent){if(IsDisposed||!IsHandleCreated)return;BeginInvoke(new Action(()=>{if(!IsDisposed)Status("Downloading installation files… "+percent+"%","설치 파일 다운로드 중… "+percent+"%");}));}
 async Task Work(bool uninstall){
  if(busy)return;
  string root=path.Text;bool cp=campaign.Checked,m=mouse.Checked,d=display.Checked;
  uninstall=uninstall||!(cp||m||d);
  if(!uninstall&&cp) {
   try { using(var p=ReleasePayload.OpenManifest(Assembly.GetExecutingAssembly())) {
    if(Core.InspectCampaignLoader(root,p).ForeignLoader) {
     string warning=ui.T("Another mod uses Game/Binaries/Win64/dinput8.dll. Korean campaign subtitles need the same file, so both loaders cannot occupy this path. Your existing loader and mod files will be preserved.\n\nTurn Korean campaign subtitles OFF and continue with the selected Mouse/Screen modules? In-game coexistence is unverified. After removing the other loader yourself, use Installation to add Korean subtitles.\n\nYes: continue with Korean campaign subtitles OFF. No: cancel without changing files.","다른 모드가 Game/Binaries/Win64/dinput8.dll을 사용합니다. 캠페인 한국어 자막도 같은 파일이 필요하므로 두 로더를 이 경로에 함께 설치할 수 없습니다. 기존 로더와 모드 파일은 보존합니다.\n\n캠페인 한국어 자막을 끄고 선택한 마우스·화면 기능으로 계속할까요? 실제 게임에서의 동시 사용은 검증되지 않았습니다. 기존 로더를 직접 제거한 뒤 ‘설치’에서 한국어 자막을 추가할 수 있습니다.\n\n예: 캠페인 한국어 자막을 끄고 계속합니다. 아니요: 파일 변경 없이 취소합니다.");
     if(ConfirmCoexistence(warning)!=DialogResult.Yes){Status("Cancelled; no files changed","취소했습니다. 파일은 변경되지 않았습니다.");return;}
     campaign.Checked=false;cp=false;
     if(!m&&!d){Status("Korean campaign subtitles are OFF. Select Mouse or Screen to install.","캠페인 한국어 자막을 껐습니다. 설치할 마우스 또는 화면 기능을 선택하세요.");return;}
    }
   }}catch(Exception ex){Status("Not completed","완료하지 못했습니다.");Dialog(ui.Error(ex),MessageBoxIcon.Error);return;}
  }
  busy=true;foreach(Control c in new Control[]{path,browse,campaign,mouse,display,install,remove})c.Enabled=false;
  Status(uninstall?"Removing…":"Installing…",uninstall?"제거 중…":"설치 중…");
  try {
   await Task.Run(()=>{if(uninstall)Core.Uninstall(root);else {
    Core.VerifyGame(root);if(Core.Running(root))throw new Exception("Close ACE COMBAT 8 before changing installed modules.");
    using(var p=ReleasePayload.OpenPayload(Assembly.GetExecutingAssembly(),PayloadProgress,CancellationToken.None))Core.Install(root,cp,m,d,p,Assembly.GetExecutingAssembly().Location);
   }});
   Status(uninstall||!(cp||m||d)?"Removed":"Installation complete",uninstall||!(cp||m||d)?"제거를 완료했습니다.":"설치를 완료했습니다.");
   if(!uninstall&&(cp||m||d))Dialog(ui.T("Open "+Core.Brand+".exe in the game folder to play and change settings.","게임 폴더의 "+Core.Brand+".exe를 열어 게임을 실행하고 설정을 조절하세요."),MessageBoxIcon.Information);
  }catch(Exception ex){Status("Not completed","완료하지 못했습니다.");string log=Core.RecordInstallError(ex);Dialog(ui.Error(ex)+(log==null?"":"\n\n"+ui.T("Details: ","오류 기록: ")+log),MessageBoxIcon.Error);}
  finally{busy=false;foreach(Control c in new Control[]{path,browse,campaign,mouse,display,install,remove})c.Enabled=true;LoadState(false);}
 }
 protected override void WndProc(ref Message m){base.WndProc(ref m);if(m.Msg==0x02E0&&IsHandleCreated&&!IsDisposed)BeginInvoke(new Action(()=>UiWindow.Fit(this)));}
}
