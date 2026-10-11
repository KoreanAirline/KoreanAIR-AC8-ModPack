using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Globalization;
using System.Windows.Forms;
using KoreanAIR;

sealed class HudPreview : Control {
 public int AimStyle,HeadingStyle;public float AimSize=30,HeadingSize=24,StrokeWidth=1.5F,OutlineWidth=1;
 public Color AimColor=Color.White,HeadingColor=Color.White,OutlineColor=Color.Black;
 public bool Outline=true;public int Opacity=100;public string AimTitle="Mouse aim",HeadingTitle="Aircraft direction";
 public HudPreview(){Name="crosshairPreview";Height=175;MinimumSize=new Size(220,175);BackColor=Color.FromArgb(25,31,39);DoubleBuffered=true;ResizeRedraw=true;Margin=new Padding(0,5,0,15);}
 protected override void OnPaint(PaintEventArgs e){
  base.OnPaint(e);var g=e.Graphics;g.SmoothingMode=SmoothingMode.AntiAlias;g.PixelOffsetMode=PixelOffsetMode.HighQuality;g.CompositingQuality=CompositingQuality.HighQuality;
  using(var brush=new SolidBrush(Color.FromArgb(224,230,236)))using(var format=new StringFormat{Alignment=StringAlignment.Center}){
   float top=14*ClientSize.Height/175F,captionHeight=Math.Max(30,Font.Height+8);
   g.DrawString(AimTitle,Font,brush,new RectangleF(0,top,ClientSize.Width/2F,captionHeight),format);g.DrawString(HeadingTitle,Font,brush,new RectangleF(ClientSize.Width/2F,top,ClientSize.Width/2F,captionHeight),format);
  }
  Draw(g,new PointF(ClientSize.Width*.25F,ClientSize.Height*.60F),AimStyle,AimSize,AimColor);
  Draw(g,new PointF(ClientSize.Width*.75F,ClientSize.Height*.60F),HeadingStyle,HeadingSize,HeadingColor);
 }
 void Draw(Graphics g,PointF center,int style,float diameter,Color color){
  float r=diameter*.5F;using(var path=new GraphicsPath()){
   if(style==0)path.AddEllipse(center.X-r,center.Y-r,2*r,2*r);
   else if(style==2){float a=r*.7071068F,b=a*.30F;AddLine(path,center,-a,-a,-b,-b);AddLine(path,center,b,b,a,a);AddLine(path,center,-a,a,-b,b);AddLine(path,center,b,-b,a,-a);}
   else {
    float gap=style==4?r*.55F:r*.30F;AddLine(path,center,-r,0,-gap,0);AddLine(path,center,gap,0,r,0);AddLine(path,center,0,-r,0,-gap);AddLine(path,center,0,gap,0,r);
    if(style==4){float q=r*.75F;path.AddEllipse(center.X-q,center.Y-q,2*q,2*q);}
   }
   int alpha=(int)Math.Round(255*Opacity/100.0);
   if(Outline)using(var pen=new Pen(Color.FromArgb(alpha,OutlineColor),StrokeWidth+2*OutlineWidth){StartCap=LineCap.Round,EndCap=LineCap.Round,LineJoin=LineJoin.Round})g.DrawPath(pen,path);
   using(var pen=new Pen(Color.FromArgb(alpha,color),StrokeWidth){StartCap=LineCap.Round,EndCap=LineCap.Round,LineJoin=LineJoin.Round})g.DrawPath(pen,path);
   if(style==1||style==4){float dot=Math.Max(StrokeWidth*.7F,1.2F);if(Outline)using(var brush=new SolidBrush(Color.FromArgb(alpha,OutlineColor)))g.FillEllipse(brush,center.X-dot-OutlineWidth,center.Y-dot-OutlineWidth,2*(dot+OutlineWidth),2*(dot+OutlineWidth));using(var brush=new SolidBrush(Color.FromArgb(alpha,color)))g.FillEllipse(brush,center.X-dot,center.Y-dot,2*dot,2*dot);}
  }
 }
 static void AddLine(GraphicsPath p,PointF c,float x1,float y1,float x2,float y2){p.StartFigure();p.AddLine(c.X+x1,c.Y+y1,c.X+x2,c.Y+y2);}
}

sealed class HudColor : TableLayoutPanel {
 public readonly TextBox Hex;public readonly Button Picker;readonly UiLanguage ui;
 public HudColor(UiLanguage language,string name,string en,string ko,string value){
  ui=language;Name=name+"Row";AutoSize=true;AutoSizeMode=AutoSizeMode.GrowAndShrink;ColumnCount=3;RowCount=1;Margin=new Padding(0,3,0,10);
  ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));ColumnStyles.Add(new ColumnStyle(SizeType.Percent,30));ColumnStyles.Add(new ColumnStyle(SizeType.Percent,20));RowStyles.Add(new RowStyle(SizeType.AutoSize));
  var label=new Label{AutoSize=true,Dock=DockStyle.Top,Margin=new Padding(0,6,10,0)};ui.Bind(label,en,ko);Controls.Add(label,0,0);
  Hex=new TextBox{Name=name,Dock=DockStyle.Top,MaxLength=7,Text=value,CharacterCasing=CharacterCasing.Upper,Margin=new Padding(0,3,10,0)};Controls.Add(Hex,1,0);
  Picker=new Button{Name=name+"Picker",AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,Dock=DockStyle.Top,Margin=new Padding(0),Padding=new Padding(4,1,4,1)};ui.Bind(Picker,"Choose…","색 선택…");Controls.Add(Picker,2,0);
  Picker.Click+=(s,e)=>{using(var dialog=new ColorDialog{Color=PreviewColor(Color.White),FullOpen=true})if(dialog.ShowDialog(FindForm())==DialogResult.OK)Hex.Text=String.Format(CultureInfo.InvariantCulture,"{0:X2}{1:X2}{2:X2}",dialog.Color.R,dialog.Color.G,dialog.Color.B);};
 }
 public string ColorText(){string value=Hex.Text.Trim().TrimStart('#');int rgb;if(value.Length!=6||!Int32.TryParse(value,NumberStyles.HexNumber,CultureInfo.InvariantCulture,out rgb))throw new Exception(ui.T("Enter a six-digit RGB color, such as FFFFFF or 00FF80.","FFFFFF 또는 00FF80처럼 RGB 색상 6자리를 입력해 주세요."));return value.ToUpperInvariant();}
 public Color PreviewColor(Color fallback){try{int rgb=Int32.Parse(ColorText(),NumberStyles.HexNumber,CultureInfo.InvariantCulture);return Color.FromArgb(255,(rgb>>16)&255,(rgb>>8)&255,rgb&255);}catch{return fallback;}}
}

partial class Launcher {
 ComboBox HudStyle(TableLayoutPanel p,string name,string en,string ko,int selected){
  var row=new TableLayoutPanel{AutoSize=true,AutoSizeMode=AutoSizeMode.GrowAndShrink,ColumnCount=2,RowCount=1,Margin=new Padding(0,3,0,8)};row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));row.RowStyles.Add(new RowStyle(SizeType.AutoSize));
  var label=new Label{AutoSize=true,Dock=DockStyle.Top,Margin=new Padding(0,6,10,0)};ui.Bind(label,en,ko);row.Controls.Add(label,0,0);
  var box=new ComboBox{Name=name,DropDownStyle=ComboBoxStyle.DropDownList,Dock=DockStyle.Top,Margin=new Padding(0,2,0,0)};box.Items.AddRange(new object[]{"Circle","Cross + dot","X","Cross","Ring + cross"});box.SelectedIndex=Math.Max(0,Math.Min(4,selected));row.Controls.Add(box,1,0);Row(p,row);
  row.MinimumSize=new Size(0,box.PreferredHeight+box.Margin.Vertical);
  ui.OnChange(()=>{int current=box.SelectedIndex;box.Items.Clear();box.Items.AddRange(ui.Language=="ko"?new object[]{"원","십자 + 중앙 점","X자","십자","원형 + 십자"}:new object[]{"Circle","Cross + dot","X","Cross","Ring + cross"});box.SelectedIndex=current;});return box;
 }
 HudColor HudColour(TableLayoutPanel p,string name,string en,string ko,Dictionary<string,string> d,string key,string fallback){var row=new HudColor(ui,name,en,ko,d.ContainsKey(key)?d[key]:fallback);Row(p,row);return row;}
 void CrosshairTab(){
  var p=Tab("Crosshairs","크로스헤어");if(!state.mouse){Paragraph(p,"Custom crosshairs require Mouse flight. Add it in Installation.","크로스헤어 변경에는 마우스 조종이 필요합니다. 설치 탭에서 추가하세요.");return;}
  var d=Core.ReadIni(Core.Config(root,"config.ini"),"hud");var preview=new HudPreview{Font=Font};Row(p,preview);
  var aimSize=Number(p,"aimSize","Mouse aim diameter (px)","마우스 조준점 크기 (px)",Value(d,"aim_size",30),8,120,1,.1M);
  var aimColor=HudColour(p,"aimColor","Mouse aim color (RGB hex)","마우스 조준점 색상 (RGB)",d,"aim_color","FFFFFF");
  var heading=HudStyle(p,"headingStyle","Aircraft direction style","기수 방향 크로스헤어 모양",(int)Value(d,"heading_style",3));
  var headingSize=Number(p,"headingSize","Aircraft crosshair diameter (px)","기수 크로스헤어 크기 (px)",Value(d,"heading_size",24),8,120,1,.1M);
  var headingColor=HudColour(p,"headingColor","Aircraft crosshair color (RGB hex)","기수 크로스헤어 색상 (RGB)",d,"heading_color","FFFFFF");
  var width=Number(p,"lineWidth","Line width (px)","선 두께 (px)",Value(d,"line_width",1.5M),.5M,6,1,.1M);
  var outline=Check(p,"drawOutline","Thin outline for visibility","가독성을 위한 얇은 테두리",Value(d,"outline",1)!=0);
  var outlineWidth=Number(p,"outlineWidth","Outline width (px)","테두리 두께 (px)",Value(d,"outline_width",1),.5M,4,1,.1M);
  var outlineColor=HudColour(p,"outlineColor","Outline color (RGB hex)","테두리 색상 (RGB)",d,"outline_color","000000");
  var opacity=Number(p,"opacity","Opacity (%)","불투명도 (%)",Value(d,"opacity",100),10,100,0,1);
  Action repaint=()=>{preview.AimStyle=0;preview.HeadingStyle=heading.SelectedIndex;preview.AimSize=(float)aimSize.Number.Value;preview.HeadingSize=(float)headingSize.Number.Value;preview.AimColor=aimColor.PreviewColor(Color.White);preview.HeadingColor=headingColor.PreviewColor(Color.White);preview.StrokeWidth=(float)width.Number.Value;preview.Outline=outline.Checked;preview.OutlineWidth=(float)outlineWidth.Number.Value;preview.OutlineColor=outlineColor.PreviewColor(Color.Black);preview.Opacity=(int)opacity.Number.Value;preview.Invalidate();};
  heading.SelectedIndexChanged+=(s,e)=>repaint();outline.CheckedChanged+=(s,e)=>repaint();
  foreach(var number in new[]{aimSize,headingSize,width,outlineWidth,opacity})number.Number.ValueChanged+=(s,e)=>repaint();
  foreach(var color in new[]{aimColor,headingColor,outlineColor})color.Hex.TextChanged+=(s,e)=>repaint();
  ui.OnChange(()=>{preview.AimTitle=ui.T("Mouse aim","마우스 조준점");preview.HeadingTitle=ui.T("Aircraft direction","기수 방향");preview.Invalidate();});repaint();
  Paragraph(p,"The preview shows both markers at their selected pixel size.\nSave while playing to apply automatically; no restart or reload key is needed.","미리보기는 지정한 픽셀 크기로 두 조준점을 표시합니다.\n게임 중 저장하면 자동으로 적용됩니다. 재시작이나 별도의 키 입력이 필요 없습니다.");
  Button(Actions(p),"saveCrosshairs","Save crosshairs","크로스헤어 저장",()=>{
   var values=new Dictionary<string,string>{{"aim_style","0"},{"heading_style",heading.SelectedIndex.ToString(CultureInfo.InvariantCulture)},{"aim_size",V(aimSize.Number)},{"heading_size",V(headingSize.Number)},{"aim_color",aimColor.ColorText()},{"heading_color",headingColor.ColorText()},{"line_width",V(width.Number)},{"outline",outline.Checked?"1":"0"},{"outline_width",V(outlineWidth.Number)},{"outline_color",outlineColor.ColorText()},{"opacity",V(opacity.Number)}};
   Core.WriteIni(Core.Config(root,"config.ini"),"hud",values);Status("Crosshairs saved; they update automatically in the game.","크로스헤어를 저장했습니다. 게임 중 자동으로 반영됩니다.");
  });
 }
}
