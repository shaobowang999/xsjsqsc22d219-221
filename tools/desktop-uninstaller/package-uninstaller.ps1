param([Parameter(Mandatory=$true)][string]$AppDirectory)
$ErrorActionPreference = 'Stop'
$app = (Resolve-Path -LiteralPath $AppDirectory).Path
if (!(Test-Path -LiteralPath (Join-Path $app '三千思创无线画布.exe')) -or
    !(Test-Path -LiteralPath (Join-Path $app '_internal'))) {
    throw 'AppDirectory must contain the packaged application and _internal.'
}
$compiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (!(Test-Path -LiteralPath $compiler)) { throw 'Microsoft .NET Framework 4 compiler is required.' }
& $compiler /nologo /target:winexe /reference:System.Windows.Forms.dll /reference:System.Core.dll "/out:$app\uninstall.exe" "$PSScriptRoot\uninstall.cs"
if ($LASTEXITCODE -ne 0) { throw 'Failed to compile uninstall.exe.' }
$utf8 = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText((Join-Path $app '卸载说明.txt'), @'
双击 uninstall.exe，确认后卸载。运行前请先关闭画布。
仅删除程序发行清单中列出的文件；保留用户数据、API密钥和其他个人文件。
解压包属于便携版，不会安装系统服务或注册表项目。
请保留 uninstall-files.txt，否则无法执行卸载。
'@, $utf8)
$files = @('三千思创无线画布.exe', 'uninstall.exe', 'uninstall-files.txt', '卸载说明.txt')
$files += Get-ChildItem -LiteralPath (Join-Path $app '_internal') -Recurse -File | ForEach-Object { $_.FullName.Substring($app.Length + 1) }
[IO.File]::WriteAllLines((Join-Path $app 'uninstall-files.txt'), [string[]]$files, $utf8)
$check = Start-Process -FilePath (Join-Path $app 'uninstall.exe') -ArgumentList '--verify' -Wait -PassThru
if ($check.ExitCode -ne 0) { throw 'Uninstaller manifest verification failed.' }
