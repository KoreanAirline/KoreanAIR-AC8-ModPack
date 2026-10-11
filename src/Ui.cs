using System;
using System.Linq;
using System.IO;
using System.Drawing;
using System.Globalization;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using KoreanAIR;

// Presentation only: the same language preference is shared by Setup and Launcher.
sealed class UiLanguage {
 public string Language { get; private set; }
 readonly Dictionary<Control,Func<string>> captions=new Dictionary<Control,Func<string>>();
 readonly List<Action> updates=new List<Action>();
 static string Preference { get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),Core.Folder,"language.txt"); } }
 public UiLanguage() {
  Language=CultureInfo.CurrentUICulture.TwoLetterISOLanguageName=="ko"?"ko":"en";
  try { string saved=File.ReadAllText(Preference).Trim();if(saved=="ko"||saved=="en")Language=saved; } catch {}
 }
 public string T(string en,string ko) { return Language=="ko"?ko:en; }
 public void Bind(Control control,string en,string ko) { Bind(control,()=>T(en,ko)); }
 public void Bind(Control control,Func<string> caption) { captions[control]=caption;control.Text=caption(); }
 public void OnChange(Action action) { updates.Add(action);action(); }
 public void Change(string language,bool persist) {
  if(language!="en"&&language!="ko")throw new ArgumentException("Unsupported UI language");
  Language=language;
  foreach(var entry in captions)if(!entry.Key.IsDisposed)entry.Key.Text=entry.Value();
  foreach(var action in updates)action();
  if(persist)try { Core.Text(Preference,Language); } catch {}
 }
 public Control Selector() {
  var box=new ComboBox{Name="uiLanguage",DropDownStyle=ComboBoxStyle.DropDownList,Dock=DockStyle.Fill,Margin=new Padding(0,3,0,0)};
  box.Items.AddRange(new object[]{"English","한국어"});box.SelectedIndex=Language=="ko"?1:0;
  box.SelectedIndexChanged+=(s,e)=>Change(box.SelectedIndex==1?"ko":"en",true);
  return box;
 }
 public string Error(Exception ex) {
  var write=ex as PackWriteException;
  if(write!=null)return T("The file could not be saved safely. The operation has stopped.\nFile: ","파일을 안전하게 저장하지 못해 작업을 중단했습니다.\n대상 파일: ")+write.Target+"\n"+T("Operation: ","작업: ")+(write.Stage=="write"?T("Writing","파일 기록"):T("Replacing","파일 교체"))+"\n"+write.InnerException.Message;
  var multiple=ex as AggregateException;
  if(multiple!=null&&multiple.Message.StartsWith("Rollback could not restore every file."))return T("Some files could not be restored after the operation failed.\n","작업 실패 후 일부 파일을 복원하지 못했습니다.\n")+String.Join("\n\n",multiple.InnerExceptions.Select(Error));
  // Preserve filenames and unexpected diagnostics; translate the operation's known error.
  string en=ex.Message;
  var known=new Dictionary<string,string> {
   {"Close ACE COMBAT 8 first.","먼저 ACE COMBAT 8을 종료해 주세요."},
   {"Close the game before saving its quality settings.","게임 품질을 저장하기 전에 게임을 종료해 주세요."},
   {"Start the game once so it can create its settings.","게임을 한 번 실행해 설정 파일을 만든 뒤 다시 시도해 주세요."},
   {"Run the installer before opening this launcher.","설치 프로그램으로 모드를 설치한 뒤 실행기를 열어 주세요."},
   {"Select the ACE COMBAT 8 game folder containing start_protected_game.exe.","start_protected_game.exe가 있는 ACE COMBAT 8 게임 폴더를 선택해 주세요."},
   {"This game build is not supported. No files have been changed.","지원하지 않는 게임 버전입니다. 파일은 변경되지 않았습니다."},
   {"The 64-bit game is required.","64비트 게임이 필요합니다."},
   {"Invalid command line.","잘못된 실행 옵션입니다."},
   {"Close ACE COMBAT 8 before changing installed modules.","설치된 기능을 변경하기 전에 ACE COMBAT 8을 종료해 주세요."},
   {"Close ACE COMBAT 8 before removing modules.","모드를 제거하기 전에 ACE COMBAT 8을 종료해 주세요."},
   {"Resume the installed modules before updating them.","업데이트하기 전에 실행기에서 '모드 다시 사용'을 눌러 주세요."},
   {"Another pack operation is already running for this game folder.","이 게임 폴더에서 다른 설치·제거 작업이 진행 중입니다."},
   {"Unexpected game launch configuration.","게임 실행 설정이 예상한 형식과 다릅니다."},
   {"Invalid game executable.","게임 실행 파일이 올바르지 않습니다."},
   {"Invalid executable header.","게임 실행 파일의 형식이 올바르지 않습니다."},
   {"Run the installer first.","먼저 설치 프로그램으로 모드를 설치해 주세요."},
   {"ACE COMBAT 8 is already running.","ACE COMBAT 8이 이미 실행 중입니다."},
   {"The selected folder is a redirected link.","다른 위치로 연결된 폴더는 선택할 수 없습니다."},
   {"A package file is a redirected link.","설치 파일 경로가 다른 위치로 연결되어 있습니다."},
   {"Invalid package path.","설치 파일 경로가 올바르지 않습니다."},
   {"Package path leaves the selected folder.","설치 파일 경로가 선택한 폴더 밖을 가리킵니다."},
   {"Installation record belongs to another game folder.","설치 기록이 다른 게임 폴더에 속해 있습니다."}
  };
  if(Language!="ko")return en;string ko;if(known.TryGetValue(en,out ko))return ko;
  var prefixes=new Dictionary<string,string> {
   {"A package folder is a redirected link: ","설치 폴더가 다른 위치로 연결되어 있습니다: "},
   {"Missing payload file: ","설치 파일이 누락되었습니다: "},
   {"Payload integrity check failed: ","설치 파일 무결성 확인에 실패했습니다: "},
   {"Another file already occupies this module path. It has been preserved: ","같은 위치에 다른 파일이 있어 보존했습니다: "},
   {"An installed file was changed outside this installer. It has been preserved: ","설치 프로그램 밖에서 변경된 파일을 보존했습니다: "},
   {"An installed file was changed and cannot be removed: ","변경된 설치 파일을 제거할 수 없습니다: "},
   {"Original-file backup is missing: ","설치 전 원본 파일이 누락되었습니다: "},
   {"A changed file has been preserved. Remove it manually or restore the installed version: ","변경된 파일을 보존했습니다. 직접 제거하거나 설치된 버전으로 복원해 주세요: "},
   {"Module state changed outside the launcher: ","실행기 밖에서 모드 파일 상태가 변경되었습니다: "},
   {"Installation verification failed: ","설치된 파일 확인에 실패했습니다: "}
  };
  foreach(var prefix in prefixes)if(en.StartsWith(prefix.Key,StringComparison.Ordinal))return prefix.Value+en.Substring(prefix.Key.Length);
  return en;
 }
}

// A structural layout prevents labels from covering native edit controls at any DPI.
sealed class PrecisionNumber : NumericUpDown {
 public void Commit() { ValidateEditText();Value=Decimal.Round(Value,DecimalPlaces); }
 protected override void ValidateEditText(){base.ValidateEditText();Value=Decimal.Round(Value,DecimalPlaces);}
}
sealed class PrecisionSetting : TableLayoutPanel {
 public readonly PrecisionNumber Number;
 public readonly TrackBar Slider;
 readonly decimal low,step;
 bool updating;
 public PrecisionSetting(UiLanguage ui,string name,string en,string ko,decimal value,decimal minimum,decimal maximum,int places,decimal increment,ToolTip help) {
  Name=name+"Row";low=minimum;step=increment;AutoSize=true;AutoSizeMode=AutoSizeMode.GrowAndShrink;Dock=DockStyle.Top;Margin=new Padding(0,2,0,8);MinimumSize=new Size(0,54);
  ColumnCount=3;RowCount=1;ColumnStyles.Add(new ColumnStyle(SizeType.Percent,36));ColumnStyles.Add(new ColumnStyle(SizeType.Percent,44));ColumnStyles.Add(new ColumnStyle(SizeType.Percent,20));
  RowStyles.Add(new RowStyle(SizeType.AutoSize));
  var label=new Label{AutoSize=true,Dock=DockStyle.Fill,TextAlign=ContentAlignment.MiddleLeft,Margin=new Padding(0,6,10,6)};ui.Bind(label,en,ko);
  Slider=new TrackBar{Name=name+"Slider",Minimum=0,Maximum=Decimal.ToInt32(Decimal.Round((maximum-minimum)/increment)),SmallChange=1,LargeChange=10,TickStyle=TickStyle.None,AutoSize=false,Dock=DockStyle.Top,Height=40,Margin=new Padding(0,4,8,4)};
  Number=new PrecisionNumber{Name=name,Minimum=minimum,Maximum=maximum,DecimalPlaces=places,Increment=increment,Value=Math.Max(minimum,Math.Min(maximum,value)),Dock=DockStyle.Top,Margin=new Padding(0,10,0,0),ThousandsSeparator=false};
  Controls.Add(label,0,0);Controls.Add(Slider,1,0);Controls.Add(Number,2,0);
  Number.ValueChanged+=(s,e)=>SyncSlider();
  Slider.ValueChanged+=(s,e)=>{if(!updating){updating=true;Number.Value=Math.Min(maximum,low+Slider.Value*step);updating=false;}};
  // Commit typed values on Enter as well as on focus change; expose arrow-key fine steps.
  Number.KeyDown+=(s,e)=>{if(e.KeyCode==Keys.Enter){Number.Commit();e.Handled=true;e.SuppressKeyPress=true;}};
  ui.OnChange(()=>{string tip=ui.T("Drag the slider, use Left/Right for fine steps, or type a value. Press Enter to confirm.","슬라이더를 끌거나 좌우 방향키로 미세 조정하세요. 숫자를 직접 입력한 뒤 Enter로 확정할 수도 있습니다.");help.SetToolTip(Slider,tip);help.SetToolTip(Number,tip);});
  SyncSlider();
 }
 void SyncSlider(){if(updating)return;updating=true;Slider.Value=Math.Max(Slider.Minimum,Math.Min(Slider.Maximum,Decimal.ToInt32(Decimal.Round((Number.Value-low)/step))));updating=false;}
}

static class UiWindow {
 public static void Fit(Form form) {
  var area=Screen.FromControl(form).WorkingArea;int width=Math.Max(320,area.Width-32),height=Math.Max(320,area.Height-32);
  form.MinimumSize=new Size(Math.Min(form.MinimumSize.Width,width),Math.Min(form.MinimumSize.Height,height));
  form.Size=new Size(Math.Min(form.Width,width),Math.Min(form.Height,height));
 }
}

// Launcher-only presentation. Setup retains its native light appearance.
static class LauncherTheme {
 public static readonly Color Background=Color.FromArgb(15,20,28),Surface=Color.FromArgb(23,30,41),Raised=Color.FromArgb(30,40,54),Input=Color.FromArgb(12,20,30);
 public static readonly Color Border=Color.FromArgb(51,68,87),Text=Color.FromArgb(237,244,250),Muted=Color.FromArgb(164,181,198),Accent=Color.FromArgb(79,215,232),AccentText=Color.FromArgb(7,30,40);
 [DllImport("dwmapi.dll")]static extern int DwmSetWindowAttribute(IntPtr window,int attribute,ref int value,int size);
 public static void DarkTitleBar(Form form){try{int enabled=1;if(DwmSetWindowAttribute(form.Handle,20,ref enabled,4)!=0)DwmSetWindowAttribute(form.Handle,19,ref enabled,4);}catch{}}
 public static void StyleButton(Button button,bool primary) {
  button.FlatStyle=FlatStyle.Flat;button.UseVisualStyleBackColor=false;button.Cursor=Cursors.Hand;
  button.BackColor=primary?Accent:Raised;button.ForeColor=primary?AccentText:Text;
  button.FlatAppearance.BorderColor=primary?Accent:Border;button.FlatAppearance.BorderSize=1;
  button.FlatAppearance.MouseOverBackColor=primary?Color.FromArgb(114,231,242):Color.FromArgb(44,59,77);
  button.FlatAppearance.MouseDownBackColor=primary?Color.FromArgb(48,179,198):Color.FromArgb(20,30,43);
 }
 public static void Apply(Control control) {
  string kind=control.Tag as string;
  control.BackColor=control.Parent==null?Background:control.Parent.BackColor;control.ForeColor=kind=="muted"?Muted:kind=="accent"?Accent:Text;
  if(control is TabPage)control.BackColor=Surface;
  if(kind=="card")control.BackColor=Raised;
  var setting=control as PrecisionSetting;
  if(setting!=null){control.BackColor=Raised;setting.Padding=new Padding(12,4,12,4);setting.Margin=new Padding(0,2,0,10);}
  var button=control as Button;if(button!=null)StyleButton(button,kind=="primary");
  var combo=control as ComboBox;if(combo!=null){combo.FlatStyle=FlatStyle.Flat;combo.BackColor=Input;combo.ForeColor=Text;}
  var numeric=control as NumericUpDown;if(numeric!=null){numeric.BackColor=Input;numeric.ForeColor=Text;numeric.BorderStyle=BorderStyle.FixedSingle;numeric.TextAlign=HorizontalAlignment.Right;}
  var edit=control as TextBoxBase;if(edit!=null){edit.BackColor=Input;edit.ForeColor=Text;edit.BorderStyle=BorderStyle.FixedSingle;}
  // Retain the crosshair preview's own drawing surface and all native input behavior.
  if(control.Name=="crosshairPreview")control.BackColor=Color.FromArgb(17,24,34);
  if(control.Name=="launcherStatus")control.BackColor=Surface;
  foreach(Control child in control.Controls)Apply(child);
 }
}

// Native tabs keep keyboard navigation, scrolling pages and accessibility.
sealed class LauncherTabs : TabControl {
 public LauncherTabs(){
  DrawMode=TabDrawMode.OwnerDrawFixed;SizeMode=TabSizeMode.Normal;Padding=new Point(15,11);Multiline=true;
  // Paint the entire frame, including the unused tab strip, instead of letting
  // the native light tab background surround individually owner-drawn labels.
  // Native tab geometry and interaction remain in charge of the selected page.
  SetStyle(ControlStyles.UserPaint|ControlStyles.AllPaintingInWmPaint|ControlStyles.OptimizedDoubleBuffer|ControlStyles.ResizeRedraw,true);
 }
 protected override void OnPaintBackground(PaintEventArgs e){using(var fill=new SolidBrush(LauncherTheme.Background))e.Graphics.FillRectangle(fill,ClientRectangle);}
 protected override void OnPaint(PaintEventArgs e){
  Rectangle page=DisplayRectangle;
  if(page.Top<ClientSize.Height){
   var frame=new Rectangle(0,Math.Max(0,page.Top-1),Math.Max(0,ClientSize.Width-1),Math.Max(0,ClientSize.Height-page.Top));
   using(var fill=new SolidBrush(LauncherTheme.Surface))e.Graphics.FillRectangle(fill,frame);
   if(frame.Width>0&&frame.Height>0)using(var border=new Pen(LauncherTheme.Border))e.Graphics.DrawRectangle(border,frame);
  }
  for(int i=0;i<TabPages.Count;i++)DrawTab(e.Graphics,i,GetTabRect(i));
  base.OnPaint(e);
 }
 protected override void OnSelectedIndexChanged(EventArgs e){base.OnSelectedIndexChanged(e);Invalidate();}
 protected override void OnDrawItem(DrawItemEventArgs e) {
  if(e.Index<0||e.Index>=TabPages.Count)return;
  DrawTab(e.Graphics,e.Index,e.Bounds);
  base.OnDrawItem(e);
 }
 void DrawTab(Graphics graphics,int index,Rectangle bounds){
  bool selected=index==SelectedIndex;
  using(var fill=new SolidBrush(selected?LauncherTheme.Surface:LauncherTheme.Background))graphics.FillRectangle(fill,bounds);
  TextRenderer.DrawText(graphics,TabPages[index].Text,Font,bounds,selected?LauncherTheme.Text:LauncherTheme.Muted,TextFormatFlags.HorizontalCenter|TextFormatFlags.VerticalCenter|TextFormatFlags.NoPrefix);
  if(selected)using(var accent=new SolidBrush(LauncherTheme.Accent))graphics.FillRectangle(accent,bounds.Left+9,bounds.Bottom-4,Math.Max(1,bounds.Width-18),3);
  if(selected&&Focused)ControlPaint.DrawFocusRectangle(graphics,Rectangle.Inflate(bounds,-5,-5),LauncherTheme.Text,LauncherTheme.Surface);
 }
}

sealed class LauncherPage : TabPage {
 [DllImport("uxtheme.dll",CharSet=CharSet.Unicode)]static extern int SetWindowTheme(IntPtr window,string subAppName,string subIdList);
 protected override void OnHandleCreated(EventArgs e){base.OnHandleCreated(e);try{SetWindowTheme(Handle,"DarkMode_Explorer",null);}catch{}}
}
