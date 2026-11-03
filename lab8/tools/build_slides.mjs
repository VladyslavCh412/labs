// Optional authoring helper for the Codex bundled @oai/artifact-tool runtime.
// Set RUNTIME_NODE_MODULES and PRESENTATIONS_SKILL_DIR before running.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL,fileURLToPath} from 'node:url';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const modules=process.env.RUNTIME_NODE_MODULES;
const skill=process.env.PRESENTATIONS_SKILL_DIR;
if(!modules||!skill)throw new Error('Set RUNTIME_NODE_MODULES and PRESENTATIONS_SKILL_DIR');
const require=createRequire(path.join(modules,'__runtime__.cjs'));
const {Presentation,PresentationFile}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
const {applyPresentationChartFont,finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const build=path.resolve(ROOT,'.runtime/slides',String(Date.now()));
await fs.mkdir(build,{recursive:true});
const json=async name=>JSON.parse(await fs.readFile(path.join(ROOT,'docs/evidence',name),'utf8'));
const load=await json('load-results.json'),stress=await json('stress-results.json'),gate=await json('fitness.json'),tests=await json('tests-summary.json');
const optimized=[...load.results.optimized,...stress.results.optimized];
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={ink:'#102C46',muted:'#526479',blue:'#214EAD',green:'#196B56',line:'#7C8B9C',background:'#FFFFFF'};
const notes=[];
function text(slide,value,x,y,w,h,size=28,bold=false,color=C.ink,align='left'){
 const s=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 s.text=value;s.text.style={typeface:'Arial',fontSize:size,bold,color};s.text.alignment=align;s.text.insets=0;return s;
}
function slide(title,note){const s=p.slides.add();s.background.fill=C.background;
 text(s,title,64,40,1152,74,46,true);
 const number=p.slides.items.length;text(s,String(number).padStart(2,'0'),1160,674,55,25,18,false,C.muted,'right');
 s.speakerNotes.text=note;notes.push({slide:number,title,note});return s;
}
function box(s,id,lines,x,y,w=300,h=82,kind='service'){
 const fill=kind==='data'?'#E8F4EE':kind==='external'?'#F0F3F6':'#EAF0FC';
 const stroke=kind==='data'?C.green:kind==='external'?C.muted:C.blue;
 const shape=s.shapes.add({geometry:'rect',name:id,position:{left:x,top:y,width:w,height:h},fill,line:{fill:stroke,width:1.6}});
 const first=lines[0],rest=lines.slice(1).join('\n');
 text(s,first,x+12,y+12,w-24,34,26,true,stroke,'center');
 if(rest)text(s,rest,x+10,y+46,w-20,h-47,22,false,stroke,'center');
 return shape;
}
function link(s,from,to,label,x,y,{fromSide='bottom',toSide='top',dash=false,w=290}={}){
 s.shapes.connect(from,to,{kind:'elbow',fromSide,toSide,line:{fill:C.line,width:1.8,style:dash?'dash':'solid'},tail:{type:'triangle',width:'sm',length:'sm'}});
 if(label)text(s,label,x,y,w,30,21,false,C.muted);
}

// 1: a minimal cover.
{
const s=p.slides.add();s.background.fill='#102C46';
text(s,'FleetFlow',80,180,1120,110,84,true,'#FFFFFF');
text(s,'Управління автопарком та маршрутами',84,315,1060,112,44,false,'#E1EBF5');
text(s,'Лабораторна робота 8 · Варіант 12',84,515,1080,45,28,false,'#AFC6DD');
text(s,'Самостійний кінцевий продукт · ЛР8 · 03.11.2026',84,575,1110,45,24,false,'#AFC6DD');
s.speakerNotes.text='0:00–0:40. Призначення: локальна система обліку ТЗ, водіїв, маршрутів та життєвого циклу рейсу. Матеріали: docs/ARCHITECTURE.md, поточний lab8. Звіти для ЛР1–ЛР7 не створювалися.';
notes.push({slide:1,title:'FleetFlow',note:s.speakerNotes.text});
}
// 2: context; only one system at C4 level 1.
{
const s=slide('Контекст системи','0:40–1:30. Один прямокутник FleetFlow на L1. Реалізовані актори manager/dispatcher/viewer. GPS, карти і SMS/e-mail лишаються планом. Джерело: diagrams/context.mmd; ARCHITECTURE.md §§1–3.');
const a=box(s,'manager',['Керівник','manager'],65,155,320,84,'external');
const b=box(s,'dispatcher',['Диспетчер','dispatcher'],480,155,320,84,'external');
const c=box(s,'viewer',['Спостерігач','viewer'],895,155,320,84,'external');
const core=box(s,'system',['FleetFlow','Software System'],420,340,440,105);
link(s,a,core,'Автопарк',130,277,{w:230});link(s,b,core,'Рейси та маршрути',665,280,{w:300});link(s,c,core,'Перегляд',1010,277,{w:200});
text(s,'Заплановані зовнішні інтеграції',65,520,1140,38,28,true,C.muted);
text(s,'Картографія     ·     GPS / телематика     ·     SMS / e-mail',65,580,1140,50,29,false,C.muted);
}
// 3: containers, including separately running owner workers.
{
const s=slide('Контейнери та власники даних','1:30–2:50. Dashboard є єдиним входом. Fleet/Trips — окремі процеси з незалежними SQLite. Bridge використовує HTTP; Trips Worker читає тільки свою БД. GET і команди мають timeout0.35. Джерело: diagrams/containers.mmd, ADR-003/005/011.');
const browser=box(s,'browser',['Браузер','TypeScript → JS'],65,145,280,78,'external');
const gateway=box(s,'gateway',['Gateway + Auth','FastAPI :8000'],485,145,320,78);
const fleet=box(s,'fleet',['Fleet API','FastAPI :8101'],65,325,320,78);
const trips=box(s,'trips',['Trips API','FastAPI :8102'],895,325,320,78);
const fd=box(s,'fleet-db',['Fleet SQLite','ТЗ / водії / outbox'],65,570,320,78,'data');
const td=box(s,'trips-db',['Trips SQLite','Рейси / проєкція'],895,570,320,78,'data');
const bridge=box(s,'bridge',['Event Bridge','HTTP / polling'],485,515,320,78);
const worker=box(s,'worker',['Trips Worker','TripCreated'],895,445,320,78);
link(s,browser,gateway,'HTTP + JWT',355,164,{fromSide:'right',toSide:'left',w:130});
link(s,gateway,fleet,'HTTP + JWT',165,265,{w:250});link(s,gateway,trips,'HTTP + JWT',965,265,{w:230});
link(s,trips,fleet,'GET + команди · timeout 0,35 с',420,340,{fromSide:'left',toSide:'right',w:455});
link(s,fleet,fd,'SQL',92,470,{w:70});link(s,worker,td,'SQL',1160,535,{w:70});
link(s,trips,td,'SQL',820,480,{fromSide:'left',toSide:'left',w:65});
link(s,bridge,fleet,'outbox / ack',415,435,{fromSide:'left',toSide:'right',dash:true,w:190});
link(s,bridge,trips,'Подія',720,435,{fromSide:'right',toSide:'left',dash:true,w:140});
text(s,'Легенда: синій — контейнер · зелений — дані · пунктир — асинхронна доставка',65,678,1080,28,18,false,C.muted);
}
// 4: native editable component diagram.
{
const s=slide('Компоненти контейнера Trips','2:50–3:40. Деталізовано один найскладніший контейнер. UseCases залежать тільки від доменних портів. Factory збирає залежності, Adapter приховує JSON, Observer ізолює споживача. Джерело: application.py, factory.py, diagrams/components.mmd.');
const cache=box(s,'cache',['TripPageCache','TTL 1 с / 128 ключів'],65,160,320,82);
const api=box(s,'api',['HTTP + JWT','FastAPI / DTO'],480,160,320,82);
const domain=box(s,'domain',['Domain + Ports','Trip / Route / Protocol'],65,365,320,82);
const app=box(s,'usecases',['TripUseCases','create / start / complete'],480,365,320,82);
const client=box(s,'fleet-client',['FleetClient + Adapter','HTTP / timeout'],895,365,320,82);
const observer=box(s,'observer',['EventPublisher','Observer'],65,565,320,82);
const repo=box(s,'repository',['TripsRepository','SQLite / receipts / inbox'],480,565,320,82,'data');
const factory=box(s,'factory',['ComponentsFactory','Composition root'],895,565,320,82);
link(s,api,app,'Use cases',665,295,{w:180});link(s,api,cache,'Read cache',180,270,{fromSide:'left',toSide:'right',w:240});
link(s,app,domain,'Порти',310,330,{fromSide:'left',toSide:'right',w:140});
link(s,app,client,'FleetGateway',840,330,{fromSide:'right',toSide:'left',w:280});
link(s,app,repo,'TripStore',665,495,{w:200});link(s,repo,observer,'TripCreated',245,520,{fromSide:'left',toSide:'right',dash:true,w:230});
link(s,factory,client,'DI',1150,495,{w:70});
}
// 5: two concrete decisions and their alternatives.
{
const s=slide('Два ключові архітектурні рішення','3:40–4:50. ADR-003 замінює deployment ADR-001, але не стирає історію. ADR-011 відхиляє спільну БД та 2PC для навчального стенду. Повтор команд відновлює стан після remote commit. Залишковий борг: автоматичний reconciler.');
text(s,'ADR-003: Fleet + Trips',65,165,550,55,34,true,C.blue);
text(s,'Альтернативи: моноліт, два сервіси, 5+ сервісів.\n\nРішення: два доменні контексти, кожен володіє своїми даними.\n\nЦіна: мережеві відмови й локальні транзакції.',65,245,535,365,28);
text(s,'ADR-011: безпечний повтор',685,165,530,55,34,true,C.blue);
text(s,'Альтернативи: спільна БД, 2PC, квитанції команд.\n\nРішення: trip_id + operation, receipt і зміна ТЗ в одній транзакції.\n\nЦіна: тимчасова неузгодженість; після збою повторюємо ту саму дію.',685,245,530,365,28);
}
// 6: data and enforced trust boundary.
{
const s=slide('Дані, події та безпека','4:50–5:50. Fleet змінює лише свою БД, Trips — свою. Outbox/inbox, version та event_id дають безпечний replay. Ролі перевіряються у власника навіть при прямому виклику. Джерело: ADR-005/006/011, security.py, tests/test_security.py.');
text(s,'Узгодженість',65,160,535,55,34,true,C.green);
text(s,'ТЗ + outbox — одна транзакція.\n\nBridge: ack лише після успіху Trips.\n\nInbox: event_id унікальний; старі версії не відкочують проєкцію.\n\nКеші: TTL + інвалідація при зміні.',65,245,535,370,28);
text(s,'Межа довіри',685,160,535,55,34,true,C.blue);
text(s,'Argon2id + JWT на 15 хвилин.\n\nmanager / dispatcher / viewer.\n\nJWT і RBAC у Fleet та Trips.\n\nВнутрішні команди — тільки trips-service; людський manager не має цього права.',685,245,530,370,28);
}
// 7: native editable chart, same measurements as the PDF.
{
const s=slide('Продуктивність: ціль і вимірювання','5:50–6:50. Джерела: docs/evidence/load-results.json (20k rows), stress-results.json, fitness.json. Усі optimized stages мають 0 errors. 200 users p95=394.557; 300 users p95=630.933. Baseline вже на 10 users p95=2657.585; 100/200 мають timeout. Це короткий loopback дослід, не production SLA.');
const chart=s.charts.add('line',{position:{left:58,top:160,width:800,height:445},title:'Оптимізований API: p50 та p95, мс',titleTextStyle:{fontSize:24,typeface:'Arial'},
 categories:optimized.map(r=>String(r.users)),series:[
 {name:'p50',values:optimized.map(r=>r.p50_ms),line:{fill:'#19856A',width:3}},
 {name:'p95',values:optimized.map(r=>r.p95_ms),line:{fill:'#214EAD',width:3}},
 {name:'Поріг 500 мс',values:optimized.map(()=>500),line:{fill:'#C64A45',width:2}}],
 hasLegend:true,legend:{position:'bottom',textStyle:{fontSize:22,typeface:'Arial'}},
 xAxis:{title:{text:'Одночасні користувачі',textStyle:{fontSize:20,typeface:'Arial'}},textStyle:{fontSize:20,typeface:'Arial'}},
 yAxis:{minimumScale:0,maximumScale:1200,textStyle:{fontSize:20,typeface:'Arial'},majorGridlines:{fill:'#D9E2EC',width:1}},chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'});
applyPresentationChartFont(chart,{fontFamily:'Arial'});
text(s,`${gate.p95_ms.toFixed(1)} мс`,905,190,315,70,50,true,C.blue);
text(s,'p95 HTTP gate\n100 користувачів',905,270,300,90,28);
text(s,'200 → 300',905,410,310,65,42,true,C.ink);
text(s,'між цими рівнями\nперевищено 500 мс',905,480,310,100,28);
text(s,'20 000 рядків · 1 worker · 3 с/етап · локальний стенд · 03.11.2026',65,635,1140,35,23,false,C.muted);
}
// 8: distinguish the test counts from independent smoke assertions.
{
const s=slide('Тести та автоматичні архітектурні межі','6:50–7:50. 85 functional cases and 1 isolated HTTP gate; 100% domain line coverage. Negative pipeline returns1 in disposable copy, source unchanged. 9 independent live-smoke assertions are not added to pytest count. Джерела: tests-summary.json, negative-pipeline.json, .github/workflows/architecture.yml.');
text(s,`${tests.functional_tests} + 1`,65,170,470,100,76,true,C.blue);
text(s,'функціональні кейси + HTTP gate',65,290,550,80,30);
text(s,`${tests.domain_line_coverage.toFixed(0)}%`,725,170,480,100,76,true,C.green);
text(s,'line coverage доменних модулів',725,290,485,80,30);
text(s,'0 infrastructure imports у домені та application\n0 циклів між модулями\nOpenAPI відповідає виконуваному API',65,425,1130,130,29);
text(s,'Навмисний import sqlite3 → конвеєр падає з exit 1',65,605,1130,55,29,true,C.ink);
}
// 9: ordered evolution with explicit triggers.
{
const s=slide('Технічний борг і наступні кроки','7:50–9:10. Не заявляємо реалізованими GPS, maps, admin roles або RTO/RPO. План має тригери. Після 9:10 можна перейти до короткого live demo або питань, залишаючись у 10 хв. Джерела: ARCHITECTURE.md §§9,11,12; DEMO.md.');
text(s,'1. Відновлення без оператора',65,160,1140,48,34,true,C.blue);
text(s,'Durable coordinator, retention, backup drill\nТригер: реальні дані або unattended експлуатація',95,223,1100,90,28);
text(s,'2. Промислова межа довіри',65,335,1140,48,34,true,C.blue);
text(s,'TLS, IdP/JWKS, PostgreSQL, квоти й метрики\nТригер: зовнішній доступ або конкуренція записів',95,398,1100,90,28);
text(s,'3. Зовнішні інтеграції',65,510,1140,48,34,true,C.blue);
text(s,'Карти, телематика, сповіщення через адаптери\nТригер: погоджені NFR-2/3/8 та acceptance-тести',95,573,1100,90,28);
}

await fs.writeFile(path.join(ROOT,'docs/defense-notes.json'),JSON.stringify(notes,null,2)+'\n');
for(const [index,s] of p.slides.items.entries()){
 const png=await p.export({slide:s,format:'png',scale:1});
 await fs.writeFile(path.join(build,`slide-${String(index+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
const candidate=path.join(build,'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
await fs.mkdir(path.join(build,'output'),{recursive:true});
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,
 finalPath:path.join(build,'output/validated.pptx'),pythonExecutable:process.env.RUNTIME_PYTHON,
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],
 explicitTotalSlideCount:9,requiredNativeChartOwnerSlides:[7],requiredNativeTableOwnerSlides:[],
 materializeLiteralChartWorkbooks:true,
 fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,
 receiptPath:path.join(build,'validation.json')});
await fs.mkdir(path.join(ROOT,'submission'),{recursive:true});
await fs.copyFile(path.join(build,'output/validated.pptx'),path.join(ROOT,'submission/FleetFlow_Defense.pptx'));
console.log(JSON.stringify({slides:p.slides.items.length,previewDir:build,output:path.join(ROOT,'submission/FleetFlow_Defense.pptx')}));
