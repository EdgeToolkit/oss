@ECHO OFF
SETLOCAL
set _DIR=%~dp0
pushd %_DIR%\..\..
set _TOP=%CD%
python %_DIR%\gitlab-ci.py generate %*
popd
ENDLOCAL
