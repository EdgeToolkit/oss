@ECHO OFF
set _DIR=%~dp0
python %~dp0\gitlab-ci.py generate %*
