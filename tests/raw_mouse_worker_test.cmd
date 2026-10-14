@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0.."
if not exist tests\raw_mouse_worker_fixture mkdir tests\raw_mouse_worker_fixture
"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /target:exe /platform:x64 /optimize+ /out:tests\raw_mouse_worker_fixture\MouseInputWorkerAudit.exe /reference:System.Windows.Forms.dll /reference:System.Drawing.dll tests\MouseInputWorkerAudit.cs src\MouseInputWorker.cs
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /O2 /W4 runtime\raw_mouse_worker_test.cpp /Fe:tests\raw_mouse_worker_fixture\Protocol.exe /Fo:tests\raw_mouse_worker_fixture\Protocol.obj user32.lib
if errorlevel 1 exit /b 1
tests\raw_mouse_worker_fixture\Protocol.exe
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHsc /O2 /W4 runtime\raw_mouse_worker_smoke.cpp /Fe:tests\raw_mouse_worker_fixture\AceCombat8.exe /Fo:tests\raw_mouse_worker_fixture\Smoke.obj user32.lib
if errorlevel 1 exit /b 1
tests\raw_mouse_worker_fixture\AceCombat8.exe "%cd%\tests\raw_mouse_worker_fixture\MouseInputWorkerAudit.exe"
if errorlevel 1 exit /b 1
copy /y tests\raw_mouse_worker_fixture\AceCombat8.exe tests\raw_mouse_worker_fixture\WrongGame.exe >nul
tests\raw_mouse_worker_fixture\WrongGame.exe "%cd%\tests\raw_mouse_worker_fixture\MouseInputWorkerAudit.exe"
exit /b %errorlevel%
