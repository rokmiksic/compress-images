@echo off
setlocal
set "ROOT=%~dp0"
set "PATH=%ROOT%runtime;%ROOT%runtime\Library\bin;%ROOT%runtime\Scripts;%PATH%"
set "GI_TYPELIB_PATH=%ROOT%runtime\Library\lib\girepository-1.0"
set "XDG_DATA_DIRS=%ROOT%runtime\Library\share;%XDG_DATA_DIRS%"
"%ROOT%runtime\python.exe" "%ROOT%app\compress_images_core.py" %*
