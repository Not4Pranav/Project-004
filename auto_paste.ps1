# Auto-paste the clipboard into Windows Notepad.
#   .\auto_paste.ps1
#   .\auto_paste.ps1 -Watch
#   .\auto_paste.ps1 -Live
#   .\auto_paste.ps1 -Append

param(
    [switch]$Watch,
    [switch]$Live,
    [switch]$Append,
    [double]$Interval = 0.6
)

$ErrorActionPreference = "Stop"
$path = Join-Path $env:TEMP "auto-paste-notepad.txt"

function Get-ClipText {
    try {
        $text = Get-Clipboard -Raw -ErrorAction Stop
    } catch {
        return ""
    }
    if ($null -eq $text) { return "" }
    return [string]$text
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
