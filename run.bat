@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo === Disk Audit ===
echo.

set "PY="
where py >nul 2>&1
if %ERRORLEVEL%==0 (
  set "PY=py -3"
) else (
  python --version >nul 2>&1
  if %ERRORLEVEL%==0 (
    set "PY=python"
  )
)

if not defined PY (
  echo Erro: Python 3 nao encontrado. Instale Python e tente novamente.
  pause
  exit /b 1
)

if not exist "disk.csv" (
  echo Erro: disk.csv nao encontrado.
  echo Exporte um CSV do WinDirStat e coloque nesta pasta.
  pause
  exit /b 1
)

echo Instalando pacote em modo editavel...
%PY% -m pip install -e . -q
if errorlevel 1 (
  echo Erro ao instalar dependencias.
  pause
  exit /b 1
)

echo Validando CSV...
%PY% scripts\validate_csv.py disk.csv
if errorlevel 1 (
  echo CSV invalido. Corrija o export e tente novamente.
  pause
  exit /b 1
)

echo Executando auditoria...
%PY% -m diskaudit.cli disk.csv -o disk_report.html
if errorlevel 1 (
  echo.
  echo Falha na execucao.
  pause
  exit /b 1
)

echo.
echo Relatorio gerado: disk_report.html
start "" "disk_report.html"
pause
