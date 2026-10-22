"""Agente visível de inventário para equipamentos da locadora.
Coleta somente dados básicos de hardware/SO e envia check-in autenticado.
Não coleta webcam, capturas de tela, arquivos, teclas ou localização oculta.
"""
import os, sys, json, time, uuid, platform, socket, subprocess
from pathlib import Path
import requests
try:
    import psutil
except ImportError:
    psutil=None
APP_DIR=Path(os.getenv('PROGRAMDATA',str(Path.home()))) / 'LocadoraAgente'
APP_DIR.mkdir(parents=True,exist_ok=True)
CONFIG=APP_DIR/'config.json'
LOG=APP_DIR/'agente.log'
def log(msg):
    try:
        with LOG.open('a',encoding='utf-8') as f: f.write(time.strftime('%Y-%m-%d %H:%M:%S')+' '+msg+'\n')
    except Exception: pass
def machine_serial():
    if platform.system()=='Windows':
        try:
            r=subprocess.run(['powershell','-NoProfile','-Command','(Get-CimInstance Win32_BIOS).SerialNumber'],capture_output=True,text=True,timeout=8,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if r.returncode==0 and r.stdout.strip(): return r.stdout.strip()[:180]
        except Exception: pass
    return 'NAO-DISPONIVEL'
def hardware():
    ram=''
    if psutil:
        try: ram=f'{psutil.virtual_memory().total/1024**3:.2f}'
        except Exception: pass
    manufacturer=model=''
    if platform.system()=='Windows':
        try:
            cmd='Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model | ConvertTo-Json -Compress'
            r=subprocess.run(['powershell','-NoProfile','-Command',cmd],capture_output=True,text=True,timeout=8,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            obj=json.loads(r.stdout) if r.returncode==0 and r.stdout.strip() else {}
            manufacturer=str(obj.get('Manufacturer',''))[:180]; model=str(obj.get('Model',''))[:180]
        except Exception: pass
    return {'device_key':get_device_key(),'hostname':socket.gethostname(),'serial':machine_serial(),'manufacturer':manufacturer,'model':model,'os_name':f'{platform.system()} {platform.release()} ({platform.version()[:80]})','cpu':platform.processor()[:280],'ram_gb':ram}
def get_device_key():
    p=APP_DIR/'device_id.txt'
    if p.exists():
        v=p.read_text(encoding='utf-8').strip()
        if v: return v
    v=str(uuid.uuid4()); p.write_text(v,encoding='utf-8'); return v
def setup():
    print('\n=== Agente de inventário da Locadora ===')
    print('Este aplicativo envia inventário básico do computador para a central autorizada.')
    print('Ele não captura webcam, tela, arquivos ou teclas e não faz rastreamento oculto.\n')
    url=input('URL da central (ex.: https://locadora-central.onrender.com): ').strip().rstrip('/')
    code=input('Código de instalação fornecido pela central: ').strip()
    if not url.startswith('https://') and not url.startswith('http://localhost'):
        raise ValueError('Use uma URL HTTPS da central.')
    data={'device_key':get_device_key(),'enrollment_key':code}
    r=requests.post(url+'/api/agent/enroll',json=data,timeout=20); r.raise_for_status()
    token=r.json()['device_token']
    CONFIG.write_text(json.dumps({'server_url':url,'device_token':token},indent=2),encoding='utf-8')
    try: os.chmod(CONFIG,0o600)
    except Exception: pass
    print('\nEquipamento registrado. O agente iniciará os check-ins.\n')
    return {'server_url':url,'device_token':token}
def main():
    try:
        cfg=json.loads(CONFIG.read_text(encoding='utf-8')) if CONFIG.exists() else setup()
        url=cfg['server_url'].rstrip('/'); token=cfg['device_token']
        while True:
            try:
                r=requests.post(url+'/api/agent/checkin',json=hardware(),headers={'Authorization':'Bearer '+token},timeout=20)
                r.raise_for_status(); log('Check-in enviado com sucesso')
            except Exception as e: log('Falha no check-in: '+str(e)[:250])
            time.sleep(60)
    except Exception as e:
        log('Falha de configuração: '+str(e)); print('Não foi possível iniciar: '+str(e)); input('Pressione Enter para sair...')
if __name__=='__main__': main()
