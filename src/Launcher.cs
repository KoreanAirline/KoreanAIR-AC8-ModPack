using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Globalization;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using KoreanAIR;

partial class Launcher : Form {
 string root; State state;
 readonly UiLanguage ui=new UiLanguage();
 readonly TabControl tabs=new LauncherTabs{Name="settingsTabs",Dock=DockStyle.Fill,Margin=new Padding(0)};
 readonly Label message=new Label{Name="launcherStatus",AutoSize=true,Dock=DockStyle.Fill,Margin=new Padding(0,12,0,0),Padding=new Padding(12,8,12,8),Tag="muted"};
 readonly ToolTip help=new ToolTip();
 internal Action<string,MessageBoxIcon> Dialog;
 [DllImport("user32.dll")] static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);
 [STAThread] static int Main(string[] args) {
  try {
   string r=AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
   if(args.Length>0) {
    if(args[0]=="--launch") Core.Launch(r);
    else if(args[0]=="--suspend") Core.Suspend(r,true);
    else if(args[0]=="--resume") Core.Suspend(r,false);
    else if(args[0]=="--verify") {
     Core.VerifyGame(r);var s=Core.ReadState(r);if(s==null)throw new Exception("Missing installation");
     foreach(var f in s.files.Where(x=>!x.mutable)) {
      string p=Core.Safe(r,s.suspended&&(f.path.EndsWith("/dinput8.dll")||f.path.EndsWith("/dwmapi.dll")||f.path.EndsWith("/pakchunk0-Windows_999_P.pak"))?Core.Folder+"/Disabled/"+f.path:f.path);
      if(!File.Exists(p)||Core.HashFile(p)!=f.hash)throw new Exception("Changed file: "+f.path);
     }
    } else throw new Exception("Invalid command line.");
    return 0;
   }
   try{SetThreadDpiAwarenessContext(new IntPtr(-4));}catch{}
   Application.EnableVisualStyles();Application.Run(new Launcher(r));return 0;
  } catch(Exception ex) {
   try{File.WriteAllText(Path.Combine(Path.GetTempPath(),"KoreanAIR_AC8_Launcher_error.txt"),ex.ToString());}catch{}
   if(args.Length==0)MessageBox.Show(new UiLanguage().Error(ex),Core.Brand,MessageBoxButtons.OK,MessageBoxIcon.Error);return 1;
  }
 }
 public Launcher(string r) {
  root=r;state=Core.ReadState(root);if(state==null)throw new Exception("Run the installer before opening this launcher.");
  Text=Core.Brand;AutoScaleDimensions=new SizeF(96,96);AutoScaleMode=AutoScaleMode.Dpi;
  Font=new Font("Segoe UI",10);ClientSize=new Size(920,760);MinimumSize=new Size(800,610);StartPosition=FormStartPosition.CenterScreen;
  Dialog=(text,icon)=>MessageBox.Show(this,text,Core.Brand,MessageBoxButtons.OK,icon);
  var layout=new TableLayoutPanel{Name="launcherLayout",Dock=DockStyle.Fill,Padding=new Padding(22),ColumnCount=1,RowCount=4};
  layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));
  layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));layout.RowStyles.Add(new RowStyle(SizeType.Percent,100));layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));Controls.Add(layout);
  var header=new TableLayoutPanel{Name="launcherHeader",Dock=DockStyle.Top,AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,ColumnCount=2,Margin=new Padding(0,0,0,18)};
  header.RowCount=1;header.RowStyles.Add(new RowStyle(SizeType.AutoSize));
  header.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));header.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,155));
  var identity=new TableLayoutPanel{Dock=DockStyle.Top,AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,ColumnCount=1,RowCount=3,Margin=new Padding(0,0,12,0)};
  identity.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));for(int i=0;i<3;i++)identity.RowStyles.Add(new RowStyle(SizeType.AutoSize));
  var eyebrow=new Label{Text="KOREANAIR / MOD LAUNCHER",AutoSize=true,Font=new Font("Segoe UI",8.5F,FontStyle.Bold),Margin=new Padding(0,0,0,4),Tag="accent"};identity.Controls.Add(eyebrow,0,0);
  var title=new Label{Text="ACE COMBAT 8",AutoSize=true,Dock=DockStyle.Fill,Font=new Font("Segoe UI",24,FontStyle.Bold),Margin=new Padding(0,0,0,3)};identity.Controls.Add(title,0,1);
  var caption=new Label{AutoSize=true,Dock=DockStyle.Top,Margin=new Padding(0),Tag="muted"};ui.Bind(caption,"Play, tune your cockpit, and keep your mods up to date.","게임 실행부터 조종 설정, 모드 업데이트까지 한곳에서.");identity.Controls.Add(caption,0,2);header.Controls.Add(identity,0,0);
  var language=new TableLayoutPanel{AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,Dock=DockStyle.Top,ColumnCount=1,Margin=new Padding(0)};
  language.RowCount=2;language.RowStyles.Add(new RowStyle(SizeType.AutoSize));language.RowStyles.Add(new RowStyle(SizeType.AutoSize));
  language.Controls.Add(new Label{Text="Language / 언어",AutoSize=true,Font=new Font("Segoe UI",9),Margin=new Padding(0,4,0,4),Tag="muted"},0,0);language.Controls.Add(ui.Selector(),0,1);header.Controls.Add(language,1,0);
  layout.Controls.Add(header,0,0);layout.Controls.Add(tabs,0,2);layout.Controls.Add(message,0,3);
  Play();ControlsTab();CrosshairTab();DisplayTab();SubtitlesTab();Manage();Status("Settings are saved on this PC.","설정은 이 PC에 저장됩니다.");
  InitializeUpdates(layout);LauncherTheme.Apply(this);ui.OnChange(()=>tabs.Invalidate());
  HandleCreated+=(s,e)=>LauncherTheme.DarkTitleBar(this);
  Shown+=(s,e)=>UiWindow.Fit(this);ResizeEnd+=(s,e)=>UiWindow.Fit(this);
 }
 TableLayoutPanel Tab(string name,string ko) {
  var page=new LauncherPage{Name=name,BackColor=LauncherTheme.Surface,AutoScroll=true,Padding=new Padding(20)};ui.Bind(page,name,ko);tabs.TabPages.Add(page);
  var body=new TableLayoutPanel{Dock=DockStyle.Top,AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,ColumnCount=1,Margin=new Padding(0)};body.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));page.Controls.Add(body);return body;
 }
 void Row(TableLayoutPanel body,Control c){c.Dock=DockStyle.Top;int row=body.RowCount++;body.RowStyles.Add(new RowStyle(SizeType.AutoSize));body.Controls.Add(c,0,row);}
 Label Paragraph(TableLayoutPanel p,string en,string ko){var l=new Label{AutoSize=true,Margin=new Padding(0,4,0,16),Tag="muted"};ui.Bind(l,en,ko);Row(p,l);return l;}
 FlowLayoutPanel Actions(TableLayoutPanel p){var flow=new FlowLayoutPanel{AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,Margin=new Padding(0,10,0,12),WrapContents=true};Row(p,flow);return flow;}
 Button Button(FlowLayoutPanel p,string name,string en,string ko,Action action){var b=new Button{Name=name,AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,MinimumSize=new Size(160,42),Padding=new Padding(14,7,14,7),Margin=new Padding(0,0,12,6),Tag=name.StartsWith("save",StringComparison.Ordinal)||name=="playMods"?"primary":null};ui.Bind(b,en,ko);p.Controls.Add(b);b.Click+=(s,e)=>Run(action);return b;}
 void Run(Action action){try{ValidateChildren();action();}catch(Exception ex){Dialog(ui.Error(ex),MessageBoxIcon.Error);}}
 void Status(string en,string ko){ui.Bind(message,en,ko);}
 PrecisionSetting Number(TableLayoutPanel p,string name,string en,string ko,decimal value,decimal low,decimal high,int places,decimal step){var setting=new PrecisionSetting(ui,name,en,ko,value,low,high,places,step,help);Row(p,setting);return setting;}
 static decimal Value(Dictionary<string,string> d,string k,decimal def){decimal n;return d.ContainsKey(k)&&Decimal.TryParse(d[k],NumberStyles.Float,CultureInfo.InvariantCulture,out n)?n:def;}
 static string V(PrecisionNumber n){n.Commit();return n.Value.ToString(CultureInfo.InvariantCulture);}
 CheckBox Check(TableLayoutPanel p,string name,string en,string ko,bool value){var c=new CheckBox{Name=name,AutoSize=true,Checked=value,Margin=new Padding(0,5,0,12)};ui.Bind(c,en,ko);Row(p,c);return c;}
 void Play(){
  var p=Tab("Play","플레이");
  var hero=Card(p);var ready=new Label{AutoSize=true,Font=new Font("Segoe UI",18,FontStyle.Bold),Margin=new Padding(0,0,0,8)};ui.Bind(ready,"Ready for takeoff","출격 준비 완료");Row(hero,ready);
  var installed=Paragraph(hero,"","");installed.Tag="accent";
  ui.Bind(installed,()=>ui.T("Installed: ","설치된 기능: ")+String.Join(" · ",new[]{state.campaign?ui.T("Korean subtitles","한국어 자막"):null,state.mouse?ui.T("Mouse flight","마우스 조종"):null,state.display?ui.T("Screen & camera","화면·카메라"):null}.Where(x=>x!=null)));
  Paragraph(hero,"Open Steam before playing. This launch uses offline mode.","Steam을 켠 상태에서 실행하세요. 모드는 오프라인 플레이로 실행됩니다.");
  var launch=Button(Actions(hero),"playMods","Play with selected mods","선택한 모드로 게임 실행",()=>{Core.Launch(root);Status("Game launch requested.","게임 실행을 요청했습니다.");RefreshMode();});launch.MinimumSize=new Size(260,48);launch.Font=new Font("Segoe UI",11,FontStyle.Bold);
  var standard=Card(p);var heading=new Label{AutoSize=true,Font=new Font("Segoe UI",12,FontStyle.Bold),Margin=new Padding(0,0,0,8)};ui.Bind(heading,"Standard & online play","기본·온라인 플레이");Row(standard,heading);
  Paragraph(standard,"For standard / online play, disable this pack before opening the game in Steam.\nThis removes this pack's loaders and subtitle archive from active game paths.","기본·온라인 플레이는 아래 버튼으로 모드를 끈 뒤 Steam에서 실행하세요.\n이 모드의 로더와 자막 파일을 게임이 읽는 위치에서 제외합니다.");
  var toggle=Button(Actions(standard),"standardPlay","","",()=>{Core.Suspend(root,!Core.ReadState(root).suspended);state=Core.ReadState(root);Status(state.suspended?"Pack disabled. Open the game normally in Steam.":"Pack enabled for offline launch.",state.suspended?"모드를 껐습니다. Steam에서 게임을 실행하세요.":"오프라인 모드 실행을 사용할 수 있습니다.");RefreshMode();});
  ui.Bind(toggle,()=>state.suspended?ui.T("Resume mod pack","모드 다시 사용"):ui.T("Disable pack for standard play","기본·온라인 플레이용 모드 끄기"));
 }
 TableLayoutPanel Card(TableLayoutPanel parent){var card=new TableLayoutPanel{AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,ColumnCount=1,Padding=new Padding(18,16,18,10),Margin=new Padding(0,0,0,16),Tag="card"};card.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));Row(parent,card);return card;}
 void ControlsTab(){
  var p=Tab("Controls","조종");if(!state.mouse){Paragraph(p,"Mouse flight is not installed. Add it in Installation.","마우스 조종이 설치되지 않았습니다. 설치 탭에서 추가하세요.");return;}
  var d=Core.ReadIni(Core.Config(root,"config.ini"),"control");
  var sensitivity=Number(p,"sensitivity","Mouse steering sensitivity","마우스 조종 감도",Value(d,"sensitivity",0.01M),0.01M,0.2M,3,0.001M);
  var look=Number(p,"lookSensitivity","Free look sensitivity","자유 시점 감도",Value(d,"look_sensitivity",0.03M),0.01M,0.2M,3,0.001M);
  var zoom=Core.ReadIni(Core.Config(root,"config.ini"),"zoom");
  var zoomEnabled=Check(p,"zoomEnabled","Enable aim zoom (hold)","조준 방향 확대 사용 (누르고 있기)",Value(zoom,"enabled",1)!=0);
  var zoomRatio=Number(p,"zoomRatio","Aim zoom magnification (×)","조준 방향 확대 배율 (×)",Value(zoom,"ratio",2),1,8,2,0.01M);
  ui.OnChange(()=>{string tip=ui.T("On by default. Hold Right mouse button to look toward the mouse aim and zoom in; release to return. Default: 2×. Free look takes priority.","기본으로 켜져 있습니다. 마우스 오른쪽 버튼을 누르고 있으면 마우스 조준 방향을 확대하고, 놓으면 돌아옵니다. 기본 배율: 2배. 자유 시점이 우선합니다.");help.SetToolTip(zoomEnabled,tip);help.SetToolTip(zoomRatio,tip);help.SetToolTip(zoomRatio.Slider,tip+" "+ui.T("Range: 1–8×; fine steps: 0.01×.","범위: 1~8배, 미세 조절: 0.01배."));help.SetToolTip(zoomRatio.Number,tip+" "+ui.T("Type a value and press Enter to confirm.","숫자를 입력한 뒤 Enter로 확정하세요."));});
  Paragraph(p,"Aim zoom follows the mouse steering target during flight. Hold its key to zoom; release to return.\nIt works with Mouse flight even when Screen & camera is off. Change its key below.","비행 중 마우스 조종 목표 방향을 확대합니다. 확대 키를 누르고 있다가 놓으면 돌아옵니다.\n화면·카메라 설정을 꺼도 마우스 조종 모듈에서 사용할 수 있습니다. 확대 키는 아래에서 변경하세요.");
  Paragraph(p,"Saved changes apply automatically while playing. WASD remains direct aircraft control.\nSet the game's own flight and target-selection keys in its controls menu.","저장하면 게임 중에도 자동으로 적용됩니다. WASD는 기체 직접 조종을 유지합니다.\n게임 자체의 비행·타겟 선택 키는 게임 안의 조작 설정에서 변경하세요.");
  var bindings=Hotkeys(p);
  Button(Actions(p),"saveControls","Save controls & keys","조종·키 설정 저장",()=>{var keyValues=ReadHotkeys(bindings);Core.WriteIni(Core.Config(root,"config.ini"),"keys",keyValues);Core.WriteIni(Core.Config(root,"config.ini"),"control",new Dictionary<string,string>{{"sensitivity",V(sensitivity.Number)},{"look_sensitivity",V(look.Number)}});Core.WriteIni(Core.Config(root,"config.ini"),"zoom",new Dictionary<string,string>{{"enabled",zoomEnabled.Checked?"1":"0"},{"ratio",V(zoomRatio.Number)}});Status("Controls, zoom and keys saved; changes apply automatically in the game.","조종·확대·키 설정을 저장했습니다. 게임 중 자동으로 적용됩니다.");});
 }
 void RefreshMode(){state=Core.ReadState(root);ui.Change(ui.Language,false);}
 string Geometry(out bool ok){
  ok=false;try{IntPtr old=SetThreadDpiAwarenessContext(new IntPtr(-4));try{
   var ss=Screen.AllScreens;var c=ss.Single(x=>x.Primary);
   var left=ss.FirstOrDefault(x=>x.Bounds.Right==c.Bounds.Left&&x.Bounds.Y==c.Bounds.Y&&x.Bounds.Size==c.Bounds.Size);
   var right=ss.FirstOrDefault(x=>x.Bounds.Left==c.Bounds.Right&&x.Bounds.Y==c.Bounds.Y&&x.Bounds.Size==c.Bounds.Size);
   if(left!=null&&right!=null&&c.Bounds.Width*3<=16384&&c.Bounds.Height<=16384&&ss.Count(x=>x.Bounds.Right==c.Bounds.Left&&x.Bounds.Y==c.Bounds.Y&&x.Bounds.Size==c.Bounds.Size)==1&&ss.Count(x=>x.Bounds.Left==c.Bounds.Right&&x.Bounds.Y==c.Bounds.Y&&x.Bounds.Size==c.Bounds.Size)==1){ok=true;return ui.T("Three aligned displays: ","정렬된 모니터 3대: ")+(c.Bounds.Width*3)+" × "+c.Bounds.Height;}
   return ui.T("Triple span needs equal-size, aligned displays on both sides of the main display.\nSingle-display FOV is available with your current layout.","트리플 화면은 주 모니터 양옆에 해상도가 같은 모니터를 나란히 배치해야 합니다.\n현재 배치에서도 단일 모니터 FOV는 조절할 수 있습니다.");
  }finally{SetThreadDpiAwarenessContext(old);}}catch{return ui.T("Monitor layout could not be read. Check Windows display settings.","모니터 배치를 읽지 못했습니다. Windows 디스플레이 설정을 확인하세요.");}
 }
 void DisplayTab(){
  var p=Tab("Screen & camera","화면·카메라");if(!state.display){Paragraph(p,"Screen & camera is not installed. Add it in Installation.","화면·카메라 기능이 설치되지 않았습니다. 설치 탭에서 추가하세요.");return;}
  var d=Core.ReadIni(Core.Config(root,"display.ini"),"display");bool ok;Geometry(out ok);var geometry=Paragraph(p,"","");ui.Bind(geometry,()=>{bool detected;return Geometry(out detected);});
  var enable=Check(p,"cameraEnabled","Enable camera settings","카메라 설정 사용",Value(d,"enabled",1)!=0);
  var span=Check(p,"spanEnabled","Span across three monitors (no NVIDIA Surround)","모니터 3대에 화면 확장 (NVIDIA Surround 불필요)",ok&&Value(d,"span",0)!=0);span.Enabled=ok;
  var fov=Number(p,"fov","FOV (16:9 reference)","시야각 FOV (16:9 기준)",Value(d,"fov",100),60,120,1,0.1M);
  var distance=Number(p,"cameraDistance","Chase camera distance","추적 카메라 거리",Value(d,"distance",3000),1500,6000,0,1);
  var height=Number(p,"cameraHeight","Chase camera height","추적 카메라 높이",Value(d,"height",600),0,1500,0,1);
  if(!state.mouse){distance.Enabled=height.Enabled=false;Paragraph(p,"Camera distance and height require Mouse flight.","카메라 거리·높이를 조절하려면 마우스 조종도 설치해야 합니다.");}
  Paragraph(p,"FOV affects flight. Menus and cinematics keep their original camera.\nScreen changes can be saved while playing; focus the game to see the result.","FOV는 비행 중 적용됩니다. 메뉴·영상 장면의 카메라는 원본을 사용합니다.\n게임 중에도 저장할 수 있습니다. 게임으로 돌아가면 화면 설정이 반영됩니다.");
  Button(Actions(p),"saveDisplay","Save screen & camera","화면·카메라 설정 저장",()=>{Core.WriteIni(Core.Config(root,"display.ini"),"display",new Dictionary<string,string>{{"enabled",enable.Checked?"1":"0"},{"span",span.Checked&&ok?"1":"0"},{"fov",V(fov.Number)},{"distance",V(distance.Number)},{"height",V(height.Number)}});Status("Screen & camera settings saved.","화면·카메라 설정을 저장했습니다.");});
 }
 void SubtitlesTab(){
  var p=Tab("Subtitles","자막");if(!state.mouse&&!state.display&&!state.campaign){Paragraph(p,"Subtitle positioning requires an installed module. Add one in Installation.","자막 위치를 조절하려면 모듈이 필요합니다. 설치 탭에서 추가하세요.");return;}
  var d=Core.ReadIni(Core.Config(root,"subtitle.ini"),"subtitles");string saved;int selected=d.TryGetValue("position",out saved)&&String.Equals(saved,"bottom",StringComparison.OrdinalIgnoreCase)?1:0;
  var row=new TableLayoutPanel{AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,ColumnCount=2,RowCount=1,Margin=new Padding(0,3,0,8)};row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));row.RowStyles.Add(new RowStyle(SizeType.AutoSize));
  var label=new Label{Name="subtitlePositionLabel",AutoSize=true,Dock=DockStyle.Top,Margin=new Padding(0,6,10,0)};ui.Bind(label,"Dialogue subtitle position","대사 자막 위치");row.Controls.Add(label,0,0);
  var position=new ComboBox{Name="subtitlePosition",DropDownStyle=ComboBoxStyle.DropDownList,Dock=DockStyle.Top,Margin=new Padding(0,2,0,0)};position.Items.AddRange(new object[]{"Original position","Bottom of screen"});position.SelectedIndex=selected;row.Controls.Add(position,1,0);Row(p,row);row.MinimumSize=new Size(0,position.PreferredHeight+position.Margin.Vertical);
  ui.OnChange(()=>{int current=position.SelectedIndex;position.Items.Clear();position.Items.AddRange(ui.Language=="ko"?new object[]{"원래 위치","화면 하단"}:new object[]{"Original position","Bottom of screen"});position.SelectedIndex=current;});
  Paragraph(p,"Choose the original position or lower supported dialogue subtitles toward the bottom.\nSaved changes apply automatically while playing.","지원하는 대사 자막을 원래 위치에 두거나 화면 하단으로 내릴 수 있습니다.\n저장하면 게임 중에도 자동으로 적용됩니다.");
  Button(Actions(p),"saveSubtitles","Save subtitle position","자막 위치 저장",()=>{Core.WriteIni(Core.Config(root,"subtitle.ini"),"subtitles",new Dictionary<string,string>{{"position",position.SelectedIndex==1?"bottom":"native"}});Status("Subtitle position saved; changes apply automatically in the game.","자막 위치를 저장했습니다. 게임 중 자동으로 적용됩니다.");});
 }
 void Manage(){
  var p=Tab("Installation","설치");Paragraph(p,"Add, remove or update the three modules with the installer.\nClose the game before changing installed modules.","설치 프로그램에서 각 기능을 추가·제거하거나 업데이트할 수 있습니다.\n설치 구성을 바꾸기 전에 게임을 종료하세요.");
  var compatibility=Paragraph(p,"","");compatibility.Name="campaignLoaderCompatibility";
  ui.Bind(compatibility,()=>{bool foreign=Core.InspectCampaignLoader(root).ForeignLoader;compatibility.Visible=foreign;return foreign?ui.T("Another mod uses Game/Binaries/Win64/dinput8.dll.\nTo keep it, install Mouse flight or Screen & camera with Korean campaign subtitles off.\nAfter removing the other loader, add Korean campaign subtitles in Installation.\nUsing these mods together in game has not been verified.","다른 모드가 Game/Binaries/Win64/dinput8.dll을 사용하고 있습니다.\n이 파일을 보존하려면 한국어 캠페인 자막을 끄고 마우스 조종·화면 기능을 설치하세요.\n기존 로더를 제거한 뒤 설치 탭에서 한국어 캠페인 자막을 추가할 수 있습니다.\n실제 게임에서 모드를 함께 사용하는 동작은 아직 검증되지 않았습니다."):"";});
  var actions=Actions(p);
  Button(actions,"changeModules","Change installed modules","설치된 기능 변경",()=>{if(Core.Running(root))throw new Exception("Close ACE COMBAT 8 first.");string temp=Path.Combine(Path.GetTempPath(),Core.Brand+"_Setup_"+Guid.NewGuid().ToString("N")+".exe");File.Copy(Core.Safe(root,Core.Folder+"/Setup.exe"),temp);Process.Start(new ProcessStartInfo(temp,"--ui-root \""+root+"\""){WorkingDirectory=root,UseShellExecute=true});Close();});
  Button(actions,"openFolder","Open game folder","게임 폴더 열기",()=>Process.Start("explorer.exe",root));
  var docs=Actions(p);Button(docs,"openReadme","Open README","사용 안내 열기",()=>Process.Start(new ProcessStartInfo(Core.Safe(root,Core.Folder+"/README_"+(ui.Language=="ko"?"KOR":"ENG")+".txt")){UseShellExecute=true}));
  Button(docs,"openLicenses","Licenses & credits","라이선스·제작 정보",()=>Process.Start("explorer.exe",Core.Safe(root,Core.Folder+"/Licenses")));
  Paragraph(p,"Original-file backups are kept outside the game folder.\nThe installer preserves saves and files belonging to other mods.","설치 전 원본 파일은 게임 폴더 밖에 보관됩니다.\n설치 프로그램은 세이브와 다른 모드의 파일을 보존합니다.");
 }
 protected override void Dispose(bool disposing){if(disposing)help.Dispose();base.Dispose(disposing);}
 protected override void WndProc(ref Message m){base.WndProc(ref m);if(m.Msg==0x02E0&&IsHandleCreated&&!IsDisposed)BeginInvoke(new Action(()=>UiWindow.Fit(this)));}
}
