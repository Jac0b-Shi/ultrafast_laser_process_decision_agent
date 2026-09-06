"""Markdown -> journal Typst -> PDF. No Word/host Python dependency."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
ROOT=Path('/workspace')
OUT=ROOT/'docs/research/english'
TITLE='AI-Bridged Data-Knowledge Fusion for Intelligent Laser Parameter Recommendation in Ultrafast Laser Processing'
source=OUT/(TITLE+'.md');pdf=OUT/(TITLE+'.pdf');build=OUT/'build';build.mkdir(exist_ok=True)
archive=OUT/'archive';archive.mkdir(exist_ok=True)
if pdf.exists() and not (archive/(TITLE+' - single-column.pdf')).exists():shutil.copy2(pdf,archive/(TITLE+' - single-column.pdf'))
text=subprocess.check_output(['pandoc',str(source),'-t','typst'],text=True)
intro=text.index('== 1. Introduction')
abstract=text[text.index('<abstract>')+len('<abstract>'):intro].strip()
body=text[intro:]
# Attach table captions to their floats rather than leaving detached body paragraphs.
body=re.sub(r'\n(Table \d+\. .*?)\n\n#figure\(',lambda m:'\n#figure(caption: ['+m.group(1)+'], ',body,flags=re.S)
body=body.replace('#figure(', '#figure(scope: "parent", placement: auto, numbering: none, ')
body=body.replace('#figure(scope: "parent", placement: auto, numbering: none, image("figures/mechanism_gain.png"','#figure(scope: "column", placement: auto, numbering: none, image("figures/mechanism_gain.png"')
body=re.sub(r'image\("figures/([^\"]+)\.png",',r'image("journal-figures/\1.svg", width: 100%,',body)
body=body.replace('== ', '= ').replace('=== ', '== ')
body=body.replace(r'\,#h(2em) S_(m a t c h)', ' $\n\n$ S_(m a t c h)')
header='''#set document(title: "%s")
#set page(paper: "a4", margin: (x: 15mm, y: 17mm), columns: 2, numbering: "1")
#set columns(gutter: 5mm)
#set text(font: "Libertinus Serif", size: 10pt, lang: "en")
#set par(justify: true, leading: 0.58em, spacing: 0.65em)
#set heading(numbering: none)
#show heading.where(level: 1): set text(size: 11pt, weight: "bold")
#show heading.where(level: 2): set text(size: 10pt, weight: "bold")
#set figure(gap: 5pt)
#show figure.caption: set text(size: 9pt)
#show figure.where(kind: table): set text(size: 9pt)
#set table(stroke: none, inset: (x: 4pt, y: 4pt))
#show table.cell.where(y: 0): set text(weight: "bold")
#show math.equation.where(block: true): set text(size: 9pt)
#place(top, scope: "parent", float: true)[
#align(center)[#text(size: 17pt, weight: "bold")[%s]]
#v(8pt)
#text(size: 9.5pt)[*Abstract*\n\n%s]
#v(8pt)
]
'''%(TITLE,TITLE,abstract)
typ=build/'journal.typ';typ.write_text(header+body,encoding='utf-8')
subprocess.run(['typst','compile','--root',str(ROOT),str(typ),str(pdf)],check=True)
(build/'journal-provenance.json').write_text(json.dumps({'markdown_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'pdf':pdf.name,'columns':2,'font_size_pt':10,'gutter_mm':5,'figure_scope':{'1':'parent','2':'column','3':'parent','4':'parent'},'figure_min_font_pt':8},indent=2))
print(pdf)
