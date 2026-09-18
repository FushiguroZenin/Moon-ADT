#define AppName "Moon"
#define AppVersion "0.1.0"
#define AppPublisher "Moon"
#define AppExeName "MoonRuntime.exe"

[Setup]
AppId={{1B602232-3C2C-478F-AE3F-0E509DA3AD99}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
VersionInfoVersion={#AppVersion}
VersionInfoProductVersion={#AppVersion}
UninstallDisplayName=Moon
UninstallDisplayIcon={app}\{#AppExeName}
DefaultDirName={localappdata}\Moon
DefaultGroupName=Moon
DisableProgramGroupPage=yes
OutputDir=..\installer-output
OutputBaseFilename=Moon-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern

[Files]
Source: "..\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Moon"; Filename: "{app}\{#AppExeName}"
Name: "{userstartup}\Moon Local Runtime"; Filename: "{app}\{#AppExeName}"; Parameters: "--background"

[Run]
Filename: "{app}\{#AppExeName}"; Parameters: "--setup"; Description: "Open Moon setup"; Flags: nowait postinstall skipifsilent
