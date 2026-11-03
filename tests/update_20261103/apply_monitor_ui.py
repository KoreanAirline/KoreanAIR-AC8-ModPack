from pathlib import Path
D=Path(__file__).resolve().parents[2];p=D/'src/Launcher.cs';s=p.read_text(encoding='utf-8-sig')
old='if(layout.CanSpan)return ui.T("Three aligned displays: ","정렬된 모니터 3대: ")+layout.SpanBounds.Width+" × "+layout.SpanBounds.Height+ui.T(". These three displays form the game view.",". 이 모니터 3대에 게임 화면을 표시합니다.");'
new='''if(layout.CanSpan){var b=layout.SpanBounds;string area=ui.T("Game area: ","게임 표시 영역: ")+b.X+", "+b.Y+" · "+b.Width+" × "+b.Height;
   if(layout.Reason=="selected_bounds")area+="\\n"+ui.T("The selected screens are not aligned. The yellow rectangle includes their gaps and unused desktop space. Choose different screens or change their Windows arrangement to change this area.","선택한 화면의 좌표·크기가 서로 다릅니다. 노란 사각형은 사이의 간격과 사용하지 않는 바탕 화면도 포함합니다. 다른 모니터를 선택하거나 Windows 배치를 바꾸면 영역이 달라집니다.");
   if(!String.IsNullOrEmpty(layout.SelectionDetails))area+="\\n"+layout.SelectionDetails+"\\n"+ui.T("Gaps L–C / C–R: ","간격 왼쪽–가운데 / 가운데–오른쪽: ")+layout.LeftGap+" / "+layout.RightGap+ui.T(" px; top offsets L / R: "," 픽셀; 위쪽 차이 왼쪽 / 오른쪽: ")+layout.LeftTop+" / "+layout.RightTop;
   return area;
  }'''
assert old in s;s=s.replace(old,new)
at='  var diagram=new MonitorLayoutDiagram();Row(p,diagram);'
s=s.replace(at,'  var bounds=Check(p,"spanBounds","Include gaps and different screen sizes","간격·해상도 차이를 포함해 선택 영역으로 확장",Value(d,"span_bounds",1)!=0);\n'+at)
s=s.replace('DisplayTopology.Select(desktop.Monitors,selection())','DisplayTopology.Select(desktop.Monitors,selection(),bounds.Checked)')
s=s.replace('diagram.Monitors=desktop.Monitors;var drawn=selection();','diagram.Monitors=desktop.Monitors;diagram.GameBounds=layout.CanSpan?(Rectangle?)layout.SpanBounds:null;bounds.Enabled=manual.Checked;var drawn=selection();')
s=s.replace('manual.CheckedChanged+=(sender,e)=>validate();ui.OnChange(refresh);','manual.CheckedChanged+=(sender,e)=>validate();bounds.CheckedChanged+=(sender,e)=>validate();ui.OnChange(refresh);')
s=s.replace('{{"enabled",enable.Checked?"1":"0"},{"span",span.Checked?"1":"0"},{"fov",V(fov.Number)}','{{"enabled",enable.Checked?"1":"0"},{"span",span.Checked?"1":"0"},{"span_bounds",bounds.Checked?"1":"0"},{"fov",V(fov.Number)}')
s=s.replace('모니터 3대를 연결하고 올바른 순서로 선택한 뒤 화면 확장을 저장하세요.','연결된 서로 다른 모니터 3대를 선택하세요. 배치가 다르면 ‘간격·해상도 차이를 포함해 선택 영역으로 확장’을 켜세요.')
s=s.replace('Choose three connected, aligned displays before saving triple span.','Choose three connected displays. Enable the include-gaps option if their desktop edges differ.')
# The failure reason remains useful for the optional strict selection policy.
s=s.replace('Use Refresh monitor detection after arranging them. You do not need to disconnect the other displays. Include the problem report if the coordinates look correct.','Enable Include gaps and different screen sizes to use the selected bounding area, or align them in Windows. Other displays can stay connected.')
s=s.replace('배치를 맞춘 뒤 모니터 다시 인식을 누르세요. 다른 모니터를 끌 필요는 없습니다. 좌표가 맞는데도 안 되면 문제 보고서를 보내 주세요.','위의 ‘간격·해상도 차이를 포함해 선택 영역으로 확장’을 켜면 현재 배치로 사용할 수 있습니다. 다른 모니터를 끌 필요는 없습니다.')
s=s.replace('internal string[] Selection=new string[3];internal bool Korean;','internal string[] Selection=new string[3];internal bool Korean;internal Rectangle? GameBounds;')
end='''  }
 }
}'''
pos=s.index('internal sealed class MonitorLayoutDiagram')
prefix=s[:pos];diagram=s[pos:]
assert end in diagram
diagram=diagram.replace(end,'''  }
  if(GameBounds.HasValue){var b=GameBounds.Value;using(var edge=new Pen(Color.Gold,2)){edge.DashStyle=System.Drawing.Drawing2D.DashStyle.Dash;g.DrawRectangle(edge,ox+(b.X-all.X)*scale,oy+(b.Y-all.Y)*scale,b.Width*scale,b.Height*scale);}}
 }
}''',1)
p.write_text(prefix+diagram,encoding='utf-8',newline='\n')
print('Applied manual selected-bounds control and visible game rectangle.')
