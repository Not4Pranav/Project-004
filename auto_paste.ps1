# Auto-paste the clipboard into Windows Notepad.
#   .\auto_paste.ps1
#   .\auto_paste.ps1 -Watch
#   .\auto_paste.ps1 -Live
#   .\auto_paste.ps1 -Append
#   .\auto_paste.ps1 -List
#   .\auto_paste.ps1 -Next
#   .\auto_paste.ps1 -SaveClip
#   .\auto_paste.ps1 -Collect
#   .\auto_paste.ps1 -Doctor

param(
    [switch]$Watch,
    [switch]$Live,
    [switch]$Append,
    [switch]$List,
    [switch]$Next,
    [switch]$SaveClip,
    [switch]$Collect,
    [switch]$Doctor,
    [double]$Interval = 0.6,
    [string]$ListFile = ""
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ListFile) { $ListFile = Join-Path $here "links.txt" }
$path = Join-Path $env:TEMP "auto-paste-notepad.txt"
$cursorPath = Join-Path (Split-Path -Parent $ListFile) ".auto-paste-cursor"

function Get-ClipText {
    try {
        $text = Get-Clipboard -Raw -ErrorAction Stop
    } catch {
        return ""
    }
    if ($null -eq $text) { return "" }
    return [string]$text
}

function Get-ListItems([string]$File) {
    if (-not (Test-Path $File)) { return @() }
    $items = @()
    foreach ($line in Get-Content -Path $File -Encoding UTF8) {
        $trim = $line.Trim()
        if (-not $trim) { continue }
        if ($trim.StartsWith("#")) { continue }
        $items += $trim
    }
    return $items
}

function Add-ListItem([string]$File, [string]$Text) {
    $item = $Text.TrimEnd("`r", "`n")
    if ([string]::IsNullOrWhiteSpace($item)) { return $false }
    $existing = Get-ListItems $File
    if ($existing -contains $item) { return $false }
    $prefix = ""
    if (Test-Path $File) {
        $bytes = [System.IO.File]::ReadAllBytes($File)
        if ($bytes.Length -gt 0 -and $bytes[$bytes.Length - 1] -ne 10) { $prefix = "`r`n" }
    }
    Add-Content -Path $File -Value ($prefix + $item) -Encoding UTF8
    return $true
}

function Open-NotepadWithText([string]$Text) {
    if ($Append -and (Test-Path $path)) {
        $existing = [System.IO.File]::ReadAllText($path)
        if ($existing -and -not $existing.EndsWith("`n")) {
            $existing += "`r`n"
        }
        $Text = $existing + $Text
    }
    [System.IO.File]::WriteAllText($path, $Text)
    Start-Process notepad.exe -ArgumentList $path
}

function Paste-Live([string]$Text) {
    Add-Type -AssemblyName System.Windows.Forms
    Add-Type -AssemblyName Microsoft.VisualBasic
    $proc = Get-Process notepad -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $proc) {
        Start-Process notepad.exe
        Start-Sleep -Milliseconds 500
    } else {
        [Microsoft.VisualBasic.Interaction]::AppActivate($proc.Id)
        Start-Sleep -Milliseconds 150
    }
    if (-not $Append) {
        [System.Windows.Forms.SendKeys]::SendWait("^a")
    }
    Set-Clipboard -Value $Text
    [System.Windows.Forms.SendKeys]::SendWait("^v")
}

function Apply([string]$Text) {
    if ([string]::IsNullOrEmpty($Text)) {
        Write-Host "Clipboard is empty."
        return
    }
    if ($Live) { Paste-Live $Text } else { Open-NotepadWithText $Text }
    Write-Host "Pasted $($Text.Length) characters into Notepad."
}

if ($Doctor) {
    Write-Host "Auto-paste doctor"
    Write-Host "  PowerShell  $($PSVersionTable.PSVersion)"
    Write-Host "  List file   $ListFile"
    $items = Get-ListItems $ListFile
    Write-Host "  List        $($items.Count) item(s)"
    $clip = Get-ClipText
    Write-Host "  Clipboard   $($clip.Length) chars"
    Write-Host "  Editor      notepad.exe"
    Write-Host ""
    Write-Host "Ready. Run 3-Start.bat (or .\\auto_paste.ps1 -Watch)."
    exit 0
}

if ($SaveClip) {
    if (Add-ListItem $ListFile (Get-ClipText)) {
        Write-Host "Saved to $ListFile"
        exit 0
    }
    Write-Host "Nothing new to save (empty or already in the list)."
    exit 1
}

if ($List) {
    $items = Get-ListItems $ListFile
    if ($items.Count -eq 0) {
        Write-Host "No items in $ListFile. Edit it with 2-Edit-list.bat."
        exit 1
    }
    Apply (($items -join "`r`n"))
    exit 0
}

if ($Next) {
    $items = Get-ListItems $ListFile
    if ($items.Count -eq 0) {
        Write-Host "No items in $ListFile. Edit it with 2-Edit-list.bat."
        exit 1
    }
    $idx = 0
    if (Test-Path $cursorPath) {
        try { $idx = [int](Get-Content $cursorPath -Raw) } catch { $idx = 0 }
    }
    $idx = $idx % $items.Count
    Apply $items[$idx]
    $nxt = ($idx + 1) % $items.Count
    Set-Content -Path $cursorPath -Value "$nxt" -Encoding ASCII
    exit 0
}

if ($Collect) {
    Write-Host "Collecting copies into $ListFile. Ctrl+C to stop."
    $last = Get-ClipText
    if (Add-ListItem $ListFile $last) { Write-Host "+ $($last.Split("`n")[0])" }
    while ($true) {
        Start-Sleep -Seconds $Interval
        $current = Get-ClipText
        if ($current -and $current -ne $last) {
            $last = $current
            if (Add-ListItem $ListFile $current) {
                Write-Host "+ $($current.Split("`n")[0])"
            }
        }
    }
}

$last = Get-ClipText
Apply $last

if (-not $Watch) { exit 0 }

Write-Host "Watching clipboard — copy something else to auto-paste. Ctrl+C to stop."
while ($true) {
    Start-Sleep -Seconds $Interval
    $current = Get-ClipText
    if ($current -and $current -ne $last) {
        $last = $current
        Apply $current
    }
}
