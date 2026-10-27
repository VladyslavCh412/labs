'use strict';
let accessToken = ''; // Memory only: never persist a bearer token in localStorage.

const icons = {
  grid:'<rect x="3" y="3" width="7" height="7" rx="1.3"/><rect x="14" y="3" width="7" height="7" rx="1.3"/><rect x="3" y="14" width="7" height="7" rx="1.3"/><rect x="14" y="14" width="7" height="7" rx="1.3"/>',
  truck:'<path d="M3 6h11v11H3zM14 10h4l3 4v3h-7z"/><circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>',
  route:'<circle cx="6" cy="5" r="2"/><circle cx="18" cy="19" r="2"/><path d="M6 7v6a4 4 0 0 0 4 4h4a4 4 0 0 0 4-4V8"/><path d="m15 10 3-3 3 3"/>',
  activity:'<path d="M3 12h4l3-7 4 14 3-7h4"/>',
  refresh:'<path d="M20 11a8 8 0 0 0-14-5L3 9"/><path d="M3 4v5h5"/><path d="M4 13a8 8 0 0 0 14 5l3-3"/><path d="M21 20v-5h-5"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  arrow:'<path d="M4 12h16m-7-7 7 7-7 7"/>',
  zap:'<path d="m13 2-9 12h7l-1 8 10-12h-7z"/>',
  userplus:'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M20 8v6m-3-3h6"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  menu:'<path d="M4 7h16M4 12h16M4 17h16"/>',
  close:'<path d="M5 5l14 14M19 5 5 19"/>',
  search:'<circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/>',
  check:'<path d="m5 12 5 5L20 7"/>',
  shield:'<path d="M12 3 4 7v5c0 5 3 8 8 9 5-1 8-4 8-9V7z"/><path d="m9 12 2 2 4-4"/>',
  calendar:'<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 10h18"/>',
  users:'<circle cx="9" cy="8" r="3"/><path d="M3 21v-2a6 6 0 0 1 12 0v2M16 5a3 3 0 0 1 0 6M17 15a5 5 0 0 1 4 5v1"/>',
  storage:'<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 2 18 2 18 0V5M3 12c0 2 18 2 18 0"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/>',
  alert:'<path d="m12 3 10 18H2z"/><path d="M12 9v5M12 17h.01"/>',
  bolt:'<path d="M12 2 7 12h5l-1 10 7-12h-5z"/>'
};
const icon = n => `<svg viewBox="0 0 24 24" aria-hidden="true">${icons[n] || icons.grid}</svg>`;
function hydrateIcons(){document.querySelectorAll('[data-icon]').forEach(el => {el.innerHTML=icon(el.dataset.icon)});}
const html = value => String(value == null ? '' : value).replace(/[&<>"']/g, char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const state={vehicles:[],drivers:[],trips:[],routes:[],cache:{hits:0,misses:0,ttl_seconds:30,entries:0},events:[],snapshots:[],processed:{processed_events:0},health:{fleet:false,trips:false},page:'overview',busy:false,modal:''};
const element = id=>document.getElementById(id);
const statusNames={available:'Доступний',in_trip:'У рейсі',maintenance:'На ТО',planned:'Заплановано'};
function statusBadge(s){let cls=s==='available'?'success':s==='maintenance'?'warning':s==='in_trip'?'busy':'muted';return `<span class="badge ${cls}">${html(statusNames[s]||s)}</span>`;}
const ellipsis = (s,max=32)=>s.length>max?s.substring(0,max-1)+'…':s;
function toast(message,isError=false){const node=document.createElement('div');node.className='toast'+(isError?' error':'');node.innerHTML=icon(isError?'alert':'check')+`<span>${html(message)}</span>`;element('toastRegion').appendChild(node);setTimeout(()=>node.remove(),5000);}
async function request(path,options={}){
  let response;
  try{response=await fetch(path,{...options,headers:{'content-type':'application/json',...(accessToken?{'authorization':'Bearer '+accessToken}:{}),...(options.headers||{})}})}
  catch{throw new Error('Немає з’єднання із сервісом. Перевірте, чи запущено launch.py.')}
  let content={};try{content=await response.json()}catch{}
  if(response.status===401){accessToken='';element('loginPanel').style.display='grid';element('logoutBtn').hidden=true;}
  if(!response.ok){
    let detail=content.detail||'request_failed';
    let desc=typeof detail==='string'?detail:JSON.stringify(detail);
    const friendly={vehicle_not_found:'Автомобіль не знайдено',route_not_found:'Маршрут не знайдено',driver_not_found:'Водій не знайдений',trip_not_found:'Рейс не знайдено',duplicate_trip_id:'Рейс із таким ID вже існує',vehicle_duplicate_or_invalid:'Автомобіль з таким ID вже існує або дані некоректні',driver_duplicate_or_invalid:'Водій з таким ID вже існує або дані некоректні',route_duplicate_or_invalid:'Маршрут вже існує або дані некоректні',fleet_service_unavailable:'Fleet недоступний',fleet_unavailable:'Fleet недоступний',trips_unavailable:'Trips недоступний'};
    throw new Error(friendly[desc]||`HTTP ${response.status}: ${desc}`);
  }
  return content;
}
async function refresh({silent=false}={}){
  if(state.busy)return;state.busy=true;
  const queries={vehicles:'/api/fleet/vehicles',drivers:'/api/fleet/drivers',trips:'/api/trips/trips',routes:'/api/trips/routes',cache:'/api/fleet/cache/stats',events:'/api/fleet/fleet-events/outbox',snapshots:'/api/trips/snapshots/vehicles',processed:'/api/trips/events/fleet-processed-count',health:'/api/health'};
  const entries=Object.entries(queries);
  const res=await Promise.allSettled(entries.map(([,path])=>request(path)));
  let errors=0;res.forEach((result,i)=>{if(result.status==='fulfilled')state[entries[i][0]]=result.value;else errors++;});
  const ok=!!state.health.fleet && !!state.health.trips;
  element('statusIndicator').classList.toggle('on',ok);
  element('sidebarStatus').textContent=ok?'Усі сервіси онлайн':'Перевірте сервіси';
  render();state.busy=false;
  if(errors&&!silent)toast('Не всі сервіси відповідають. Перевірте термінал запуску.',true);
}
function statCard(label,val,note,ico,cls=''){return `<div class="stat-card"><div><span class="stat-label">${label}</span><span class="stat-value">${val}</span><span class="stat-foot">${note}</span></div><span class="stat-icon ${cls}">${icon(ico)}</span></div>`;}
function empty(label,desc){return `<div class="empty"><span class="empty-icon">${icon('storage')}</span><strong>${label}</strong><p>${desc}</p></div>`;}
function table(headers,rows){return `<div class="table-scroll"><table class="list-table"><thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;}
function displayRoute(routeId){const r=state.routes.find(r=>r.id===routeId);return r?`${html(r.stops[0])} → ${html(r.stops[r.stops.length-1])}`:html(routeId);}
function vehicleRows(limit=0){const term=state.page==='vehicles'?(element('vehicleSearch')?.value||'').toLowerCase().trim():'';
  let vehicles=state.vehicles.filter(v=>(v.id+' '+v.plate+' '+v.status).toLowerCase().includes(term));if(limit)vehicles=vehicles.slice(0,limit);
  return vehicles.map(v=>`<tr><td><span class="avatar-auto">${icon('truck')}</span><span class="ident">${html(v.id)}</span></td><td><span class="plate">${html(v.plate)}</span></td><td>${statusBadge(v.status)}</td>${!limit?`<td class="muted">v${html(v.version)}</td><td><button class="tiny-btn" data-action="edit-status" data-id="${html(v.id)}">Статус</button> <button class="tiny-btn" data-action="edit-plate" data-id="${html(v.id)}">Номер</button></td>`:''}</tr>`);
}
function tripRows(limit=0){const trips=limit?state.trips.slice(0,limit):state.trips;
  return trips.map(t=>`<tr><td class="ident">${html(t.id)}</td><td>${displayRoute(t.route_id)}</td><td class="plate">${html(t.vehicle_id)}</td>${!limit?`<td>${html(t.driver_id)}</td>`:''}<td>${statusBadge(t.status)}</td></tr>`);
}
function renderOverview(){
 const available=state.vehicles.filter(v=>v.status==='available').length;
 element('summaryCards').innerHTML=[statCard('Всього автомобілів',state.vehicles.length,'У базі Fleet','truck'),statCard('Доступні для рейсу',available,'Готові до роботи','shield','green'),statCard('Заплановані рейси',state.trips.length,'У базі Trips','route','purple'),statCard('Оброблені події',state.processed.processed_events||0,'Синхронізація даних','activity','orange')].join('');
 element('overviewVehicles').innerHTML=state.vehicles.length?table(['Автомобіль','Номер','Статус'],vehicleRows(4)):empty('Автомобілів немає','Додайте перше авто у розділі «Автопарк».');
 element('overviewTrips').innerHTML=state.trips.length?table(['ID рейсу','Маршрут','Авто','Статус'],tripRows(4)):empty('Поки немає рейсів','Натисніть «Новий рейс», щоб створити першу поїздку.');
}
function renderVehicles(){
 element('vehicleCount').textContent=state.vehicles.length;
 const rows=vehicleRows();element('vehicleTable').innerHTML=rows.length?table(['Автомобіль','Держ. номер','Статус','Версія','Дії'],rows):empty('Автомобілі не знайдені','Перевірте пошук або додайте новий автомобіль.');
 const drivers=state.drivers.map(d=>`<tr><td><span class="ident">${html(d.name)}</span><span class="subtext">ID: ${html(d.id)}</span></td><td>${d.active?statusBadge('available'):'Неактивний'}</td><td>${d.license_valid?'<span class="badge success">Посвідчення дійсне</span>':'<span class="badge warning">Недійсне</span>'}</td></tr>`);
 element('driverTable').innerHTML=drivers.length?table(['Водій','Стан','Посвідчення'],drivers):empty('Немає водіїв','Додайте водія для створення рейсів.');
}
function renderTrips(){
 element('tripCount').textContent=state.trips.length;
 element('tripTable').innerHTML=state.trips.length?table(['ID рейсу','Напрямок','Автомобіль','Водій','Статус'],tripRows()):empty('Рейсів поки немає','Натисніть «Створити рейс» та оберіть маршрут, авто і водія.');
 element('routeGrid').innerHTML=state.routes.length?state.routes.map(r=>`<div class="route-card"><div class="route-card-top"><strong>${html(r.id)}</strong><span class="route-chip">${r.stops.length} точки</span></div><div class="route-city">${r.stops.map(html).join('<span class="arrow-track"> → </span>')}</div><small>Доступний маршрут</small></div>`).join(''):empty('Маршрути відсутні','Створіть перший маршрут.');
}
function renderEvents(){
 const hits=state.cache.hits||0,misses=state.cache.misses||0,ratio=hits+misses?Math.round(hits/(hits+misses)*100):0;
 element('cacheWidget').innerHTML=`<div class="metrics-box"><div class="metric-pairs"><div class="metric-pair"><span class="metric-number">${hits}</span><span class="metric-caption">Cache hits</span></div><div class="metric-pair"><span class="metric-number">${misses}</span><span class="metric-caption">Cache misses</span></div></div><div class="cache-bar"><span style="width:${ratio}%"></span></div><div class="cache-description"><span>Частка потраплянь у кеш</span><strong>${ratio}%</strong></div></div>`;
 const events=state.events||[],pending=events.filter(e=>!e.delivered).length;
 element('eventMetrics').innerHTML=`<div class="metrics-box"><div class="metric-pairs"><div class="metric-pair"><span class="metric-number">${state.processed.processed_events||0}</span><span class="metric-caption">Прийнято Trips</span></div><div class="metric-pair"><span class="metric-number">${pending}</span><span class="metric-caption">Очікують доставки</span></div></div><div class="cache-bar"><span style="width:${events.length?Math.round(100*(events.length-pending)/events.length):100}%;background:linear-gradient(90deg,#29ba9a,#6ddcc8)"></span></div><div class="cache-description"><span>Доставлено з outbox</span><strong>${events.length-pending} / ${events.length}</strong></div></div>`;
 const snaps=state.snapshots||[];
 element('snapshotsTable').innerHTML=snaps.length?table(['Автомобіль','Держ. номер','Статус','Версія','Оновлено'],snaps.map(s=>`<tr><td class="ident">${html(s.id)}</td><td class="plate">${html(s.plate)}</td><td>${statusBadge(s.status)}</td><td class="muted">v${html(s.version)}</td><td class="muted">${html(String(s.updated_at).replace('T',' ').slice(0,19))}</td></tr>`)):empty('Копій поки немає','Змініть статус автомобіля в розділі «Автопарк». Через подію копія з’явиться тут.');
 element('eventsTable').innerHTML=events.length?table(['Тип події','Автомобіль','Версія','Доставка'],events.slice().reverse().slice(0,12).map(e=>`<tr><td class="ident">${html(e.payload?.type||'Подія')}</td><td class="plate">${html(e.payload?.data?.id||'—')}</td><td class="muted">v${html(e.payload?.data?.version||'—')}</td><td>${e.delivered?'<span class="badge success">Доставлено</span>':'<span class="badge warning">Очікує</span>'}</td></tr>`)):empty('Подій ще немає','Змініть статус авто, щоб створити першу подію.');
}
function render(){renderOverview();renderVehicles();renderTrips();renderEvents();}
const pageNames={overview:'Огляд',vehicles:'Автопарк',trips:'Рейси та маршрути',events:'Дані та події'};
function setPage(page){if(!pageNames[page])return;state.page=page;document.querySelectorAll('.page').forEach(p=>p.classList.toggle('active',p.id==='page-'+page));document.querySelectorAll('.nav-link').forEach(n=>n.classList.toggle('active',n.dataset.page===page));element('breadcrumbName').textContent=pageNames[page];element('sidebar').classList.remove('open');element('mobileShade').classList.remove('open');window.scrollTo({top:0,behavior:'smooth'});render();}
function option(value,label,selected=''){return `<option value="${html(value)}" ${value===selected?'selected':''}>${html(label)}</option>`;}
function field(name,label,type='text',value='',extra='',options=''){if(type==='select')return `<label class="field"><span>${label}</span><select name="${name}" required>${options}</select></label>`;return `<label class="field"><span>${label}</span><input name="${name}" type="${type}" value="${html(value)}" required ${extra}></label>`;}
function openModal(type,id){
 let title='',kicker='',fields='',save='Зберегти';state.modal=type;
 if(type==='new-vehicle'){
  title='Новий автомобіль';kicker='FLEET SERVICE';fields=field('id','ID автомобіля','text',`v-${Date.now().toString(36).slice(-5)}`)+field('plate','Державний номер','text','','placeholder="BH1234AA"')+field('status','Початковий статус','select','','',Object.entries({available:'Доступний',in_trip:'У рейсі',maintenance:'На ТО'}).map(([v,l])=>option(v,l)).join(''));
 }else if(type==='new-driver'){
  title='Додати водія';kicker='FLEET SERVICE';fields=field('id','ID водія','text',`d-${Date.now().toString(36).slice(-5)}`)+field('name','Ім’я водія','text','','placeholder="Ірина Коваленко"');
 }else if(type==='new-route'){
  title='Новий маршрут';kicker='TRIPS SERVICE';fields=field('id','ID маршруту','text',`r-${Date.now().toString(36).slice(-5)}`)+field('stops','Пункти маршруту (через кому)','text','','placeholder="Одеса, Миколаїв, Херсон"');
 }else if(type==='new-trip'){
  if(!state.vehicles.length||!state.drivers.length||!state.routes.length){toast('Спочатку додайте автомобіль, водія та маршрут.',true);return}
  title='Створити рейс';kicker='TRIPS SERVICE';save='Створити рейс';
  const available=state.vehicles.filter(v=>v.status==='available');if(!available.length){toast('Немає доступних автомобілів. Спочатку змініть статус.',true);return}
  fields=field('id','ID рейсу','text',`t-${Date.now().toString(36).slice(-6)}`)+field('route_id','Маршрут','select','','',state.routes.map(r=>option(r.id,`${r.id} · ${r.stops.join(' → ')}`)).join(''))+field('vehicle_id','Автомобіль','select','','',available.map(v=>option(v.id,`${v.plate} (${v.id})`)).join(''))+field('driver_id','Водій','select','','',state.drivers.filter(d=>d.active&&d.license_valid).map(d=>option(d.id,`${d.name} (${d.id})`)).join(''));
 }else if(type==='edit-status'){
  let v=state.vehicles.find(v=>v.id===id);if(!v)return;title=`Статус ${v.plate}`;kicker='ІНВАЛІДАЦІЯ КЕШУ';fields=field('id','Автомобіль','text',id,'readonly')+field('status','Новий статус','select','','',Object.entries({available:'Доступний',in_trip:'У рейсі',maintenance:'На ТО'}).map(([key,value])=>option(key,value,v.status)).join(''));
 }else if(type==='edit-plate'){
  let v=state.vehicles.find(v=>v.id===id);if(!v)return;title=`Номер ${v.id}`;kicker='FLEET SERVICE';fields=field('id','Автомобіль','text',id,'readonly')+field('plate','Державний номер','text',v.plate);
 }
 element('modalTitle').textContent=title;element('modalKicker').textContent=kicker;element('saveModal').textContent=save;element('modalFields').innerHTML=fields;
 element('modalOverlay').hidden=false;const first=element('modalFields').querySelector('input:not([readonly]),select');if(first)first.focus();
}
function closeModal(){element('modalOverlay').hidden=true;state.modal='';}
async function submitForm(evt){evt.preventDefault();const button=element('saveModal');button.disabled=true;button.textContent='Збереження...';const d=Object.fromEntries(new FormData(element('modalForm')).entries());let path='',method='POST',payload={};
 try{
  switch(state.modal){
   case 'new-vehicle':path='/api/fleet/vehicles';payload={id:d.id.trim(),plate:d.plate.trim(),status:d.status};break;
   case 'new-driver':path='/api/fleet/drivers';payload={id:d.id.trim(),name:d.name.trim()};break;
   case 'new-route':path='/api/trips/routes';payload={id:d.id.trim(),stops:d.stops.split(/[,;\n]+/).map(x=>x.trim()).filter(Boolean)};if(payload.stops.length<2)throw new Error('Вкажіть принаймні два пункти маршруту');break;
   case 'new-trip':path='/api/trips/trips';payload={id:d.id.trim(),route_id:d.route_id,vehicle_id:d.vehicle_id,driver_id:d.driver_id};break;
   case 'edit-status':path='/api/fleet/vehicles/'+encodeURIComponent(d.id)+'/status';method='PATCH';payload={status:d.status};break;
   case 'edit-plate':path='/api/fleet/vehicles/'+encodeURIComponent(d.id)+'/registration';method='PATCH';payload={plate:d.plate.trim()};break;
   default:return;
  }
  await request(path,{method,body:JSON.stringify(payload)});
  let msg=state.modal==='new-trip'?'Рейс створено успішно':state.modal==='edit-status'?'Статус оновлено. Кеш очищено, подію створено.':'Зміни збережено';
  closeModal();toast(msg);await refresh({silent:true});
 }catch(e){toast(e.message,true)}finally{button.disabled=false;button.textContent='Зберегти';}
}
async function cacheDemo(){
 const v=state.vehicles[0];if(!v){toast('Спочатку додайте автомобіль.',true);return}
 try{const before=await request('/api/fleet/cache/stats');await request('/api/fleet/vehicles/'+encodeURIComponent(v.id));await request('/api/fleet/vehicles/'+encodeURIComponent(v.id));const after=await request('/api/fleet/cache/stats');
 toast(`Кеш: hits +${after.hits-before.hits}; misses +${after.misses-before.misses}. TTL ${after.ttl_seconds} с.`);await refresh({silent:true});setPage('events');
 }catch(e){toast(e.message,true)}
}
async function doAction(act,id){switch(act){case 'new-vehicle':case 'new-driver':case 'new-trip':case 'new-route':case 'edit-status':case 'edit-plate':openModal(act,id);break;case 'cache-demo':await cacheDemo();break;case 'refresh':await refresh();toast('Дані оновлено');break;}}
document.addEventListener('click',e=>{const pg=e.target.closest('[data-page]');if(pg){setPage(pg.dataset.page);return}const act=e.target.closest('[data-action]');if(act){doAction(act.dataset.action,act.dataset.id)}});
element('modalForm').addEventListener('submit',submitForm);
element('closeModal').addEventListener('click',closeModal);
element('cancelModal').addEventListener('click',closeModal);
element('modalOverlay').addEventListener('click',e=>{if(e.target.id==='modalOverlay')closeModal()});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!element('modalOverlay').hidden)closeModal()});
element('refreshBtn').addEventListener('click',()=>doAction('refresh'));
element('vehicleSearch').addEventListener('input',renderVehicles);
element('menuBtn').addEventListener('click',()=>{element('sidebar').classList.toggle('open');element('mobileShade').classList.toggle('open')});
element('mobileShade').addEventListener('click',()=>{element('sidebar').classList.remove('open');element('mobileShade').classList.remove('open')});
hydrateIcons();
element('loginForm').addEventListener('submit',async e=>{
 e.preventDefault();element('loginError').textContent='';
 try{
  const r=await fetch('/auth/token',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({username:element('loginUser').value,password:element('loginPassword').value})});
  if(!r.ok)throw new Error(r.status===429?'Забагато спроб. Зачекайте хвилину.':'Неправильний логін або пароль');
  const result=await r.json();accessToken=result.access_token;element('loginPassword').value='';
  element('loginPanel').style.display='none';element('logoutBtn').hidden=false;
  element('logoutBtn').textContent=result.username+' · Вийти';
  await refresh();
 }catch(error){element('loginError').textContent=error.message;}
});
element('logoutBtn').addEventListener('click',()=>{accessToken='';window.location.reload();});
setInterval(()=>{if(accessToken&&!document.hidden&&element('modalOverlay').hidden)refresh({silent:true});},15000);
