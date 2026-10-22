import os, secrets, hashlib, hmac
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import FastAPI, Request, Form, Header, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine, String, DateTime, Boolean, ForeignKey, Text, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, relationship

APP_NAME = os.getenv('APP_NAME', 'Central da Locadora')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./locadora_dev.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+psycopg://', 1)
elif DATABASE_URL.startswith('postgresql://') and '+psycopg' not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://', 1)
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if DATABASE_URL.startswith('sqlite') else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase): pass
class Device(Base):
    __tablename__='devices'
    id: Mapped[int]=mapped_column(primary_key=True)
    device_key: Mapped[str]=mapped_column(String(80), unique=True, index=True)
    token_hash: Mapped[str]=mapped_column(String(64))
    hostname: Mapped[str]=mapped_column(String(200), default='')
    serial: Mapped[str]=mapped_column(String(200), default='', index=True)
    manufacturer: Mapped[str]=mapped_column(String(200), default='')
    model: Mapped[str]=mapped_column(String(200), default='')
    os_name: Mapped[str]=mapped_column(String(200), default='')
    cpu: Mapped[str]=mapped_column(String(300), default='')
    ram_gb: Mapped[str]=mapped_column(String(30), default='')
    last_seen: Mapped[Optional[datetime]]=mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    active: Mapped[bool]=mapped_column(Boolean, default=True)
    checkins: Mapped[list['Checkin']]=relationship(back_populates='device', cascade='all, delete-orphan')
class Checkin(Base):
    __tablename__='checkins'
    id: Mapped[int]=mapped_column(primary_key=True)
    device_id: Mapped[int]=mapped_column(ForeignKey('devices.id'), index=True)
    seen_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    summary: Mapped[str]=mapped_column(Text, default='')
    device: Mapped[Device]=relationship(back_populates='checkins')
class Customer(Base):
    __tablename__='customers'
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(200))
    phone: Mapped[str]=mapped_column(String(60), default='')
    company: Mapped[str]=mapped_column(String(200), default='')
    notes: Mapped[str]=mapped_column(Text, default='')
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
class Lease(Base):
    __tablename__='leases'
    id: Mapped[int]=mapped_column(primary_key=True)
    device_id: Mapped[int]=mapped_column(ForeignKey('devices.id'))
    customer_id: Mapped[int]=mapped_column(ForeignKey('customers.id'))
    delivered_on: Mapped[str]=mapped_column(String(20), default='')
    due_on: Mapped[str]=mapped_column(String(20), default='')
    status: Mapped[str]=mapped_column(String(40), default='Ativa')
    notes: Mapped[str]=mapped_column(Text, default='')
    device: Mapped[Device]=relationship()
    customer: Mapped[Customer]=relationship()

Base.metadata.create_all(engine)
app=FastAPI(title=APP_NAME)
app.add_middleware(SessionMiddleware, secret_key=os.getenv('SESSION_SECRET','dev-only-change-this-secret'), https_only=os.getenv('RENDER','')=='true', same_site='lax', max_age=60*60*8)

CSS='''<style>body{margin:0;background:#f3f6fb;color:#172033;font:15px Arial,sans-serif}.top{background:#111827;color:white;padding:20px 5%;display:flex;justify-content:space-between;align-items:center}.wrap{max-width:1180px;margin:26px auto;padding:0 18px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:14px}.card,.panel{background:white;border:1px solid #e1e7f0;border-radius:14px;padding:18px;margin-bottom:16px;box-shadow:0 4px 15px #18243b0a}.num{font-size:28px;font-weight:700;margin-top:8px}.muted{color:#68758a;font-size:13px}table{width:100%;border-collapse:collapse;background:white}th,td{text-align:left;padding:11px;border-bottom:1px solid #e8edf4;vertical-align:top}th{background:#f8fafc}input,select,textarea{box-sizing:border-box;padding:10px;border:1px solid #ccd5e2;border-radius:8px;width:100%;margin:5px 0 12px;background:white;color:#172033}button,.btn{background:#2563eb;color:white;border:0;border-radius:8px;padding:10px 14px;text-decoration:none;cursor:pointer;display:inline-block}.danger{background:#b91c1c}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}.tag{border-radius:99px;padding:4px 9px;font-size:12px;background:#e0f2fe;color:#075985}.online{background:#dcfce7;color:#166534}.offline{background:#fee2e2;color:#991b1b}.nav a{color:#bfdbfe;margin-right:15px;text-decoration:none}@media(max-width:700px){.top{align-items:flex-start;gap:12px;flex-direction:column}table{font-size:12px}th,td{padding:7px}}</style>'''
def page(body, request=None, title=None):
    nav=''
    if request and request.session.get('admin'):
        nav='<div class="nav"><a href="/">Painel</a><a href="/devices">Equipamentos</a><a href="/customers">Clientes</a><a href="/leases">Locações</a><a href="/logout">Sair</a></div>'
    return HTMLResponse(f'<!doctype html><html lang="pt-br"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title or APP_NAME}</title>{CSS}<header class="top"><div><strong>▣ {APP_NAME}</strong><div class="muted" style="color:#cbd5e1">Gestão de equipamentos e locações</div></div>{nav}</header><main class="wrap">{body}</main></html>')
def logged(request): return bool(request.session.get('admin'))
def require_admin(request):
    if not logged(request): raise HTTPException(303, headers={'Location':'/login'})
def utcnow(): return datetime.now(timezone.utc)
def is_online(d):
    if not d.last_seen: return False
    seen=d.last_seen
    if seen.tzinfo is None: seen=seen.replace(tzinfo=timezone.utc)
    return utcnow()-seen < timedelta(minutes=5)
def digest(token): return hashlib.sha256(token.encode()).hexdigest()
def safe(s):
    import html
    return html.escape(str(s or ''))
@app.get('/health')
def health(): return {'ok':True,'service':APP_NAME}
@app.get('/login',response_class=HTMLResponse)
def login_get(request:Request):
    return page('<div class="panel" style="max-width:420px;margin:45px auto"><h2>Entrar na central</h2><form method="post"><label>Usuário</label><input name="username" required autocomplete="username"><label>Senha</label><input type="password" name="password" required autocomplete="current-password"><button type="submit">Entrar</button></form><p class="muted">Acesso restrito à equipe autorizada.</p></div>',request)
@app.post('/login')
def login_post(request:Request, username:str=Form(...), password:str=Form(...)):
    eu=os.getenv('ADMIN_USERNAME','admin'); ep=os.getenv('ADMIN_PASSWORD','')
    if not ep or not hmac.compare_digest(username,eu) or not hmac.compare_digest(password,ep):
        return page('<div class="panel"><h2>Não foi possível entrar</h2><p>Confira usuário e senha. O administrador precisa configurar ADMIN_PASSWORD no ambiente do servidor.</p><a class="btn" href="/login">Tentar novamente</a></div>',request)
    request.session.clear(); request.session['admin']=username
    return RedirectResponse('/',status_code=303)
@app.get('/logout')
def logout(request:Request): request.session.clear(); return RedirectResponse('/login',status_code=303)
@app.get('/',response_class=HTMLResponse)
def dashboard(request:Request):
    if not logged(request): return RedirectResponse('/login',status_code=303)
    with SessionLocal() as db:
        ds=db.scalars(select(Device).order_by(Device.id.desc())).all(); cs=db.scalars(select(Customer).order_by(Customer.id.desc()).limit(8)).all(); ls=db.scalars(select(Lease).order_by(Lease.id.desc()).limit(8)).all()
    online=sum(1 for d in ds if d.active and is_online(d)); offline=sum(1 for d in ds if d.active and not is_online(d))
    rows=''.join(f'<tr><td>{safe(d.hostname or "Sem nome")}</td><td>{safe(d.serial or "—")}</td><td>{safe(d.manufacturer)} {safe(d.model)}</td><td><span class="tag {"online" if is_online(d) else "offline"}">{"Online" if is_online(d) else "Offline"}</span></td><td>{safe(d.last_seen.strftime("%d/%m/%Y %H:%M UTC") if d.last_seen else "Nunca")}</td></tr>' for d in ds[:12]) or '<tr><td colspan="5">Nenhum equipamento cadastrado. Instale o agente ou cadastre os dados.</td></tr>'
    return page(f'<h1>Visão geral</h1><p class="muted">Status online significa comunicação nos últimos 5 minutos; não comprova localização física.</p><section class="cards"><div class="card">Equipamentos<div class="num">{len(ds)}</div></div><div class="card">Online<div class="num">{online}</div></div><div class="card">Offline<div class="num">{offline}</div></div><div class="card">Clientes<div class="num">{len(cs)}</div></div><div class="card">Locações ativas<div class="num">{sum(1 for x in ls if x.status=="Ativa")}</div></div></section><section class="panel"><h2>Equipamentos recentes</h2><div style="overflow:auto"><table><thead><tr><th>Nome</th><th>Nº de série</th><th>Modelo</th><th>Status</th><th>Último contato</th></tr></thead><tbody>{rows}</tbody></table></div><p><a class="btn" href="/devices">Ver equipamentos</a> <a class="btn" href="/customers">Cadastrar cliente</a> <a class="btn" href="/leases">Gerenciar locações</a></p></section>',request)
@app.get('/devices',response_class=HTMLResponse)
def devices(request:Request):
    if not logged(request): return RedirectResponse('/login',status_code=303)
    with SessionLocal() as db: ds=db.scalars(select(Device).order_by(Device.id.desc())).all()
    rows=''.join(f'<tr><td>{safe(d.hostname)}</td><td>{safe(d.serial)}</td><td>{safe(d.manufacturer)} {safe(d.model)}</td><td>{safe(d.os_name)}</td><td>{safe(d.cpu)}</td><td>{safe(d.ram_gb)} GB</td><td>{"Online" if is_online(d) else "Offline"}</td><td>{safe(d.last_seen.isoformat() if d.last_seen else "Nunca")}</td></tr>' for d in ds) or '<tr><td colspan="8">Sem equipamentos.</td></tr>'
    body=f'<h1>Equipamentos</h1><div class="panel"><p>O agente cadastra e atualiza os dados de inventário. Duplicidades de serial devem ser revisadas antes de mesclar registros.</p><div style="overflow:auto"><table><tr><th>Hostname</th><th>Serial</th><th>Fabricante/modelo</th><th>Sistema</th><th>CPU</th><th>RAM</th><th>Status</th><th>Último contato</th></tr>{rows}</table></div></div>'
    return page(body,request)
@app.get('/customers',response_class=HTMLResponse)
def customers(request:Request):
    if not logged(request): return RedirectResponse('/login',status_code=303)
    with SessionLocal() as db: cs=db.scalars(select(Customer).order_by(Customer.id.desc())).all()
    rows=''.join(f'<tr><td>{c.id}</td><td>{safe(c.name)}</td><td>{safe(c.company)}</td><td>{safe(c.phone)}</td><td>{safe(c.notes)}</td></tr>' for c in cs) or '<tr><td colspan="5">Nenhum cliente cadastrado.</td></tr>'
    return page(f'<h1>Clientes</h1><div class="panel"><h2>Novo cliente</h2><form method="post" action="/customers"><div class="grid"><div>Nome*<input name="name" required></div><div>Empresa<input name="company"></div><div>Telefone<input name="phone"></div></div><label>Observações</label><textarea name="notes"></textarea><button>Cadastrar cliente</button></form></div><div class="panel"><h2>Cadastro</h2><div style="overflow:auto"><table><tr><th>ID</th><th>Nome</th><th>Empresa</th><th>Telefone</th><th>Observações</th></tr>{rows}</table></div></div>',request)
@app.post('/customers')
def customer_create(request:Request,name:str=Form(...),company:str=Form(''),phone:str=Form(''),notes:str=Form('')):
    if not logged(request): return RedirectResponse('/login',status_code=303)
    with SessionLocal() as db: db.add(Customer(name=name.strip(),company=company.strip(),phone=phone.strip(),notes=notes.strip())); db.commit()
    return RedirectResponse('/customers',status_code=303)
@app.get('/leases',response_class=HTMLResponse)
def leases(request:Request):
    if not logged(request): return RedirectResponse('/login',status_code=303)
    with SessionLocal() as db:
        ds=db.scalars(select(Device).order_by(Device.id.desc())).all(); cs=db.scalars(select(Customer).order_by(Customer.name)).all(); ls=db.scalars(select(Lease).order_by(Lease.id.desc())).all()
    devopts=''.join(f'<option value="{d.id}">{safe(d.hostname)} — {safe(d.serial)}</option>' for d in ds)
    custopts=''.join(f'<option value="{c.id}">{safe(c.name)} ({safe(c.company)})</option>' for c in cs)
    rows=''.join(f'<tr><td>{l.id}</td><td>{safe(l.device.hostname)} / {safe(l.device.serial)}</td><td>{safe(l.customer.name)}</td><td>{safe(l.delivered_on)}</td><td>{safe(l.due_on)}</td><td>{safe(l.status)}</td><td>{safe(l.notes)}</td></tr>' for l in ls) or '<tr><td colspan="7">Nenhuma locação.</td></tr>'
    return page(f'<h1>Locações</h1><div class="panel"><h2>Nova locação</h2><form method="post"><div class="grid"><div>Equipamento<select name="device_id" required>{devopts}</select></div><div>Cliente<select name="customer_id" required>{custopts}</select></div><div>Data de entrega<input type="date" name="delivered_on" required></div><div>Previsão de devolução<input type="date" name="due_on" required></div><div>Status<select name="status"><option>Ativa</option><option>Devolvida</option><option>Em atraso</option><option>Cancelada</option></select></div></div><label>Observações</label><textarea name="notes"></textarea><button>Salvar locação</button></form></div><div class="panel"><h2>Registros</h2><div style="overflow:auto"><table><tr><th>ID</th><th>Equipamento</th><th>Cliente</th><th>Entrega</th><th>Devolução prevista</th><th>Status</th><th>Observações</th></tr>{rows}</table></div></div>',request)
@app.post('/leases')
def lease_create(request:Request,device_id:int=Form(...),customer_id:int=Form(...),delivered_on:str=Form(...),due_on:str=Form(...),status:str=Form('Ativa'),notes:str=Form('')):
    if not logged(request): return RedirectResponse('/login',status_code=303)
    with SessionLocal() as db:
        if not db.get(Device,device_id) or not db.get(Customer,customer_id): raise HTTPException(400,'Equipamento ou cliente inválido')
        db.add(Lease(device_id=device_id,customer_id=customer_id,delivered_on=delivered_on,due_on=due_on,status=status,notes=notes.strip())); db.commit()
    return RedirectResponse('/leases',status_code=303)
@app.post('/api/agent/enroll')
def enroll(payload:dict):
    key=os.getenv('ENROLLMENT_KEY','')
    if not key or not hmac.compare_digest(str(payload.get('enrollment_key','')),key): raise HTTPException(403,'Código de instalação inválido')
    device_key=str(payload.get('device_key',''))
    if len(device_key)<12 or len(device_key)>80: raise HTTPException(400,'Identificador inválido')
    token=secrets.token_urlsafe(36)
    with SessionLocal() as db:
        d=db.scalar(select(Device).where(Device.device_key==device_key))
        if d: raise HTTPException(409,'Este agente já está registrado. Contate o administrador.')
        d=Device(device_key=device_key,token_hash=digest(token)); db.add(d); db.commit()
    return {'device_token':token,'device_id':device_key,'message':'Equipamento registrado'}
@app.post('/api/agent/checkin')
def checkin(payload:dict, authorization:Optional[str]=Header(default=None)):
    if not authorization or not authorization.lower().startswith('bearer '): raise HTTPException(401,'Token obrigatório')
    token=authorization.split(' ',1)[1]
    device_key=str(payload.get('device_key',''))
    with SessionLocal() as db:
        d=db.scalar(select(Device).where(Device.device_key==device_key))
        if not d or not hmac.compare_digest(d.token_hash,digest(token)) or not d.active: raise HTTPException(403,'Dispositivo não autorizado')
        for field in ('hostname','serial','manufacturer','model','os_name','cpu','ram_gb'):
            val=str(payload.get(field,'') or '')[:300]
            setattr(d,field,val)
        d.last_seen=utcnow()
        db.add(Checkin(device_id=d.id,seen_at=d.last_seen,summary=f"{d.hostname} | {d.os_name} | {d.model}"))
        # Keep recent history bounded per device (last 500 check-ins)
        old_ids=db.scalars(select(Checkin.id).where(Checkin.device_id==d.id).order_by(Checkin.seen_at.desc()).offset(500)).all()
        if old_ids: db.query(Checkin).filter(Checkin.id.in_(old_ids)).delete(synchronize_session=False)
        db.commit()
    return {'ok':True,'server_time':utcnow().isoformat()}
@app.get('/api/agent/status')
def agent_status(): return {'ok':True,'service':APP_NAME}
