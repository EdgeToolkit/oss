@ECHO OFF
SETLOCAL
set _DIR=%~dp0
pushd %_DIR%\..\..
set _TOP=%CD%
REM set PYTHONPATH=%_TOP%\.toolkit\lib;%PYTHONPATH%
python %_TOP%\.toolkit\lib\ci.py %*
popd
ENDLOCAL
