@echo off
setlocal EnableDelayedExpansion
rem
rem Download and configure a local, single-node OpenSearch for ArcGIS testing.
rem Windows counterpart of setup_opensearch.sh - same behaviour, same options,
rem same build/ layout. Nothing is installed system-wide and no admin rights
rem are needed.
rem
rem NOTE: this file was written from the Windows documentation but not executed
rem here; the Linux script is the tested one. See the README.
rem
rem A "!" in --password does not survive cmd: see the KEYSTORE_PASSWORD note
rem below. Use a password without it.
rem
rem The version is pinned to 2.12.0 in input\opensearch_dist.json because
rem ArcGIS Pro 3.7 and ArcGIS Enterprise 12.1 certify exactly OpenSearch 2.12.
rem The checksum is the one OpenSearch publishes; a mismatch aborts.
rem
rem The HTTPS certificate is generated with the keytool of OpenSearch's own
rem bundled JDK, not taken from the demo configuration: the demo root CA of
rem 2.12.0 was issued 2023-08-29 with a 30-day validity and expired 2023-09-28,
rem so every client rejects it with "certificate has expired". --demo-certs
rem keeps the broken configuration, for demonstrating the failure.
rem

set "HERE=%~dp0"
for %%I in ("%HERE%..") do set "ROOT=%%~fI"
set "MANIFEST=%ROOT%\input\opensearch_dist.json"
set "BUILD=%ROOT%\build"

set "HOST=localhost"
set "MODE=secure"
set "ALLOW_MMAP=true"
set "FORCE=false"
set "OWN_CERTS=true"
set "EXTRA_SAN="
rem Protects the generated PKCS#12 keystores inside build\, which is gitignored.
set "KEYSTORE_PASSWORD=devsummit"
rem Neither password contains "!". Under EnableDelayedExpansion cmd removes an
rem unmatched "!" from any `set "VAR=..."` - including one arriving via
rem --password or the environment - so the node would silently end up with a
rem different password than the documented one, and every client gets a 401.
if defined OPENSEARCH_INITIAL_ADMIN_PASSWORD (
    set "PASSWORD=%OPENSEARCH_INITIAL_ADMIN_PASSWORD%"
) else (
    set "PASSWORD=DevSummit#2026os"
)

:parse
if "%~1"=="" goto parsed
if /I "%~1"=="--host" (set "HOST=%~2" & shift & shift & goto parse)
if /I "%~1"=="--insecure" (set "MODE=insecure" & shift & goto parse)
if /I "%~1"=="--no-mmap" (set "ALLOW_MMAP=false" & shift & goto parse)
if /I "%~1"=="--san" (set "EXTRA_SAN=!EXTRA_SAN!,%~2" & shift & shift & goto parse)
if /I "%~1"=="--demo-certs" (set "OWN_CERTS=false" & shift & goto parse)
if /I "%~1"=="--password" (set "PASSWORD=%~2" & shift & shift & goto parse)
if /I "%~1"=="--force" (set "FORCE=true" & shift & goto parse)
if /I "%~1"=="-h" goto usage
if /I "%~1"=="--help" goto usage
echo error: unknown option: %~1 (try --help) 1>&2
exit /b 1

:usage
echo Usage: scripts\setup_opensearch.bat [options]
echo.
echo Download OpenSearch 2.12.0 into build\ and configure it as a single node.
echo.
echo Options:
echo   --host HOST      address OpenSearch binds to and that the TLS certificate
echo                    has to match. Use the machine's hostname or IP if ArcGIS
echo                    Pro runs elsewhere (default: localhost)
echo   --insecure       disable the security plugin: plain HTTP, no credentials.
echo                    Convenient for curl, not the configuration ArcGIS is
echo                    documented against - it needs basic auth
echo   --no-mmap        set node.store.allow_mmap: false
echo   --san NAME       extra subject alternative name for the HTTPS certificate.
echo                    Repeatable. Prefix with 'ip:' for an address
echo   --demo-certs     keep OpenSearch's own demo certificates instead of
echo                    generating one. Their root CA expired on 2023-09-28, so
echo                    every client will reject the connection
echo   --password PW    admin password. Must pass OpenSearch's strength check -
echo                    'admin' does not (default: the committed demo password).
echo                    Avoid an exclamation mark: cmd removes it from the value
echo   --force          re-extract and re-configure, wiping the data directory
echo   -h, --help       show this help
echo.
echo Example:
echo   scripts\setup_opensearch.bat --host localhost
echo   scripts\run_opensearch.bat start
echo.
echo Requires: PowerShell 5.1+, python (or py -3).
exit /b 0

:parsed

rem -- locate python -----------------------------------------------------------
set "PYTHON="
where python >nul 2>&1 && set "PYTHON=python"
if not defined PYTHON (where py >nul 2>&1 && set "PYTHON=py -3")
if not defined PYTHON (
    echo error: python is required ^(it reads the manifest^) 1>&2
    exit /b 1
)
if not exist "%MANIFEST%" (
    echo error: manifest not found: %MANIFEST% 1>&2
    exit /b 1
)

rem -- read the manifest -------------------------------------------------------
set "PLATFORM=windows-x64"
for /f "tokens=1-5" %%a in ('%PYTHON% -c "import json,sys;m=json.load(open(r'%MANIFEST%',encoding='utf-8'));d=m['distributions']['%PLATFORM%'];print(m['version'],d['file'],d['url'],d['bytes'],d['sha512'])"') do (
    set "VERSION=%%a"
    set "FILE=%%b"
    set "URL=%%c"
    set "BYTES=%%d"
    set "SHA512=%%e"
)
if not defined VERSION (
    echo error: could not read the distribution manifest 1>&2
    exit /b 1
)

set "OS_HOME=%BUILD%\opensearch-%VERSION%"
set "ARCHIVE=%BUILD%\dist\%FILE%"

echo OpenSearch %VERSION% (%PLATFORM%), pinned by input\opensearch_dist.json
echo   ArcGIS Pro 3.7 / Enterprise 12.1 certify exactly this release line

rem -- download ----------------------------------------------------------------
if not exist "%BUILD%\dist" mkdir "%BUILD%\dist"

set "NEED_DOWNLOAD=true"
if exist "%ARCHIVE%" (
    for /f %%h in ('powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA512 -LiteralPath '%ARCHIVE%').Hash.ToLower()"') do set "ACTUAL=%%h"
    if /I "!ACTUAL!"=="%SHA512%" (
        echo archive already present and checksum matches: build\dist\%FILE%
        set "NEED_DOWNLOAD=false"
    ) else (
        echo archive present but checksum does not match - downloading again
        del /q "%ARCHIVE%"
    )
)

if "!NEED_DOWNLOAD!"=="true" (
    set /a MB=%BYTES% / 1048576
    echo downloading %FILE% ^(!MB! MB^) ...
    powershell -NoProfile -Command "$ProgressPreference='Continue'; Invoke-WebRequest -Uri '%URL%' -OutFile '%ARCHIVE%.part' -UseBasicParsing"
    if errorlevel 1 (
        echo error: download failed 1>&2
        exit /b 1
    )
    move /y "%ARCHIVE%.part" "%ARCHIVE%" >nul
    for /f %%h in ('powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA512 -LiteralPath '%ARCHIVE%').Hash.ToLower()"') do set "ACTUAL=%%h"
    if /I not "!ACTUAL!"=="%SHA512%" (
        del /q "%ARCHIVE%"
        echo error: checksum mismatch for %FILE% 1>&2
        echo   expected %SHA512% 1>&2
        echo   actual   !ACTUAL! 1>&2
        echo The download was corrupt or the artifact changed. Nothing was installed. 1>&2
        exit /b 1
    )
    echo checksum verified ^(sha512, as published by OpenSearch^)
)

rem -- extract -----------------------------------------------------------------
if exist "%OS_HOME%" if /I not "%FORCE%"=="true" (
    echo installation already present: build\opensearch-%VERSION% ^(use --force to redo^)
    goto configure
)
if exist "%OS_HOME%" (
    echo removing previous installation
    rmdir /s /q "%OS_HOME%"
)
echo extracting into build\ ...
powershell -NoProfile -Command "Expand-Archive -LiteralPath '%ARCHIVE%' -DestinationPath '%BUILD%' -Force"
if not exist "%OS_HOME%" (
    echo error: archive did not contain opensearch-%VERSION%\ 1>&2
    exit /b 1
)

:configure
if not exist "%BUILD%\data" mkdir "%BUILD%\data"
if not exist "%BUILD%\logs" mkdir "%BUILD%\logs"
if not exist "%BUILD%\tls" mkdir "%BUILD%\tls"

set "CONFIG=%OS_HOME%\config\opensearch.yml"
set "DATA_YAML=%BUILD:\=/%/data"
set "LOGS_YAML=%BUILD:\=/%/logs"

> "%CONFIG%" echo # Written by scripts\setup_opensearch.bat - do not edit by hand, re-run the
>>"%CONFIG%" echo # script instead. A single throwaway node for local ArcGIS testing.
>>"%CONFIG%" echo cluster.name: devsummit
>>"%CONFIG%" echo node.name: devsummit-node-1
>>"%CONFIG%" echo discovery.type: single-node
>>"%CONFIG%" echo.
>>"%CONFIG%" echo network.host: %HOST%
>>"%CONFIG%" echo http.port: 9200
>>"%CONFIG%" echo.
>>"%CONFIG%" echo path.data: %DATA_YAML%
>>"%CONFIG%" echo path.logs: %LOGS_YAML%
>>"%CONFIG%" echo.
>>"%CONFIG%" echo # 449 documents do not need memory mapping.
>>"%CONFIG%" echo node.store.allow_mmap: %ALLOW_MMAP%

if /I "%MODE%"=="insecure" (
    >>"%CONFIG%" echo.
    >>"%CONFIG%" echo # --insecure: the security plugin is off. Plain HTTP, no authentication,
    >>"%CONFIG%" echo # no TLS. ArcGIS is documented against basic authentication, so this mode
    >>"%CONFIG%" echo # is for curl and debugging, not for the ArcGIS connection.
    >>"%CONFIG%" echo plugins.security.disabled: true
    echo configured WITHOUT the security plugin: http://%HOST%:9200, no credentials
    set "SCHEME=http"
) else (
    set "DEMO=%OS_HOME%\plugins\opensearch-security\tools\install_demo_configuration.bat"
    if not exist "!DEMO!" (
        echo error: security demo installer not found at !DEMO! 1>&2
        exit /b 1
    )
    echo installing demo TLS certificates and the admin user ...
    set "OPENSEARCH_INITIAL_ADMIN_PASSWORD=%PASSWORD%"
    call "!DEMO!" -y -i -s
    if errorlevel 1 (
        echo error: the demo security installer failed. The most common cause is a 1>&2
        echo password that does not pass the strength check - 'admin' does not. Pass a 1>&2
        echo stronger one with --password. 1>&2
        exit /b 1
    )
    if not exist "%OS_HOME%\config\root-ca.pem" (
        echo error: expected root-ca.pem in config\ after setup 1>&2
        exit /b 1
    )
    if /I "%OWN_CERTS%"=="true" (
        call :make_certs
        if errorlevel 1 exit /b 1
    ) else (
        copy /y "%OS_HOME%\config\root-ca.pem" "%BUILD%\tls\root-ca.pem" >nul
        echo keeping the demo certificates ^(--demo-certs^)
        echo   WARNING: their root CA expired on 2023-09-28. Clients will fail with
        echo   'certificate has expired'. This is the upstream default, not a bug here.
    )
    echo configured WITH TLS and basic auth: https://%HOST%:9200
    echo   user     : admin
    echo   password : %PASSWORD%
    echo   CA cert  : build\tls\root-ca.pem
    echo.
    echo   The CA is a private one. ArcGIS Pro will refuse the connection until
    echo   build\tls\root-ca.pem is imported into the Windows certificate store
    echo   under Trusted Root Certification Authorities.
    set "SCHEME=https"
)

rem State the other scripts read, so nobody has to remember which mode this is.
> "%BUILD%\cluster.env" echo OPENSEARCH_HOME=%OS_HOME%
>>"%BUILD%\cluster.env" echo OPENSEARCH_VERSION=%VERSION%
>>"%BUILD%\cluster.env" echo CLUSTER_MODE=%MODE%
>>"%BUILD%\cluster.env" echo CLUSTER_HOST=%HOST%
>>"%BUILD%\cluster.env" echo CLUSTER_SCHEME=!SCHEME!
>>"%BUILD%\cluster.env" echo CLUSTER_PORT=9200

echo.
echo done. Next:
echo   scripts\run_opensearch.bat start
if /I "%MODE%"=="insecure" (
    echo   python scripts\index_stations.py --recreate --host http://%HOST%:9200 --no-auth
) else (
    echo   python scripts\index_stations.py --recreate --host https://%HOST%:9200 --ca-cert build\tls\root-ca.pem
)
endlocal
exit /b 0

rem ---------------------------------------------------------------------------
rem Generate a private CA and an HTTPS certificate for it, using the keytool of
rem OpenSearch's bundled JDK. A real two-level chain rather than one self-signed
rem certificate, for two reasons: OpenSearch Security drops any certificate
rem carrying basicConstraints CA:true out of the server chain, and a Windows
rem trust store wants a proper CA in Trusted Root Certification Authorities.
rem ---------------------------------------------------------------------------
:make_certs
set "KEYTOOL=%OS_HOME%\jdk\bin\keytool.exe"
if not exist "%KEYTOOL%" (
    echo error: keytool not found in the bundled JDK: %KEYTOOL% 1>&2
    exit /b 1
)
set "CA_STORE=%BUILD%\tls\ca.p12"
set "HTTP_STORE=%OS_HOME%\config\http.p12"

rem localhost and the loopback addresses are always in, so a cluster bound to a
rem hostname stays reachable from the machine it runs on.
set "SAN=dns:localhost,ip:127.0.0.1,ip:::1"
if /I not "%HOST%"=="localhost" if not "%HOST%"=="127.0.0.1" (
    echo %HOST% | findstr /r "^[0-9][0-9.]*$" >nul
    if errorlevel 1 (set "SAN=!SAN!,dns:%HOST%") else (set "SAN=!SAN!,ip:%HOST%")
)
set "SAN=!SAN!!EXTRA_SAN!"

echo generating a CA and an HTTPS certificate for %HOST% ^(SAN: !SAN!^) ...
echo   reason: the demo root CA of OpenSearch 2.12.0 expired on 2023-09-28
if exist "%CA_STORE%" del /q "%CA_STORE%"
if exist "%HTTP_STORE%" del /q "%HTTP_STORE%"
if exist "%BUILD%\tls\root-ca.pem" del /q "%BUILD%\tls\root-ca.pem"

"%KEYTOOL%" -genkeypair -alias ca -keyalg RSA -keysize 2048 -validity 3650 ^
    -dname "CN=DevSummit Local Test CA, OU=devsummit, O=devsummit, C=de" ^
    -ext "bc:c=ca:true,pathlen:0" -ext "ku:c=keyCertSign,cRLSign" ^
    -keystore "%CA_STORE%" -storetype PKCS12 ^
    -storepass "%KEYSTORE_PASSWORD%" -keypass "%KEYSTORE_PASSWORD%" >nul 2>&1
if errorlevel 1 (echo error: keytool failed to generate the CA 1>&2 & exit /b 1)

"%KEYTOOL%" -genkeypair -alias http -keyalg RSA -keysize 2048 -validity 3650 ^
    -dname "CN=%HOST%, OU=devsummit, O=devsummit, C=de" ^
    -keystore "%HTTP_STORE%" -storetype PKCS12 ^
    -storepass "%KEYSTORE_PASSWORD%" -keypass "%KEYSTORE_PASSWORD%" >nul 2>&1
if errorlevel 1 (echo error: keytool failed to generate the node key pair 1>&2 & exit /b 1)

"%KEYTOOL%" -exportcert -rfc -alias ca -keystore "%CA_STORE%" -storetype PKCS12 ^
    -storepass "%KEYSTORE_PASSWORD%" -file "%BUILD%\tls\root-ca.pem" >nul 2>&1
if errorlevel 1 (echo error: keytool failed to export the CA certificate 1>&2 & exit /b 1)

"%KEYTOOL%" -certreq -alias http -keystore "%HTTP_STORE%" -storetype PKCS12 ^
    -storepass "%KEYSTORE_PASSWORD%" -file "%BUILD%\tls\http.csr" 2>nul
if errorlevel 1 (echo error: keytool failed to create the CSR 1>&2 & exit /b 1)

"%KEYTOOL%" -gencert -alias ca -keystore "%CA_STORE%" -storetype PKCS12 ^
    -storepass "%KEYSTORE_PASSWORD%" -validity 3650 -rfc ^
    -ext "san=!SAN!" -ext "bc:c=ca:false" ^
    -ext "ku:c=digitalSignature,keyEncipherment" -ext "eku=serverAuth" ^
    -infile "%BUILD%\tls\http.csr" -outfile "%BUILD%\tls\http-cert.pem" 2>nul
if errorlevel 1 (echo error: keytool failed to sign the node certificate 1>&2 & exit /b 1)

rem Importing the reply needs the whole chain in one file, and the CA has to be
rem a known entry in the keystore first.
"%KEYTOOL%" -importcert -noprompt -alias ca -file "%BUILD%\tls\root-ca.pem" ^
    -keystore "%HTTP_STORE%" -storetype PKCS12 -storepass "%KEYSTORE_PASSWORD%" >nul 2>&1
if errorlevel 1 (echo error: keytool failed to import the CA 1>&2 & exit /b 1)

copy /b /y "%BUILD%\tls\http-cert.pem"+"%BUILD%\tls\root-ca.pem" "%BUILD%\tls\http-chain.pem" >nul
"%KEYTOOL%" -importcert -noprompt -alias http -file "%BUILD%\tls\http-chain.pem" ^
    -keystore "%HTTP_STORE%" -storetype PKCS12 -storepass "%KEYSTORE_PASSWORD%" >nul 2>&1
if errorlevel 1 (echo error: keytool failed to import the signed certificate 1>&2 & exit /b 1)

rem Replace the demo HTTP certificate settings the installer appended. Appending
rem instead would leave duplicate YAML keys, which OpenSearch refuses to parse.
powershell -NoProfile -Command "(Get-Content -LiteralPath '%CONFIG%') | Where-Object { $_ -notmatch '^plugins\.security\.ssl\.http\.pem' } | Set-Content -LiteralPath '%CONFIG%'"
>>"%CONFIG%" echo.
>>"%CONFIG%" echo # Generated HTTPS certificate, replacing the demo one whose root CA expired
>>"%CONFIG%" echo # on 2023-09-28. Transport TLS still uses the demo certificates: they run to
>>"%CONFIG%" echo # 2033 and a single node never opens a transport connection to a peer. Only
>>"%CONFIG%" echo # the HTTP layer is what ArcGIS - and every other client - validates.
>>"%CONFIG%" echo plugins.security.ssl.http.keystore_filepath: http.p12
>>"%CONFIG%" echo plugins.security.ssl.http.keystore_type: PKCS12
>>"%CONFIG%" echo plugins.security.ssl.http.keystore_alias: http
>>"%CONFIG%" echo plugins.security.ssl.http.keystore_password: %KEYSTORE_PASSWORD%
>>"%CONFIG%" echo plugins.security.ssl.http.clientauth_mode: NONE
exit /b 0
