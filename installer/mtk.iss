; installer/mtk.iss
[Setup]
AppName=MTK Noise Canceller
AppVersion=1.0.0
AppPublisher=Mobiltracker
AppPublisherURL=https://github.com/edinhograno/mtk-supression
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
