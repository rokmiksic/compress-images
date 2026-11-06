Compress Images for Windows

For the normal installed version, use the Windows installer from the GitHub Release.
This portable folder is useful when you do not want to install the application.

1. Extract this folder to a location where you have write permission.
2. Double-click CompressImagesGUI.cmd to start the GUI.
3. For the command line, open a terminal in this folder and run:
   CompressImagesCLI.cmd 1 --max-dimension 2400

The portable bundle includes Python, GTK4/PyGObject, ImageMagick, FFmpeg and libheif.
Original images are never modified. Settings are stored in %APPDATA%\compress-images.
