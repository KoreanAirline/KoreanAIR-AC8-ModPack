using System;
using System.Drawing;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using KoreanAIR;

partial class Launcher {
 public bool CheckUpdatesOnOpen=true;
 readonly CancellationTokenSource updateCancellation=new CancellationTokenSource();
 Label updateTitle,updateDescription;Button updateAction;ProgressBar updateProgress;
 UpdateManifest availableUpdate;bool checkingUpdate,applyingUpdate;
 internal Task UpdateWork;
 void InitializeUpdates(TableLayoutPanel layout) {
  var banner=new TableLayoutPanel{Name="updateBanner",Tag="card",Dock=DockStyle.Top,AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,Padding=new Padding(14,10,14,10),Margin=new Padding(0,0,0,14),ColumnCount=2};
  banner.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));banner.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
  updateTitle=new Label{Name="updateTitle",Tag="accent",AutoSize=true,Dock=DockStyle.Top,Font=new Font(Font,FontStyle.Bold),Margin=new Padding(0,0,12,4)};
  updateDescription=new Label{Name="updateDescription",Tag="muted",AutoSize=true,Dock=DockStyle.Top,Margin=new Padding(0,0,12,0)};
  banner.Controls.Add(updateTitle,0,0);banner.Controls.Add(updateDescription,0,1);
  updateAction=new Button{Name="updateAction",Tag="primary",AutoSize=true,MinimumSize=new Size(150,40),Margin=new Padding(4,0,0,0),Padding=new Padding(12,5,12,5)};
  banner.Controls.Add(updateAction,1,0);banner.SetRowSpan(updateAction,2);
  updateProgress=new ProgressBar{Name="updateProgress",Dock=DockStyle.Top,Visible=false,Height=5,Margin=new Padding(0,8,0,0)};banner.Controls.Add(updateProgress,0,2);banner.SetColumnSpan(updateProgress,2);
  layout.Controls.Add(banner,0,1);
  SetUpdateState("Automatic update check","자동 업데이트 확인","A new release is checked each time the launcher opens.","런처를 열 때마다 새 배포본을 확인합니다.","Check now","지금 확인",true);
  updateAction.Click+=(s,e)=>{if(availableUpdate!=null)ApplyUpdate();else CheckForUpdate();};
  Shown+=(s,e)=>{if(CheckUpdatesOnOpen)CheckForUpdate();};
  FormClosing+=(s,e)=>updateCancellation.Cancel();
 }
 void SetUpdateState(string titleEn,string titleKo,string detailEn,string detailKo,string buttonEn,string buttonKo,bool enabled) {
  ui.Bind(updateTitle,titleEn,titleKo);ui.Bind(updateDescription,detailEn,detailKo);ui.Bind(updateAction,buttonEn,buttonKo);updateAction.Enabled=enabled;
 }
 void PostUpdate(Action action){if(IsDisposed||Disposing||!IsHandleCreated)return;try{BeginInvoke(new Action(()=>{if(!IsDisposed&&!Disposing)action();}));}catch(InvalidOperationException){}}
 void CheckForUpdate() {
  if(checkingUpdate||applyingUpdate)return;checkingUpdate=true;
  SetUpdateState("Checking for updates…","업데이트 확인 중…","You can use the launcher while this check runs.","확인하는 동안 런처를 사용할 수 있습니다.","Checking…","확인 중…",false);
  UpdateWork=Task.Factory.StartNew(()=>{
   try {var manifest=UpdateCore.Fetch(updateCancellation.Token);PostUpdate(()=>{checkingUpdate=false;ShowUpdate(manifest);});}
   catch(OperationCanceledException){}
   catch(Exception){PostUpdate(()=>{checkingUpdate=false;availableUpdate=null;SetUpdateState("Update check unavailable","업데이트 확인 불가","Check your connection and try again. Installed mods remain available.","인터넷 연결을 확인하고 다시 시도하세요. 설치된 모드는 사용할 수 있습니다.","Retry","다시 확인",true);});}
  });
 }
 // Shared with fixture UI verification: all production manifests are validated by Fetch.
 internal void ShowUpdate(UpdateManifest manifest) {
  availableUpdate=UpdateCore.IsNewer(manifest)?manifest:null;
  if(availableUpdate==null)SetUpdateState("You're up to date · "+state.version,"최신 버전 · "+state.version,"Installed settings and modules are unchanged.","설치된 기능과 사용자 설정은 그대로 유지됩니다.","Check again","다시 확인",true);
  else SetUpdateState("UPDATE AVAILABLE · "+manifest.version,"업데이트 가능 · "+manifest.version,"Your settings and selected modules will be kept.","사용자 설정과 선택한 기능을 유지하며 업데이트합니다.","Update now","지금 업데이트",true);
 }
 void ApplyUpdate() {
  if(applyingUpdate)return;
  if(Core.Running(root)){Dialog(ui.T("Close ACE COMBAT 8 before applying this update. Your settings will be kept.","업데이트를 적용하려면 먼저 게임을 종료하세요. 사용자 설정은 유지됩니다."),MessageBoxIcon.Information);return;}
  var manifest=availableUpdate;if(manifest==null)return;applyingUpdate=true;tabs.Enabled=false;updateProgress.Value=0;updateProgress.Visible=true;
  SetUpdateState("Downloading update…","업데이트 다운로드 중…","The launcher will reopen after installation. Your settings will be kept.","설치 후 런처가 다시 열립니다. 사용자 설정은 유지됩니다.","Downloading…","다운로드 중…",false);
  UpdateWork=Task.Factory.StartNew(()=>{
   try {string installer=UpdateCore.Download(manifest,n=>PostUpdate(()=>updateProgress.Value=n),updateCancellation.Token);
    PostUpdate(()=>{try{UpdateCore.StartInstaller(root,manifest,installer);Close();}catch(Exception ex){UpdateFailed(ex);}});
   } catch(OperationCanceledException){}catch(Exception ex){PostUpdate(()=>UpdateFailed(ex));}
  });
 }
 void UpdateFailed(Exception ex) {
  applyingUpdate=false;tabs.Enabled=true;updateProgress.Visible=false;
  SetUpdateState("Update could not be applied","업데이트를 적용하지 못했습니다.","Your current installation is preserved. Try again when ready.","현재 설치본은 보존됩니다. 준비가 되면 다시 시도하세요.","Try update again","업데이트 다시 시도",true);
  Dialog(ui.Error(ex),MessageBoxIcon.Error);
 }
}
