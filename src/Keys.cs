using System;
using System.Linq;
using System.Collections.Generic;
using System.Drawing;
using System.Windows.Forms;
using KoreanAIR;

sealed class ModKey {
 public readonly int Code;public readonly string Caption;
 public ModKey(int code,string caption){Code=code;Caption=caption;}
 public override string ToString(){return Caption;}
 public static int Normalize(int code){if(code==160||code==161)return 16;if(code==162||code==163)return 17;if(code==164||code==165)return 18;return code;}
 public static int MouseCode(MouseButtons button){return button==MouseButtons.Right?2:button==MouseButtons.Middle?4:button==MouseButtons.XButton1?5:button==MouseButtons.XButton2?6:0;}
 public static List<ModKey> Options(bool mouse=false,string language="en"){
  var result=new List<ModKey>();
  int[] buttons=mouse?new[]{2,4,5,6}:new[]{5,6};
  var english=new Dictionary<int,string>{{2,"Right mouse button"},{4,"Middle mouse button"},{5,"Mouse 4 (Back)"},{6,"Mouse 5 (Forward)"}};
  var korean=new Dictionary<int,string>{{2,"마우스 오른쪽 버튼"},{4,"마우스 가운데 버튼"},{5,"마우스 4 (뒤로)"},{6,"마우스 5 (앞으로)"}};
  foreach(int button in buttons)result.Add(new ModKey(button,language=="ko"?korean[button]:english[button]));
  int[] codes={16,17,18,32,8,33,34,35,36,37,38,39,40,45,46};
  string[] names={"Shift","Ctrl","Alt","Space","Backspace","Page Up","Page Down","End","Home","Left","Up","Right","Down","Insert","Delete"};
  for(int i=0;i<codes.Length;i++)result.Add(new ModKey(codes[i],names[i]));
  for(int i=48;i<=57;i++)result.Add(new ModKey(i,((char)i).ToString()));
  for(int i=65;i<=90;i++)if(i!=65&&i!=68&&i!=69&&i!=81&&i!=83&&i!=87)result.Add(new ModKey(i,((char)i).ToString()));
  for(int i=112;i<=123;i++)result.Add(new ModKey(i,"F"+(i-111)));
  for(int i=96;i<=105;i++)result.Add(new ModKey(i,"Num "+(i-96)));
  int[] extra={106,107,109,110,111,186,187,188,189,190,191,192,219,220,221,222};
  string[] captions={"Num *","Num +","Num -","Num .","Num /","; / :","= / +",", / <","- / _",". / >","/ / ?","` / ~","[ / {","\\ / |","] / }","' / \""};
  for(int i=0;i<extra.Length;i++)result.Add(new ModKey(extra[i],captions[i]));return result;
 }
}

// A button held while opening the capture dialog must be released first.
sealed class ModMouseCapture {
 bool armed;
 public ModMouseCapture(MouseButtons held){Observe(held);}
 public void Observe(MouseButtons held){if(held==MouseButtons.None)armed=true;}
 public int Press(MouseButtons button){return armed?ModKey.MouseCode(button):0;}
}

partial class Launcher {
 internal Func<MouseButtons> HotkeyMouseButtons=()=>Control.MouseButtons;
 Dictionary<string,ComboBox> Hotkeys(TableLayoutPanel p){
  var d=Core.ReadIni(Core.Config(root,"config.ini"),"keys");var result=new Dictionary<string,ComboBox>();
  string[] keys={"free_look","hud_toggle","steering_toggle","recenter","reload","zoom"};
  string[] en={"Free look (hold)","Show / hide crosshairs","Mouse steering on / off","Center mouse aim on aircraft","Reload mod settings","Aim zoom (toggle)"};
  string[] ko={"자유 시점 (누르고 있기)","크로스헤어 표시·숨기기","마우스 조종 켜기·끄기","조준점을 기수 방향에 맞추기","모드 설정 다시 읽기","조준 방향 확대 (전환)"};
  int[] defaults={18,118,119,120,121,2};
  for(int i=0;i<keys.Length;i++){
   var row=new TableLayoutPanel{AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,ColumnCount=3,RowCount=1,Margin=new Padding(0,3,0,6)};
   row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,36));row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,44));row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,20));row.RowStyles.Add(new RowStyle(SizeType.AutoSize));
   var label=new Label{AutoSize=true,Dock=DockStyle.Top,Margin=new Padding(0,6,10,0)};ui.Bind(label,en[i],ko[i]);row.Controls.Add(label,0,0);
   var box=new ComboBox{Name="key_"+keys[i],DropDownStyle=ComboBoxStyle.DropDownList,Dock=DockStyle.Top,Margin=new Padding(0,2,10,0)};
   bool mouse=keys[i]=="zoom";var options=ModKey.Options(mouse,ui.Language);foreach(var item in options)box.Items.Add(item);
   int code=ModKey.Normalize((int)Value(d,keys[i],defaults[i]));box.SelectedItem=options.FirstOrDefault(x=>x.Code==code)??options.First(x=>x.Code==defaults[i]);row.Controls.Add(box,1,0);result.Add(keys[i],box);
   var capture=new Button{Name="capture_"+keys[i],AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,Dock=DockStyle.Top,Margin=new Padding(0),Padding=new Padding(4,1,4,1)};ui.Bind(capture,"Press key…","키 입력…");row.Controls.Add(capture,2,0);Row(p,row);
   var select=box;capture.Click+=(s,e)=>CaptureHotkey(select);
   bool zoom=mouse;ui.OnChange(()=>{int selected=((ModKey)select.SelectedItem).Code;select.BeginUpdate();select.Items.Clear();foreach(var item in ModKey.Options(zoom,ui.Language))select.Items.Add(item);select.SelectedItem=select.Items.Cast<ModKey>().First(x=>x.Code==selected);select.EndUpdate();string tip=zoom?ui.T("Default: click Right mouse button for 2× aim zoom; click again to return. Keyboard keys and right, middle or side mouse buttons are available. A game's binding on the same button can still react; change it in the game if needed.","기본: 마우스 오른쪽 버튼을 한 번 누르면 조준 방향을 2배 확대하고, 다시 누르면 돌아옵니다. 키보드 키 또는 마우스 오른쪽·가운데·옆 버튼을 지정할 수 있습니다. 같은 버튼에 지정한 게임 기능도 반응할 수 있으므로 필요하면 게임에서 변경하세요."):ui.T("Choose a keyboard key or Mouse 4 / Mouse 5 (side buttons). A game's binding on the same button can still react; change it in the game if needed.","키보드 키 또는 마우스 4·5(옆 버튼)를 지정할 수 있습니다. 같은 버튼에 지정한 게임 기능도 반응할 수 있으므로 필요하면 게임에서 변경하세요.");help.SetToolTip(select,tip);help.SetToolTip(capture,tip);});
  }
  Paragraph(p,"Select a key or use ‘Press key’. Every action supports Mouse 4 / Mouse 5 (side buttons); aim zoom also supports right and middle mouse buttons.\nEach action needs a different key. WASD/QE, Escape, Enter, Tab and Windows keys are reserved.\nIf a mod key also triggers a game action, change that binding in the game's controls menu.","목록에서 선택하거나 ‘키 입력’을 누르세요. 모든 기능에 마우스 4·5(옆 버튼)를 지정할 수 있으며, 확대는 오른쪽·가운데 버튼도 지원합니다.\n기능마다 서로 다른 키를 사용하세요. WASD/QE·Esc·Enter·Tab·Windows 키는 지정할 수 없습니다.\n모드 키가 게임 기능도 실행한다면 게임의 조작 설정에서 해당 단축키를 변경하세요.");
  return result;
 }
 Dictionary<string,string> ReadHotkeys(Dictionary<string,ComboBox> inputs){
  var values=new Dictionary<string,string>();var used=new HashSet<int>();
  foreach(var pair in inputs){var key=pair.Value.SelectedItem as ModKey;if(key==null||!ModKey.Options(pair.Key=="zoom").Any(x=>x.Code==key.Code))throw new Exception(ui.T("Select a supported key for every action. Every action supports Mouse 4 / Mouse 5.","모든 기능에 사용 가능한 키를 선택해 주세요. 모든 기능에 마우스 4·5를 지정할 수 있습니다."));int code=ModKey.Normalize(key.Code);if(!used.Add(code))throw new Exception(ui.T("Each mod action must use a different key.","모드 기능마다 서로 다른 키를 지정해 주세요."));values[pair.Key]=code.ToString(System.Globalization.CultureInfo.InvariantCulture);}
  return values;
 }
 void CaptureHotkey(ComboBox selection){
  using(var dialog=new Form{Text=ui.T("Choose a mod key","모드 키 선택"),Font=Font,ClientSize=new Size(440,145),FormBorderStyle=FormBorderStyle.FixedDialog,StartPosition=FormStartPosition.CenterParent,MinimizeBox=false,MaximizeBox=false,KeyPreview=true}){
   bool mouse=selection.Items.Cast<ModKey>().Any(x=>x.Code==2);
   var hint=new Label{AutoSize=false,Dock=DockStyle.Fill,Padding=new Padding(18),Text=mouse?ui.T("Press one key or a right, middle or side mouse button.\nPress Escape to cancel.\nWASD/QE and system keys cannot be assigned.","키 하나 또는 마우스 오른쪽·가운데·옆 버튼을 누르세요.\nEsc를 누르면 취소합니다.\nWASD/QE 및 시스템 키는 지정할 수 없습니다."):ui.T("Press one key or Mouse 4 / Mouse 5 (side buttons).\nPress Escape to cancel.\nWASD/QE and system keys cannot be assigned.","키 하나 또는 마우스 4·5(옆 버튼)를 누르세요.\nEsc를 누르면 취소합니다.\nWASD/QE 및 시스템 키는 지정할 수 없습니다.")};dialog.Controls.Add(hint);
   dialog.KeyDown+=(s,e)=>{e.Handled=true;e.SuppressKeyPress=true;if(e.KeyCode==Keys.Escape){dialog.DialogResult=DialogResult.Cancel;return;}int code=ModKey.Normalize((int)e.KeyCode);var item=selection.Items.Cast<ModKey>().FirstOrDefault(x=>x.Code==code);if(item!=null){selection.SelectedItem=item;dialog.DialogResult=DialogResult.OK;}else hint.Text=ui.T("That key is reserved. Choose another key.\nPress Escape to cancel.","지정할 수 없는 키입니다. 다른 키를 누르세요.\nEsc를 누르면 취소합니다.");};
   var mouseCapture=new ModMouseCapture(HotkeyMouseButtons());
   MouseEventHandler captureMouse=(s,e)=>{int code=mouseCapture.Press(e.Button);var item=selection.Items.Cast<ModKey>().FirstOrDefault(x=>x.Code==code);if(item!=null){selection.SelectedItem=item;dialog.DialogResult=DialogResult.OK;}};dialog.MouseDown+=captureMouse;hint.MouseDown+=captureMouse;
   using(var release=new Timer{Interval=20}){release.Tick+=(s,e)=>mouseCapture.Observe(HotkeyMouseButtons());release.Start();dialog.ShowDialog(this);}
  }
 }
}
