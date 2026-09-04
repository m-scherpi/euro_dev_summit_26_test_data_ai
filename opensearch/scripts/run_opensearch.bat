@echo off
setlocal EnableDelayedExpansion
rem
rem Start, stop and inspect the local OpenSearch node prepared by
rem setup_opensearch.bat. Windows counterpart of run_opensearch.sh: the process
rem runs from build\, its PID goes to build\opensearch.pid and its output to
rem build\logs\startup.log. No service, nothing to uninstall.
rem
rem NOTE: written from the Windows documentation but not executed here; the
rem Linux script is the tested one. See the README.
rem

set "HERE=%~dp0"
for %%I in ("%HERE%..") do set "ROOT=%%~fI"
set "BUILD=%ROOT%\build"
set "PID_FILE=%BUILD%\opensearch.pid"
set "STARTUP_LOG=%BUILD%\logs\startup.log"
set "WAIT_SECONDS=180"

set "COMMAND=%~1"
if "%COMMAND%"=="" goto usage
if /I "%COMMAND%"=="-h" goto usage
if /I "%COMMAND%"=="--help" goto usage
shift

:parse
if "%~1"=="" goto parsed
if /I "%~1"=="--timeout" (set "WAIT_SECONDS=%~2" & shift & shift & goto parse)
if /I "%~1"=="-h" goto usage
if /I "%~1"=="--help" goto usage
echo error: unknown option: %~1 (try --help) 1>&2
exit /b 1

:usage
echo Usage: scripts\run_opensearch.bat {start^|stop^|status^|logs} [options]
echo.
echo Commands:
echo   start     start the node in the background and wait for the cluster
echo   stop      stop the node
echo   status    report whether it runs, and what the cluster says
echo   logs      show the tail of the startup log
echo.
echo Options:
echo   --timeout SECONDS   how long start waits for the cluster (default: 180)
echo   -h, --help          show this help
echo.
echo Example:
echo   scripts\setup_opensearch.bat --host localhost
echo   scripts\run_opensearch.bat start
echo   scripts\run_opensearch.bat status
echo   scripts\run_opensearch.bat stop
exit /b 0

:parsed

if not exist "%BUILD%\cluster.env" (
    echo error: build\cluster.env not found - run scripts\setup_opensearch.bat first 1>&2
    exit /b 1
)
for /f "usebackq tokens=1,* delims==" %%a in ("%BUILD%\cluster.env") do set "%%a=%%b"

set "BASE_URL=%CLUSTER_SCHEME%://%CLUSTER_HOST%:%CLUSTER_PORT%"
if not defined OPENSEARCH_PASSWORD set "OPENSEARCH_PASSWORD=DevSummit#2026os"
if /I "%CLUSTER_MODE%"=="insecure" (
    set "CURL_AUTH="
) else (
    set "CURL_AUTH=--cacert "%BUILD%\tls\root-ca.pem" -u admin:%OPENSEARCH_PASSWORD%"
)

if /I "%COMMAND%"=="start" goto do_start
if /I "%COMMAND%"=="stop" goto do_stop
if /I "%COMMAND%"=="status" goto do_status
if /I "%COMMAND%"=="logs" goto do_logs
echo error: unknown command: %COMMAND% (try --help) 1>&2
exit /b 1

:do_start
call :running
if "!RUNNING_PID!" NEQ "" (
    echo already running ^(pid !RUNNING_PID!^) at %BASE_URL%
    exit /b 0
)
if not exist "%OPENSEARCH_HOME%\bin\opensearch.bat" (
    echo error: %OPENSEARCH_HOME%\bin\opensearch.bat missing - re-run setup 1>&2
    exit /b 1
)
if not exist "%BUILD%\logs" mkdir "%BUILD%\logs"
echo starting OpenSearch %OPENSEARCH_VERSION% ^(%CLUSTER_MODE% mode^) ...
rem The bundled JDK, named explicitly: whatever JAVA_HOME points at on this
rem machine is not what this node was tested against.
set "OPENSEARCH_JAVA_HOME=%OPENSEARCH_HOME%\jdk"
set "OPENSEARCH_PATH_CONF=%OPENSEARCH_HOME%\config"
for /f %%p in ('powershell -NoProfile -Command "(Start-Process -FilePath '%OPENSEARCH_HOME%\bin\opensearch.bat' -WindowStyle Hidden -RedirectStandardOutput '%STARTUP_LOG%' -RedirectStandardError '%STARTUP_LOG%.err' -PassThru).Id"') do set "PID=%%p"
if not defined PID (
    echo error: could not start the process 1>&2
    exit /b 1
)
> "%PID_FILE%" echo %PID%
echo pid %PID%, log build\logs\startup.log

<nul set /p="waiting for %BASE_URL% "
for /l %%i in (1,1,%WAIT_SECONDS%) do (
    curl --silent --max-time 5 %CURL_AUTH% "%BASE_URL%/_cluster/health" >"%BUILD%\health.tmp" 2>nul
    findstr /c:"\"status\"" "%BUILD%\health.tmp" >nul 2>&1
    if not errorlevel 1 (
        echo.
        type "%BUILD%\health.tmp"
        del /q "%BUILD%\health.tmp" 2>nul
        echo.
        echo next: python scripts\index_stations.py --recreate --host %BASE_URL% ^\
        if /I "%CLUSTER_MODE%"=="insecure" (
            echo           --no-auth
        ) else (
            echo           --ca-cert build\tls\root-ca.pem
        )
        exit /b 0
    )
    <nul set /p="."
    timeout /t 1 /nobreak >nul
)
echo.
echo error: cluster did not answer within %WAIT_SECONDS%s - see build\logs\startup.log 1>&2
exit /b 1

:do_stop
call :running
if "!RUNNING_PID!"=="" (
    echo not running
    if exist "%PID_FILE%" del /q "%PID_FILE%"
    exit /b 0
)
echo stopping pid !RUNNING_PID! ...
taskkill /PID !RUNNING_PID! /T /F >nul 2>&1
if exist "%PID_FILE%" del /q "%PID_FILE%"
echo stopped
exit /b 0

:do_status
call :running
if "!RUNNING_PID!"=="" (echo not running) else (echo running, pid !RUNNING_PID!)
echo mode    : %CLUSTER_MODE%
echo endpoint: %BASE_URL%
if /I not "%CLUSTER_MODE%"=="insecure" echo CA cert : build\tls\root-ca.pem
echo health  :
curl --silent --max-time 5 %CURL_AUTH% "%BASE_URL%/_cluster/health?pretty"
exit /b 0

:do_logs
if not exist "%STARTUP_LOG%" (
    echo error: no startup log yet: %STARTUP_LOG% 1>&2
    exit /b 1
)
powershell -NoProfile -Command "Get-Content -LiteralPath '%STARTUP_LOG%' -Tail 60"
exit /b 0

:running
set "RUNNING_PID="
if not exist "%PID_FILE%" exit /b 0
set /p CANDIDATE=<"%PID_FILE%"
if "%CANDIDATE%"=="" exit /b 0
tasklist /FI "PID eq %CANDIDATE%" 2>nul | findstr /r /c:"^java" >nul
if not errorlevel 1 (set "RUNNING_PID=%CANDIDATE%") else (
    tasklist /FI "PID eq %CANDIDATE%" 2>nul | findstr /c:"%CANDIDATE%" >nul
    if not errorlevel 1 set "RUNNING_PID=%CANDIDATE%"
)
exit /b 0
