@echo off
setlocal
set "ROOT=%~dp0"
set "PATH=%ROOT%runtime;%ROOT%runtime\Library\bin;%ROOT%runtime\Scripts;%PATH%"
set "GI_TYPELIB_PATH=%ROOT%runtime\Library\lib\girepository-1.0"
set "XDG_DATA_DIRS=%ROOT%runtime\Library\share;%XDG_DATA_DIRS%"
start "Compress Images" /b "%ROOT%runtime\pythonw.exe" "%ROOT%app\compress_images_gui.py"
