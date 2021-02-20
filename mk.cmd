@echo off

if "%1" == "build"     goto Build

if "%1" == "setup"     goto Setup

if "%1" == "run"       goto Run

if "%1" == "mpy"       goto RunMpy

goto :eof

:Build
set  TOOLCHAIN=VS2017
call edksetup.bat
cd   BaseTools
call toolsetup.bat
cd   ..
call build -p TestPkg\TestPkg.dsc -a IA32 -t %TOOLCHAIN%
goto :eof

:Setup
set SETUP_BSF=Build\Setup.bsf
set SETUP_INC=Build\Setup.inc
set SETUP_DSC=Build\Setup.dsc
set SETUP_YML=Build\Setup.yaml
set SETUP_BIN=Build\Setup.bin
set SETUP_PKL=Build\Setup.pkl
set SETUP_JSN=Build\Setup.json
python Tools\BiosVfr2Dsc.py Build\TestPkg\DEBUG_VS2017\IA32\TestPkg\Setup\PlatformSetupDxe\OUTPUT\PlatformSetupDxeStrDefs.hpk ^
       Build\TestPkg\DEBUG_VS2017\IA32\TestPkg\Setup\PlatformSetupDxe\OUTPUT\Vfr.i > %SETUP_INC%

setlocal EnableDelayedExpansion
  set "line="
  for %%a in (
      "fi=open(r'%SETUP_DSC%','w');fi.write('[PcdsDynamicVpd.Upd]\n\n\x21include %SETUP_INC%\n');fi.close()"
  ) do set line=!line!%%~a
  python -c "!line!"
endlocal

python Tools\FspDscBsf2Yaml.py %SETUP_DSC% %SETUP_YML%
python Tools\GenCfgData.py GENPKL %SETUP_YML% %SETUP_PKL%
python Tools\GenCfgData.py GENBIN %SETUP_YML% %SETUP_BIN%
goto :eof

:Run
python Tools\ConfigEditor.py %SETUP_YML%
goto :eof

:RunMpy
echo Run following to start setup browser on target uisng MicroPython environment
echo   python Tools\SblSetup.py %SETUP_JSN% %SETUP_BIN%
echo.
echo It can be also launched on host uisng PuTTY named pipe conneciton
echo   python Tools\SblSetup.py %SETUP_JSN% %SETUP_BIN%
echo.
echo Now, please open PuTTY with Serial connection type, and set Serila line to "\\.\pipe\TermPipe"
echo   then set termin Window size to 100x30.
echo.
python Tools\SblSetup.py %SETUP_JSN% %SETUP_BIN%
goto :eof



