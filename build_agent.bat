@echo off
setlocal
cd /d "%~dp0"
py -m pip install --upgrade pip
py -m pip install -r requirements-agent-build.txt
py -m PyInstaller --noconfirm --clean --onefile --name LocadoraAgente --console agent\agente_locadora.py
if errorlevel 1 goto erro
echo.
echo Executavel criado em dist\LocadoraAgente.exe
pause
exit /b 0
:erro
echo Falha ao compilar. Confira as mensagens acima.
pause
exit /b 1
