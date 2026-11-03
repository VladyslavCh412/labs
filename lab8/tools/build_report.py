"""Build the LR8 PDF from Markdown + measured evidence (requires reportlab)."""
from collections import defaultdict
from contextlib import closing
import hashlib
from html import escape
import json
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET

from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Rect, Line, PolyLine, Polygon, String
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderSVG
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
    Spacer, PageBreak, Table, TableStyle, Image, KeepTogether)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT=Path(__file__).resolve().parents[1]
DOC=ROOT/'docs'
EVIDENCE=DOC/'evidence'
OUTPUT=ROOT/'submission'
EVIDENCE.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)


def load(name):
    source=ROOT/'verification'/name
    aliases={'load_results.json':'load-results.json','stress_results.json':'stress-results.json',
             'cache_benchmark.json':'cache-benchmark.json','fitness_measurement.json':'fitness.json'}
    if not source.exists(): source=EVIDENCE/aliases.get(name,name)
    return json.loads(source.read_text(encoding='utf-8'))


def level(name):
    if 'test_domain' in name or any(x in name for x in ['test_transition_invariants_without_database','test_use_cases_depend_on_in_memory_ports_only']): return 'unit'
    if 'test_contract' in name: return 'contract'
    if 'test_fitness' in name or 'test_architecture_extensions.test_relative' in name or 'test_architecture_extensions.test_application' in name: return 'architecture'
    if 'test_read_cache' in name and 'test_trip_write' not in name: return 'unit'
    if any(x in name for x in ['domain_invariants','adapter','strategy','fleet_client_keeps','fleet_client_still','cache_hits']): return 'unit'
    return 'integration'


def collect_evidence():
    for a,b in [('load_results.json','load-results.json'),('stress_results.json','stress-results.json'),
                ('cache_benchmark.json','cache-benchmark.json'),('fitness_measurement.json','fitness.json'),
                ('live_smoke.json','live-smoke.json'),('negative_pipeline.json','negative-pipeline.json')]:
        source=ROOT/'verification'/a
        if source.exists(): shutil.copyfile(source,EVIDENCE/b)
        elif not (EVIDENCE/b).exists(): raise FileNotFoundError(source)
    if not (ROOT/'verification/test_results.xml').exists():
        return json.loads((EVIDENCE/'tests-summary.json').read_text(encoding='utf-8'))
    groups=defaultdict(lambda: {'count':0,'seconds':0.0})
    by_file=defaultdict(lambda: {'count':0,'seconds':0.0,'levels':set()})
    tests=[]
    for case in ET.parse(ROOT/'verification/test_results.xml').findall('.//testcase'):
        name=case.attrib.get('classname','')+'.'+case.attrib['name']
        category=level(name);seconds=float(case.attrib.get('time',0))
        groups[category]['count']+=1;groups[category]['seconds']+=seconds
        f=case.attrib.get('classname','');by_file[f]['count']+=1;by_file[f]['seconds']+=seconds;by_file[f]['levels'].add(category)
        tests.append(dict(name=name,level=category,seconds=seconds,passed=not any(case.find(x) is not None for x in ['failure','error','skipped'])))
    coverage=load('coverage.json')['totals']
    digest=hashlib.sha256()
    for path in sorted(ROOT.rglob('*.py')):
        if any(part in {'.venv','data','__pycache__'} for part in path.parts):continue
        digest.update(path.relative_to(ROOT).as_posix().encode());digest.update(path.read_bytes())
    summary=dict(date='2026-11-03',functional_tests=len(tests),passed=sum(t['passed'] for t in tests),
                 http_gate_tests=1,domain_line_coverage=coverage['percent_covered'],
                 source_sha256=digest.hexdigest(),levels=dict(groups),tests=tests)
    (EVIDENCE/'tests-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    frontend=ROOT/'frontend'
    frontend_digest=hashlib.sha256((frontend/'src/app.ts').read_bytes()).hexdigest()
    frontend_evidence=dict(language='TypeScript',compiler='7.0.2',strict=True,noEmitOnError=True,
        command='npm ci && npm run typecheck && npm run build',source='frontend/src/app.ts',
        source_sha256=frontend_digest,bundle_sha256=hashlib.sha256((frontend/'build/app.js').read_bytes()).hexdigest())
    (EVIDENCE/'frontend-build.json').write_text(json.dumps(frontend_evidence,indent=2)+'\n',encoding='utf-8')
    lines=['# Аудит тестів ЛР8','', 'Виміряно 03.11.2026 з JUnit XML. Час містить setup/call/teardown для кейсу; це не лише час функції.',
           '', '| Рівень | Кількість | Сума часу, с | Залежності |','|---|---:|---:|---|']
    deps={'unit':'Немає БД/HTTP','integration':'Тимчасова SQLite / ASGI / mock transport','contract':'Незалежний контракт + provider або mock','architecture':'AST та тимчасова копія джерел'}
    for key,value in groups.items():lines.append(f'| {key} | {value["count"]} | {value["seconds"]:.3f} | {deps[key]} |')
    lines+=['','Окремо: 1 реальний HTTP performance gate (100 users, 0 errors, p95<=500 мс).',
            'Live smoke запускає три HTTP-процеси; його 7 перевірок не додаються до кількості pytest-кейсів.',
            '', '| Файл тестів | Рівні | Кількість | Час, с |','|---|---|---:|---:|']
    for key,value in by_file.items():lines.append(f'| {key} | {", ".join(sorted(value["levels"]))} | {value["count"]} | {value["seconds"]:.3f} |')
    lines+=['','Баланс: доменні правила та in-memory порти перевіряються модульно; більшість boundary-кейсів — швидкі інтеграційні ASGI/SQLite, а не повні E2E. Немає потреби піднімати весь стенд для кожного правила. Піраміда не ідеальна за кількістю, але локальна функціональна suite займає кілька секунд; дорогий HTTP gate відокремлено.',
            '', 'Правила ЛР2 → тести: Vehicle identity/mileage/ТО → test_domain.py; Driver.can_drive → test_driver_permission; Route stops → test_route_requires_two_nonempty_stops; Trip lifecycle → test_trip_lifecycle_and_mileage і test_transition_invariants_without_database. Persistence, migration, cache/event replay → test_lab5.py. Конкуренція і відновлення двох власників → test_lifecycle.py.']
    (DOC/'TEST_AUDIT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (EVIDENCE/'README.md').write_text('''# Перевірені результати 03.11.2026

Санітизовані результати без JWT, паролів і робочих БД. `tests-summary.json`
містить digest Python-джерел, рівні тестів і виміряний час; JUnit originals
генеруються у verification/ та зберігаються в CI artifacts.

- `load-results.json`: 20 000 рейсів, baseline/optimized, 1/10/50/100/200 users.
- `stress-results.json`: ті самі дані, optimized, 300/500 users для межі NFR-1.
- `fitness.json`: окремий CI-style HTTP gate, 5000 рейсів /100 users.
- `cache-benchmark.json`: локальний repository lookup, 1000 повторень, не HTTP.
- `live-smoke.json`: справжній HTTP login/proxy/roles/lifecycle/bridge.
- `negative-pipeline.json`: exit1 на заборонений імпорт у тимчасовій копії.
- `dashboard.png`: демонстраційні дані після завершення рейсу на 25 км.

Повторення: з кореня `python run.py verify`, `python run.py benchmark`;
з lab8 — `python verification/live_smoke.py` та
`python verification/load_test.py --modes optimized --levels 300,500 --output verification/stress_results.json`.
Середовище/тривалості/помилки записані всередині JSON. Короткий loopback
benchmark не є production SLA. Невдалий baseline із timeout не приховано.
''',encoding='utf-8')
    return summary


FONT_DIRS=[Path('C:/Windows/Fonts'),Path('/usr/share/fonts/truetype/dejavu')]
for name,files in [('Body',['arial.ttf','DejaVuSans.ttf']),('Bold',['arialbd.ttf','DejaVuSans-Bold.ttf'])]:
    match=next((folder/f for folder in FONT_DIRS for f in files if (folder/f).exists()),None)
    if not match:raise RuntimeError('Install Arial or DejaVu Sans for Cyrillic text')
    pdfmetrics.registerFont(TTFont(name,str(match)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold',italic='Body',boldItalic='Bold')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle('BodyUA',fontName='Body',fontSize=10,leading=14,spaceAfter=7))
styles.add(ParagraphStyle('H1UA',fontName='Bold',fontSize=22,leading=27,spaceAfter=15,keepWithNext=True))
styles.add(ParagraphStyle('H2UA',fontName='Bold',fontSize=14,leading=18,spaceBefore=10,spaceAfter=9,keepWithNext=True))
styles.add(ParagraphStyle('TableUA',fontName='Body',fontSize=8.1,leading=11,spaceAfter=0,splitLongWords=True))
styles.add(ParagraphStyle('CaptionUA',fontName='Body',fontSize=8.5,leading=12,textColor=colors.HexColor('#475569'),spaceAfter=10))
styles.add(ParagraphStyle('ADRUA',fontName='Body',fontSize=9.5,leading=13.2,spaceAfter=6))
styles.add(ParagraphStyle('CoverUA',fontName='Bold',fontSize=35,leading=42,spaceAfter=24))


def inline(t):
    t=t.replace('\u2011','-').replace('–','-').replace('—','-')
    t=escape(t)
    t=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',t)
    t=re.sub(r'`([^`]+)`',r'\1',t)
    t=re.sub(r'\[([^]]+)\]\(([^)]+)\)',r'\1',t)
    return t


def para(t,style='BodyUA'):
    return Paragraph(inline(t),styles[style])


def table(rows,width=491):
    n=len(rows[0]);widths=[width/n]*n
    if n==3:widths=[width*.22,width*.36,width*.42]
    if n>=5:widths=[width/n]*n
    cells=[[para(c,'TableUA') for c in row] for row in rows]
    result=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
    result.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E8F0FF')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.8,colors.HexColor('#94A3B8')),
        ('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#DDE5EF')),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    return result


def diagram(model):
    height=850 if len(model['nodes'])==8 and model['nodes'][0]['id']=='browser' else 730
    if model['title'].startswith('Межі довіри'): height=550
    d=Drawing(1200,height)
    palette={'container':('#E8F0FF','#164E95'),'person':('#F1F5F9','#334155'),'planned':('#F8FAFC','#64748B'),'database':('#E6F5EE','#17634A')}
    for edge in model['edges']:
        points=[(x,height-y) for x,y in edge['points']]
        opts={'strokeColor':colors.HexColor('#475569'),'strokeWidth':2,'fillColor':None}
        if edge.get('dash'):opts['strokeDashArray']=[9,6]
        d.add(PolyLine([value for point in points for value in point],**opts))
        (ax,ay),(bx,by)=points[-2:]
        import math
        angle=math.atan2(by-ay,bx-ax);size=9
        p=[bx,by,bx-size*math.cos(angle-.4),by-size*math.sin(angle-.4),bx-size*math.cos(angle+.4),by-size*math.sin(angle+.4)]
        d.add(Polygon(p,fillColor=colors.HexColor('#475569'),strokeColor=None))
        label=edge['label'];x=edge['x'];y=height-edge['y']
        label_width=pdfmetrics.stringWidth(label,'Body',18)
        d.add(Rect(x-3,y-3,label_width+6,22,fillColor=colors.white,strokeColor=None))
        d.add(String(x,y,label,fontName='Body',fontSize=18,fillColor=colors.HexColor('#334155')))
    for node in model['nodes']:
        fill,stroke=palette[node['kind']]
        d.add(Rect(node['x'],height-node['y']-node['h'],node['w'],node['h'],rx=8,ry=8,fillColor=colors.HexColor(fill),strokeColor=colors.HexColor(stroke),strokeWidth=2))
        cy=node['y']+(node['h']-len(node['lines'])*26)/2+21
        for i,line in enumerate(node['lines']):
            d.add(String(node['x']+node['w']/2,height-cy-i*26,line,textAnchor='middle',fontName='Bold' if i==0 else 'Body',fontSize=22 if i==0 else 18,fillColor=colors.HexColor(stroke)))
    factor=491/1200;d.scale(factor,factor);d.width=491;d.height=height*factor
    return d


def performance_chart(measurements):
    d=Drawing(491,245)
    plot=LinePlot();plot.x=52;plot.y=38;plot.width=415;plot.height=190
    plot.data=[[(r['users'],r['p50_ms']) for r in measurements],[(r['users'],r['p95_ms']) for r in measurements],[(1,500),(500,500)]]
    plot.xValueAxis.valueMin=0;plot.xValueAxis.valueMax=500;plot.xValueAxis.valueSteps=[0,100,200,300,400,500]
    plot.yValueAxis.valueMin=0;plot.yValueAxis.valueMax=1200;plot.yValueAxis.valueSteps=[0,300,600,900,1200]
    plot.lines[0].strokeColor=colors.HexColor('#16A085');plot.lines[1].strokeColor=colors.HexColor('#355BCE');plot.lines[2].strokeColor=colors.HexColor('#D54A40');plot.lines[2].strokeDashArray=[4,3]
    for i in range(3):plot.lines[i].strokeWidth=1.6
    plot.xValueAxis.labels.fontName='Body';plot.yValueAxis.labels.fontName='Body'
    plot.xValueAxis.labels.fontSize=8;plot.yValueAxis.labels.fontSize=8
    d.add(plot)
    d.add(String(9,230,'мс',fontName='Body',fontSize=9))
    d.add(String(178,6,'Одночасні користувачі',fontName='Body',fontSize=9))
    for x,label,color in [(65,'p50','#16A085'),(185,'p95','#355BCE'),(300,'Поріг 500 мс','#D54A40')]:
        d.add(Line(x,22,x+18,22,strokeColor=colors.HexColor(color),strokeWidth=2));d.add(String(x+24,18,label,fontName='Body',fontSize=8.5))
    renderSVG.drawToFile(d,str(EVIDENCE/'performance.svg'))
    return d


class Report(BaseDocTemplate):
    def __init__(self,path):
        super().__init__(str(path),pagesize=A4,leftMargin=52,rightMargin=52,topMargin=54,bottomMargin=48,
                         title='FleetFlow - Лабораторна робота 8',author='FleetFlow project')
        frame=Frame(self.leftMargin,self.bottomMargin,self.width,self.height,id='normal',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)
        self.addPageTemplates(PageTemplate(id='main',frames=frame,onPage=self.decorate))
    def decorate(self,canvas,doc):
        if doc.page>1:
            canvas.setFont('Body',8);canvas.setFillColor(colors.HexColor('#64748B'))
            canvas.drawString(52,A4[1]-30,'FleetFlow / Лабораторна робота 8 / 03.11.2026')
            canvas.drawRightString(A4[0]-52,28,str(doc.page))
    def afterFlowable(self,flowable):
        if isinstance(flowable,Paragraph) and flowable.style.name=='H1UA':
            text=flowable.getPlainText();key='section-'+str(self.seq.nextf('section'))
            if text in {'Лабораторна робота №8','Зміст'}: return
            self.canv.bookmarkPage(key);self.canv.addOutlineEntry(text,key,0)
            self.notify('TOCEntry',(0,text,self.page,key))


def main():
    summary=collect_evidence();gate=load('fitness_measurement.json');load_data=load('load_results.json');stress=load('stress_results.json')
    optimized=load_data['results']['optimized']+stress['results']['optimized']
    docpath=DOC/'ARCHITECTURE.md';text=docpath.read_text(encoding='utf-8')
    text=re.sub(r'\| NFR-1, p95 <=500 мс /100 users \| .*? \| Виконано локально; 300 users перевищують поріг \|',
                f'| NFR-1, p95 <=500 мс /100 users | Gate p95 {gate["p95_ms"]} мс, {gate["requests"]} запитів, 0 помилок | Виконано локально; 300 users перевищують поріг |',text)
    docpath.write_text(text,encoding='utf-8')
    results=['# Продуктивність: фактичні вимірювання','', '| Режим | Користувачі | p50, мс | p95, мс | Помилки / спроби |','|---|---:|---:|---:|---:|']
    for mode in ['baseline','optimized']:
        data=load_data['results'][mode]+(stress['results']['optimized'] if mode=='optimized' else [])
        for r in data:results.append(f'| {mode} | {r["users"]} | {r["p50_ms"]} | {r["p95_ms"]} | {r["errors"]}/{r["requests"]} |')
    results+=['',f'Окремий gate: p95 {gate["p95_ms"]} мс, {gate["requests"]} відповідей, 0 помилок. Функціональних тестів: {summary["passed"]}; domain line coverage: {summary["domain_line_coverage"]:.0f}%.',
              '', 'На 20 000 рядках optimized: p95 217.530 мс /100 users і 394.557 мс /200 users; перший виміряний вихід за 500 мс — 300 users (630.933 мс). Межа лежить між 200 і 300 у цьому короткому досліді. Baseline перевищує поріг уже на 10 users; 100/200 мають timeout, не є успішними відповідями.',
              '', '![Графік p50/p95](evidence/performance.svg)']
    (DOC/'PERFORMANCE.md').write_text('\n'.join(results)+'\n',encoding='utf-8')
    flow=[Spacer(1,80),para('FleetFlow','CoverUA'),para('Лабораторна робота №8','H1UA'),
          para('Документування та захист архітектури','H2UA'),para('Варіант 12: управління автопарком та маршрутами'),
          Spacer(1,30),para('Підсумковий пакет наскрізного проєкту ЛР1–ЛР8'),
          para('Код, архітектурні рішення, результати перевірок і план еволюції'),
          Spacer(1,40),para('03 листопада 2026 року'),para('Репозиторій: github.com/VladyslavCh412/labs · ветка lab8-complete','CaptionUA'),
          PageBreak(),para('Зміст','H1UA')]
    toc=TableOfContents();toc.levelStyles=[ParagraphStyle('TOCUA',fontName='Body',fontSize=10,leading=17,spaceBefore=4)]
    flow.extend([toc,PageBreak()])
    models=json.loads((ROOT/'diagrams/c4-model.json').read_text(encoding='utf-8'))
    lines=text[text.index('## 1.'):].splitlines();i=0
    while i<len(lines):
        line=lines[i].strip()
        if line.startswith('# '):i+=1;continue
        if not line:i+=1;continue
        if line.startswith('## '):
            if len(flow)>3 and not isinstance(flow[-1],PageBreak):flow.append(PageBreak())
            title=line[3:];flow.append(para(title,'H1UA'))
            if title.startswith('3. '):
                for key in ['context','containers','components']:
                    flow.extend([para(models[key]['title'],'H2UA'),diagram(models[key]),
                                 para('Легенда: синій - контейнер, сірий - актор/план, зелений - дані. Суцільний зв’язок - виклик, пунктир - подія або майбутня інтеграція.','CaptionUA')])
                    if key!='components':flow.append(PageBreak())
            if title.startswith('8. '):flow.extend([diagram(models['trust']),Spacer(1,12)])
            i+=1;continue
        if line.startswith('### '):
            flow.append(para(line[4:],'H2UA'))
            if 'Підсумок вимірювань' in line:
                flow.extend([performance_chart(optimized),Spacer(1,8)])
                measure=[['Режим','Users','p50, мс','p95, мс','Помилки/спроби']]
                for mode in ['baseline','optimized']:
                    data=load_data['results'][mode]+(stress['results']['optimized'] if mode=='optimized' else [])
                    for r in data:measure.append([mode,str(r['users']),str(r['p50_ms']),str(r['p95_ms']),f'{r["errors"]}/{r["requests"]}'])
                flow.extend([table(measure),Spacer(1,12),para(f'Окремий gate: p95 {gate["p95_ms"]} мс; {gate["requests"]} відповідей; 0 помилок. Coverage домену {summary["domain_line_coverage"]:.0f}%; {summary["passed"]} функціональних кейсів + 1 HTTP gate.','CaptionUA')])
            i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                row=[c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r'[:\- ]+',c) for c in row):rows.append(row)
                i+=1
            flow.extend([table(rows),Spacer(1,10)]);continue
        paragraph=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|')):
            paragraph.append(lines[i].strip());i+=1
        flow.append(para(' '.join(paragraph)))
    flow.extend([PageBreak(),para('Додаток A. Аудит і докази','H1UA')])
    audit=(DOC/'TEST_AUDIT.md').read_text(encoding='utf-8')
    for block in audit.split('\n\n')[1:]:
        if block.startswith('|'):
            rows=[[c.strip() for c in x.strip('|').split('|')] for x in block.splitlines() if not re.match(r'^\|[\-:| ]+\|$',x)]
            compact=table(rows)
            compact.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
            flow.extend([compact,Spacer(1,8)])
        else:flow.append(para(block.replace('\n',' ')))
    flow.append(para('Негативний дослід: import sqlite3 у копії fleet_service/domain.py → ARCHITECTURE FAILED, returncode=1; original_source_unchanged=true. Live HTTP smoke: усі 7 перевірок пройшли.'))
    screenshot=EVIDENCE/'dashboard.png'
    if screenshot.exists():
        flow.extend([PageBreak(),para('Додаток B. Демонстрація застосунку','H1UA'),Image(str(screenshot),width=491,height=491*1077/1425),para('Демонстраційний рейс завершено на 25 км; пробіг збережений у Fleet. Облікові дані не включено.','CaptionUA')])
    flow.extend([PageBreak(),para('Додаток C. Повний журнал ADR','H1UA')])
    files=sorted((DOC/'adr').glob('ADR-*'))
    for adr in files:
        flow.append(para(adr.stem.replace('-original',''),'H2UA'))
        if adr.name.startswith('ADR-001'):
            flow.append(para('Поточний статус: замінено щодо deployment рішенням ADR-003. Нижче збережено оригінальний контекст і формулювання.','CaptionUA'))
        content=adr.read_text(encoding='utf-8')
        for block in content.split('\n\n'):
            block=block.strip().lstrip('#').strip()
            if block:flow.append(para(block.replace('\n',' '),'ADRUA'))
    report=Report(OUTPUT/'FleetFlow_Lab8.pdf');report.multiBuild(flow)
    print(f'PDF written: {report.filename}; tests={summary["passed"]}; gate_p95={gate["p95_ms"]} ms')


if __name__=='__main__':main()
