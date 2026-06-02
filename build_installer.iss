[Setup]
AppName=EditForge
AppVersion=4.0.0
DefaultDirName={pf}\EditForge
DefaultGroupName=EditForge
OutputDir=installer
OutputBaseFilename=EditForge_v4_Installer
Compression=lzma
SolidCompression=yes
SetupIconFile=app.ico

[Files]
Source: "dist\EditForge.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"
Source: "creative_patterns.json"; DestDir: "{app}"

[Icons]
Name: "{group}\EditForge"; Filename: "{app}\EditForge.exe"
Name: "{commondesktop}\EditForge"; Filename: "{app}\EditForge.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    MsgBox('EditForge installed successfully. Run EditForge.exe to start.', mbInformation, MB_OK);
end;