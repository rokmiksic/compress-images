#define AppVersion GetEnv("APP_VERSION")

[Setup]
AppId={{B6AC04D9-C0D9-4E43-98B7-7B2C1D55D6F2}
AppName=Compress Images
AppVersion={#AppVersion}
AppPublisher=rokmiksic
AppPublisherURL=https://github.com/rokmiksic/compress-images
AppSupportURL=https://github.com/rokmiksic/compress-images/issues
DefaultDirName={autopf}\Compress Images
DefaultGroupName=Compress Images
OutputDir=build
OutputBaseFilename=compress-images-windows-x64-setup
SetupIconFile=compress-images.ico
UninstallDisplayIcon={app}\compress-images.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "build\CompressImagesPortable\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Compress Images"; Filename: "{app}\CompressImagesGUI.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\compress-images.ico"
Name: "{autodesktop}\Compress Images"; Filename: "{app}\CompressImagesGUI.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\compress-images.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\CompressImagesGUI.cmd"; Description: "Launch Compress Images"; WorkingDir: "{app}"; Flags: postinstall nowait skipifsilent
