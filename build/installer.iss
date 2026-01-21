#define AppName "SAI Alpha Dashboard Demo"
#define AppVersion "1.0.0"
#define AppPublisher "SAI Alpha"
#define AppExeName "StartDemo.cmd"

[Setup]
AppId={{9F3B0C63-7C2F-4C1F-9A7C-7C95C6D87651}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputBaseFilename=SAI-Alpha-Dashboard-Demo-Installer
Compression=lzma
SolidCompression=yes
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "build\staging\StartDemo.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "build\staging\runtime\*"; DestDir: "{app}\runtime"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "build\staging\app\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Start Demo"; Filename: "{app}\{#AppExeName}"
Name: "{commondesktop}\Start Demo"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Start Demo"; Flags: nowait postinstall skipifsilent
