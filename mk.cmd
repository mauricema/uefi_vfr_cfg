@echo off

set SETUP_BSF=Build\Setup.bsf
set SETUP_INC=Build\Setup.inc
set SETUP_DSC=Build\Setup.dsc
set SETUP_YML=Build\Setup.yaml
set SETUP_BIN=Build\Setup.yaml
set SETUP_PKL=Build\Setup.pkl
set SETUP_JSN=Build\Setup.json
python Tools\BiosVfr2Dsc.py Build\PayloadPkg\DEBUG_VS2017\IA32\PayloadPkg\Setup\PlatformSetupDxe\OUTPUT\PlatformSetupDxeStrDefs.hpk Build\PayloadPkg\DEBUG_VS2017\IA32\PayloadPkg\Setup\PlatformSetupDxe\OUTPUT\Vfr.i > %SETUP_INC%

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

echo.

echo Run following to run setup browser
echo   python Tools\SblSetup.py %SETUP_JSN% %SETUP_BIN%
echo   python Tools\ConfigEditor.py

