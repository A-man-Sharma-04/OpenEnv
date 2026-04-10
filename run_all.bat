@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

set "PYTHON_CMD="
if exist ".venv\Scripts\python.exe" set "PYTHON_CMD=.venv\Scripts\python.exe"

if not defined PYTHON_CMD (
  where py >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
  where python >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
  echo [ERROR] No Python executable found.
  echo [HINT] Create .venv or install Python and add it to PATH.
  exit /b 1
)

set "MODE=%~1"
if "%MODE%"=="" set "MODE=all"

if "%HOST%"=="" (
  set "API_BIND_HOST=127.0.0.1"
) else (
  set "API_BIND_HOST=%HOST%"
)
if "%PORT%"=="" (
  set "API_PORT=7860"
) else (
  set "API_PORT=%PORT%"
)

set "API_BROWSER_HOST=%API_BIND_HOST%"
if /I "%API_BROWSER_HOST%"=="0.0.0.0" set "API_BROWSER_HOST=127.0.0.1"
set "DEFAULT_API_BASE_URL=http://%API_BROWSER_HOST%:%API_PORT%"

if /I "%MODE%"=="help" (
  set "USAGE_EXIT=0"
  goto :usage
)
if /I "%MODE%"=="all" goto :run_all
if /I "%MODE%"=="validate" goto :run_validate
if /I "%MODE%"=="tests" goto :run_tests
if /I "%MODE%"=="api" goto :run_api
if /I "%MODE%"=="inference" goto :run_inference

echo [ERROR] Unknown mode: %MODE%
set "USAGE_EXIT=1"
goto :usage

:run_all
echo [INFO] Running validate.py
call :run_validate || exit /b 1

echo [INFO] Running pytest tests
call :run_tests || exit /b 1

echo [INFO] Starting API server in a new terminal window
call :run_api || exit /b 1

echo [INFO] Running inference.py
call :run_inference || exit /b 1

echo [OK] All selected tasks completed.
exit /b 0

:run_validate
%PYTHON_CMD% validate.py
if errorlevel 1 (
  echo [ERROR] validate.py failed.
  exit /b 1
)
exit /b 0

:run_tests
%PYTHON_CMD% -m pytest -q tests
if errorlevel 1 (
  echo [ERROR] Tests failed.
  exit /b 1
)
exit /b 0

:run_api
echo [INFO] API URL: %DEFAULT_API_BASE_URL%
start "OpenEnv API" cmd /k "set HOST=%API_BIND_HOST%&& set PORT=%API_PORT%&& %PYTHON_CMD% app.py"
if errorlevel 1 (
  echo [ERROR] Failed to start API server.
  exit /b 1
)
exit /b 0

:run_inference
if "%API_BASE_URL%"=="" set "API_BASE_URL=%DEFAULT_API_BASE_URL%"
set "OPENENV_INFER_CMD=set API_BASE_URL=%API_BASE_URL%&& %PYTHON_CMD% inference.py"
cmd /c "%OPENENV_INFER_CMD%"
if errorlevel 1 (
  echo [ERROR] inference.py failed.
  echo [HINT] Set required env vars, for example MODEL_NAME and HF_TOKEN.
  exit /b 1
)
exit /b 0

:usage
if "%USAGE_EXIT%"=="" set "USAGE_EXIT=1"
echo Usage: run_all.bat [all^|validate^|tests^|api^|inference^|help]
echo.
echo   all        Run validate, tests, start API, then run inference
echo   validate   Run validate.py only
echo   tests      Run pytest only
echo   api        Start API server only
echo   inference  Run inference.py only
echo.
echo Environment overrides:
echo   HOST       API bind host (default 127.0.0.1)
echo   PORT       API port (default 7860)
echo   API_BASE_URL  Inference target URL (default uses HOST/PORT)
exit /b %USAGE_EXIT%
