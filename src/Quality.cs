using System;
using System.IO;
using System.Collections.Generic;
using System.Drawing;
using System.Windows.Forms;
using KoreanAIR;
partial class Launcher {
 void RefreshMode(){state=Core.ReadState(root);ui.Change(ui.Language,false);}
 string GameSettings { get { return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"BANDAI NAMCO Entertainment","ACE COMBAT 8","Saved","Config","Windows","GameUserSettings.ini"); } }
 void GameQuality(){
  var p=Tab("Game quality","게임 품질");var existing=Core.ReadIni(GameSettings,"ScalabilityGroups");
  string[] keys={"sg.ShadowQuality","sg.CloudQuality","sg.ReflectionQuality","sg.GlobalIlluminationQuality","sg.EffectsQuality","sg.TextureQuality","sg.ViewDistanceQuality","sg.ModelQuality","sg.PostProcessQuality","sg.FoliageQuality","sg.ShadingQuality","sg.LandscapeQuality"};
  string[] en={"Shadows","Clouds","Reflections","Global illumination","Effects","Textures","View distance","Aircraft models","Post processing","Foliage","Shading","Landscape"};
  string[] ko={"그림자","구름","반사","전역 조명","효과","텍스처","시야 거리","기체 모델","후처리","식생","셰이딩","지형"};
  var inputs=new Dictionary<string,ComboBox>();
  Paragraph(p,"These are the game's saved quality settings. Close the game before saving.","게임에 저장된 품질 설정입니다. 저장하기 전에 게임을 종료하세요.");
  var grid=new TableLayoutPanel{AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,ColumnCount=4,Margin=new Padding(0,0,0,10)};
  grid.RowCount=6;for(int row=0;row<6;row++)grid.RowStyles.Add(new RowStyle(SizeType.AutoSize));
  grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,27));grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,23));grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,27));grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,23));
  for(int i=0;i<keys.Length;i++){
   int col=(i/6)*2,row=i%6;var label=new Label{AutoSize=true,Dock=DockStyle.Fill,TextAlign=ContentAlignment.MiddleLeft,Margin=new Padding(col==0?0:14,5,4,8)};ui.Bind(label,en[i],ko[i]);
   var select=new ComboBox{Name=keys[i],Dock=DockStyle.Fill,DropDownStyle=ComboBoxStyle.DropDownList,Margin=new Padding(0,3,4,8)};
   select.Items.AddRange(new object[]{"Low","Medium","High","Ultra"});select.SelectedIndex=(int)Math.Max(0,Math.Min(3,Value(existing,keys[i],3)));
   var current=select;ui.OnChange(()=>{int index=current.SelectedIndex;current.Items.Clear();current.Items.AddRange(ui.Language=="ko"?new object[]{"낮음","중간","높음","최고"}:new object[]{"Low","Medium","High","Ultra"});current.SelectedIndex=index;});
   grid.Controls.Add(label,col,row);grid.Controls.Add(select,col+1,row);inputs.Add(keys[i],select);
  }
  Row(p,grid);var game=Core.ReadIni(GameSettings,"/Script/Live.LiveGameUserSettings");
  var vsync=Check(p,"vsyncEnabled","VSync","수직 동기화 (VSync)",game.ContainsKey("bUseVSync")&&game["bUseVSync"].Equals("True",StringComparison.OrdinalIgnoreCase));
  var fps=Number(p,"frameLimit","Frame limit (0 = unlimited)","프레임 제한 (0 = 제한 없음)",Value(game,"FrameRateLimit",0),0,240,0,1);
  var actions=Actions(p);
  Button(actions,"balancedQuality","Balanced high quality","품질·성능 균형 설정",()=>{foreach(var key in keys)inputs[key].SelectedIndex=key=="sg.ShadowQuality"||key=="sg.CloudQuality"||key=="sg.ReflectionQuality"||key=="sg.GlobalIlluminationQuality"||key=="sg.EffectsQuality"?2:3;Status("Balanced preset selected. Save to apply on the next launch.","균형 설정을 선택했습니다. 저장하면 다음 게임 실행부터 적용됩니다.");});
  Button(actions,"saveGameQuality","Save game quality","게임 품질 저장",()=>{
   if(Core.Running(root))throw new Exception("Close the game before saving its quality settings.");
   if(!File.Exists(GameSettings))throw new Exception("Start the game once so it can create its settings.");
   string backup=Core.Safe(state.backup,"settings/GameUserSettings.ini");if(!File.Exists(backup))Core.Atomic(backup,File.ReadAllBytes(GameSettings));
   var values=new Dictionary<string,string>();foreach(var key in keys)values[key]=inputs[key].SelectedIndex.ToString();
   Core.WriteIni(GameSettings,"ScalabilityGroups",values);Core.WriteIni(GameSettings,"/Script/Live.LiveGameUserSettings",new Dictionary<string,string>{{"bUseVSync",vsync.Checked?"True":"False"},{"FrameRateLimit",V(fps.Number)}});
   Status("Game quality saved for the next launch.","게임 품질을 저장했습니다. 다음 실행부터 적용됩니다.");
  });
 }
}
