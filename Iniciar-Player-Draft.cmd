@echo off
setlocal
cd /d "%~dp0"
echo Player Draft - Scouting de Clubes
if not exist ".venv\Scripts\python.exe" python -m venv .venv
if errorlevel 1 goto erro
if not exist ".venv\.player-draft-ready" (
  ".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
  if errorlevel 1 goto erro
  type nul > ".venv\.player-draft-ready"
)
echo.
echo Abra http://127.0.0.1:5000 no navegador.
echo Mercado Transfermarkt: base de 06/07/2026. Estatisticas: Sofascore.
echo Mantenha esta janela aberta. Para encerrar, pressione Ctrl+C.
cd backend
"..\.venv\Scripts\python.exe" -m flask --app app run --host 127.0.0.1 --port 5000
pause
exit /b
:erro
echo Nao foi possivel preparar o ambiente. Verifique Python 3.11+ e a conexao.
pause
exit /b 1
