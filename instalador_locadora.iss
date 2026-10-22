; Script para Inno Setup 6. Compilar após gerar dist\LocadoraAgente.exe.
#define MyAppName "Agente de Inventário da Locadora"
#define MyAppVersion "2.0.0"
[Setup]
AppId={{2E3C7B15-63A1-47BC-98C1-7A3B7A31B2B0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\Locadora\Agente
DefaultGroupName=Locadora
OutputDir=installer
OutputBaseFilename=Instalador_Locadora_Agente
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayName={#MyAppName}
[Files]
Source: "dist\LocadoraAgente.exe"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{group}\Agente de Inventário da Locadora"; Filename: "{app}\LocadoraAgente.exe"
Name: "{autodesktop}\Agente de Inventário da Locadora"; Filename: "{app}\LocadoraAgente.exe"
[Run]
Filename: "{app}\LocadoraAgente.exe"; Description: "Configurar e iniciar o agente"; Flags: postinstall nowait
