"""Render the generated Mermaid topology as a self-contained zoomable SVG."""
import html
import re
from pathlib import Path

def render(folder):
    folder=Path(folder)
    source=(folder/"execution.mmd").read_text(encoding="utf-8")
    labels=dict(re.findall(r'(\w+)\["([^"\n]+)"\]',source))
    edges=[]
    for line in source.splitlines():
        match=re.match(r'^(\w+)(?:\["[^"\n]+"\])?\s+(-->|-\.)(.*)',line)
        if not match: continue
        a,style,tail=match.groups()
        if style == '-->':
            b=tail.strip().split('[')[0].strip(); note=''
        else:
            note,tail=tail.split('.->',1)
            b=tail.strip().split('[')[0].strip()
        edges.append((a,b,style,note.strip()))
        labels.setdefault(a,a.replace('_',' '))
        labels.setdefault(b,b.replace('_',' '))
    positions={}
    flow=[n for n in labels if not n.startswith(('agent_','tool_','mcp_')) and n not in {'manager','memory','artifacts','schema','scan','research_task'}]
    for i,n in enumerate(flow): positions[n]=(60,150+i*105)
    other=[n for n in labels if n not in positions]
    for i,n in enumerate(other): positions[n]=(560+(i//10)*500,150+(i%10)*145)
    width=max(1600,max(x for x,y in positions.values())+460); height=max(1800,180+len(flow)*105)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#7192b0"/></marker></defs>',
           '<rect width="100%" height="100%" fill="#0e1725"/>',
           '<text x="60" y="48" fill="#f1f5fb" font-family="sans-serif" font-size="26">DevCrew: implemented execution architecture</text>',
           '<text x="60" y="83" fill="#bdccdc" font-family="sans-serif" font-size="15">Solid: Flow dependency. Dotted: capability / contained work. UI design, standards and security are required baseline stages.</text>',
           '<text x="60" y="110" fill="#bdccdc" font-family="sans-serif" font-size="15">Review cycles join parallel code, security and visual review; revisions stop on completion or no progress.</text>']
    for a,b,style,note in edges:
        x,y=positions[a]; xx,yy=positions[b]
        if x==xx:
            x+=200; xx+=200; y+=65
        else:
            x+=400; y+=32; yy+=32
        dash=' stroke-dasharray="5 6"' if style=='-.' else ''
        parts.append(f'<path d="M{x},{y} L{xx},{yy}" fill="none" stroke="#7192b0" stroke-width="1.4" opacity="0.65" marker-end="url(#arrow)"{dash}><title>{html.escape(note or "Flow dependency")}</title></path>')
    for n,label in labels.items():
        x,y=positions[n]
        color='#173d45' if n.startswith('agent_') else '#23304a'
        parts.append(f'<rect x="{x}" y="{y}" width="400" height="65" rx="12" fill="{color}" stroke="#7292ac"/>')
        words=label.split(); rows=['']
        for word in words:
            if len(rows[-1])+len(word)>43: rows.append('')
            rows[-1]+=(' ' if rows[-1] else '')+word
        for j,row in enumerate(rows[:3]):
            parts.append(f'<text x="{x+14}" y="{y+24+j*17}" font-family="sans-serif" font-size="14" fill="#eff6ff">{html.escape(row)}</text>')
    parts.append('</svg>')
    (folder/'execution.svg').write_text(''.join(parts),encoding='utf-8')
