; Package an existing, validated portable build. Keep AppId stable across upgrades.
#ifndef SourceDir
  #error SourceDir must identify the existing GENESIS distribution
#endif
#ifndef ReleaseVersion
  #error ReleaseVersion must match build-info.json
#endif

[Setup]
AppId={{14EF869A-8464-40A5-AF05-D75D40826B46}
AppName=GENESIS
AppVersion={#ReleaseVersion}
AppPublisher=GENESIS
AppComments=An evolving artificial life ecosystem
VersionInfoVersion={#ReleaseVersion}
VersionInfoProductName=GENESIS
DefaultDirName={localappdata}\Programs\GENESIS
DefaultGroupName=GENESIS
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
UsePreviousAppDir=yes
UsePreviousTasks=yes
Uninstallable=yes
UninstallDisplayName=GENESIS
UninstallDisplayIcon={app}\GENESIS.exe
SetupIconFile={#SourceDir}\_internal\genesis\assets\genesis.ico
OutputBaseFilename=GENESIS-{#ReleaseVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "INSTALLING.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\GENESIS"; Filename: "{app}\GENESIS.exe"; WorkingDir: "{app}"; IconFilename: "{app}\_internal\genesis\assets\genesis.ico"
Name: "{autodesktop}\GENESIS"; Filename: "{app}\GENESIS.exe"; WorkingDir: "{app}"; IconFilename: "{app}\_internal\genesis\assets\genesis.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\GENESIS.exe"; Description: "Launch GENESIS"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

; No user-data files are installed, migrated, or listed for uninstall deletion.
; Inno removes only its installed payload/shortcuts and per-user registration.
