@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo === Disk Audit ===
echo.

where py >nul 2>&1
if %ERRORLEVEL%==0 goto :run_py

python --version >nul 2>&1
if %ERRORLEVEL%==0 goto :run_python

echo Erro: Python 3 nao encontrado. Instale Python e tente novamente.
pause
exit /b 1

:run_py
echo Verificando dependencias...
py -3 -m pip install -r requirements.txt -q
if errorlevel 1 goto :pip_error

if not exist "disk.csv" (
    echo Erro: disk.csv nao encontrado.
    echo Exporte um CSV do WinDirStat e coloque nesta pasta.
    pause
    exit /b 1
)

echo Executando auditoria...
py -3 disk_audit.py
if errorlevel 1 goto :run_error
goto :done

:run_python
echo Verificando dependencias...
python -m pip install -r requirements.txt -q
if errorlevel 1 goto :pip_error

if not exist "disk.csv" (
    echo Erro: disk.csv nao encontrado.
    echo Exporte um CSV do WinDirStat e coloque nesta pasta.
    pause
    exit /b 1
)

echo Executando auditoria...
python disk_audit.py
if errorlevel 1 goto :run_error
goto :done

:pip_error
echo Erro ao instalar dependencias.
pause
exit /b 1

:run_error
echo.
echo Falha na execucao.
pause
exit /b 1

:done
echo.
echo Relatorio gerado: disk_report.html
start "" "disk_report.html"
pause
