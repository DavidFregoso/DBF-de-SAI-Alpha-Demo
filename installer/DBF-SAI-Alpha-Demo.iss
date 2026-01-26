[Setup]
AppName=DBF SAI Alpha Demo
AppVersion=1.0.0
DefaultDirName={localappdata}\DBF-SAI-Alpha-Demo
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=DBF-SAI-Alpha-Demo-Setup
Compression=lzma2
SolidCompression=yes


[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"


[Files]
; Copia TODO lo que generó build_staging.ps1 (runtime + app + StartDemo.cmd)
Source: "build\staging\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs


[Icons]
Name: "{autoprograms}\DBF SAI Alpha Demo"; Filename: "{app}\StartDemo.cmd"; WorkingDir: "{app}"
Name: "{userdesktop}\DBF SAI Alpha Demo"; Filename: "{app}\StartDemo.cmd"; WorkingDir: "{app}"; Tasks: desktopicon


[Run]
Filename: "{app}\StartDemo.cmd"; WorkingDir: "{app}"; Description: "Abrir dashboard"; Flags: nowait postinstall skipifsilent
