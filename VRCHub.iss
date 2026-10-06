; VRCHub installer script - compiled by GitHub Actions with Inno Setup
; Produces vrchub_setup.exe: installs to Program Files, desktop +
; Start Menu shortcuts, adds uninstaller, same as any normal app.

[Setup]
AppName=VRCHub
AppVersion=6.5.1
AppPublisher=Ben Heck
DefaultDirName={autopf}\VRCHub
DefaultGroupName=VRCHub
OutputDir=installer
OutputBaseFilename=vrchub_setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
WizardStyle=modern
UninstallDisplayIcon={app}\VRCHub.ico
SetupIconFile=VRCHub.ico

[Files]
Source: "dist\VRCHub.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "VRCHub.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\VRCHub"; Filename: "{app}\VRCHub.exe"; IconFilename: "{app}\VRCHub.ico"
Name: "{group}\VRCHub"; Filename: "{app}\VRCHub.exe"; IconFilename: "{app}\VRCHub.ico"
Name: "{group}\Uninstall VRCHub"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\VRCHub.exe"; Description: "Launch VRCHub"; Flags: nowait postinstall skipifsilent
