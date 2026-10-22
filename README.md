# Sistema Locadora V2 — Central na nuvem + agente Windows

## Arquitetura
- FastAPI no Render (central web e API de check-in).
- PostgreSQL gerenciado no Render para equipamentos, clientes, locações e histórico.
- Agente Windows 10/11 empacotável como EXE com PyInstaller.
- Instalador Windows criado com Inno Setup 6, com atalhos e desinstalador.
- O agente usa um código de instalação para se registrar e recebe um token individual; o token é guardado localmente e enviado por HTTPS.

## Plano de demonstração gratuita no Render
O arquivo `render.yaml` desta cópia usa `plan: free` para o serviço web e o PostgreSQL. É voltado a demonstração/testes: o serviço web gratuito pode dormir após inatividade e o PostgreSQL gratuito do Render expira após 30 dias, tem limite de 1 GB e não oferece backups. Não use esse banco para dados importantes de produção; migre para um banco com persistência/backup antes de uso real. Consulte https://render.com/docs/free.

## Limites importantes
O agente coleta inventário básico (hostname, serial do BIOS quando disponível, fabricante/modelo, versão do Windows, CPU e RAM) e check-ins. Não coleta GPS, webcam, capturas de tela, arquivos ou teclas. Não há comando remoto de bloqueio neste protótipo. A localização não é simulada: para mapa, é necessário implementar uma fonte autorizada e exibir sua precisão e horário.

## 1. Publicar a central no Render
1. Crie um repositório privado e envie os arquivos deste diretório.
2. No Render, crie um Blueprint usando `render.yaml`, ou crie um Web Service Python e um PostgreSQL.
3. Configure no serviço: `ADMIN_USERNAME`, `ADMIN_PASSWORD` (senha longa e exclusiva), `ENROLLMENT_KEY` (código longo e aleatório) e `SESSION_SECRET` (segredo aleatório forte). Não coloque segredos no código nem no repositório.
4. Configure `DATABASE_URL` com a Internal Database URL do PostgreSQL no Render.
5. Deploy e confirme `https://SEU-SERVICO.onrender.com/health` retornando `{"ok":true,...}`.
6. Entre em `/login` com as credenciais configuradas. O acesso web é por HTTPS.

## 2. Gerar o EXE (em um PC Windows de desenvolvimento)
1. Instale Python apenas na máquina de desenvolvimento/compilação, não nos notebooks dos clientes.
2. Abra este diretório no Windows e execute `build_agent.bat`.
3. O EXE ficará em `dist/LocadoraAgente.exe`. Na primeira execução ele pede a URL HTTPS da central e o código de instalação. Isso evita embutir o código de instalação no binário.
4. Instale Inno Setup 6, abra `instalador_locadora.iss` e compile. O instalador estará em `installer/Instalador_Locadora_Agente.exe`.
5. Teste em uma VM Windows 10 e outra Windows 11 antes de distribuir. Assine o executável digitalmente antes de distribuição comercial, se possível.

## 3. Uso do agente
O agente inicia com janela de console visível para configuração e depois envia um check-in a cada 60 segundos. A versão atual não instala serviço do Windows nem configura início automático; isso deve ser adicionado e testado como uma etapa separada, com nome visível em Aplicativos instalados e processo de desinstalação funcional.

## 4. Segurança e operação
- Nunca compartilhe `ADMIN_PASSWORD`, `SESSION_SECRET`, `ENROLLMENT_KEY` ou token individual.
- Limite o acesso de equipe e use contas pessoais; este protótipo usa um único login administrativo global.
- Faça backup do PostgreSQL e teste a restauração.
- Não use localização por IP como se fosse GPS preciso.
- Informe os usuários e obtenha autorização apropriada para inventário e gestão do equipamento.
- Antes de produção, acrescente MFA/contas por função, rate limiting, proteção CSRF nos formulários, auditoria de ações administrativas e política de retenção.

## 5. Testes
- `/health` responde sem login.
- `/login` bloqueia acesso não autenticado ao painel.
- Cadastro de cliente e locação aparece para todos os administradores porque os dados ficam no PostgreSQL.
- O agente só faz check-in com token de dispositivo válido.
- Equipamento fica Online se houve check-in nos últimos 5 minutos; caso contrário, Offline.

## Nota sobre armazenamento
O banco SQLite local é apenas para desenvolvimento. Em Render, use PostgreSQL persistente; não dependa do disco efêmero do serviço web para dados de negócio.
