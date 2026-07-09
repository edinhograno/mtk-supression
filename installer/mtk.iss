; installer/mtk.iss
[Setup]
AppName=MTK Noise Canceller
AppVersion=1.2.0
AppPublisher=Mobiltracker
AppPublisherURL=https://github.com/edinhograno/mtk-supression
AppId={{C0716AEC-1E9B-4B08-A5B4-6FED63016C76}
DefaultDirName={autopf}\MTK Noise Canceller
DefaultGroupName=MTK Noise Canceller
OutputDir=Output
OutputBaseFilename=mtk-noise-canceller-setup
PrivilegesRequired=admin
Compression=lzma2
SolidCompression=yes
UninstallDisplayName=MTK Noise Canceller
DisableProgramGroupPage=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
Source: "..\dist\mtk-noise-canceller.exe"; DestDir: "{app}"; Flags: ignoreversion

[Run]
Filename: "{app}\mtk-noise-canceller.exe"; \
  Flags: postinstall nowait skipifsilent; \
  Description: "Iniciar MTK Noise Canceller"

[Icons]
Name: "{group}\MTK Noise Canceller"; Filename: "{app}\mtk-noise-canceller.exe"
Name: "{group}\Desinstalar MTK Noise Canceller"; Filename: "{uninstallexe}"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "MTKNoiseCanceller"; Flags: uninsdeletevalue
