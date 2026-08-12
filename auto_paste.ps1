# Auto-paste unique lines into the focused Windows app.
#   .\auto_paste.ps1 -Send          # copy → Ctrl+V → Enter, red STOP
#   .\auto_paste.ps1 -Watch
#   .\auto_paste.ps1 -Live
#   .\auto_paste.ps1 -List
#   .\auto_paste.ps1 -Doctor

param(
    [switch]$Send,
    [switch]$Watch,
    [switch]$Live,
    [switch]$Append,
    [switch]$List,
    [switch]$Next,
    [switch]$SaveClip,
    [switch]$Collect,
    [switch]$Doctor,
    [switch]$ResetUsed,
    [switch]$DryRun,
    [double]$Interval = 0.6,
    [double]$Countdown = 3,
    [int]$RateCount = 4,
    [double]$RateWindow = 5,
    [string]$ListFile = ""
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ListFile) { $ListFile = Join-Path $here "links.txt" }
$path = Join-Path $env:TEMP "auto-paste-notepad.txt"
$cursorPath = Join-Path (Split-Path -Parent $ListFile) ".auto-paste-cursor"
$usedPath = Join-Path (Split-Path -Parent $ListFile) ".auto-paste-used"

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

function Get-UsedItems {
    if (-not (Test-Path $usedPath)) { return @() }
    return Get-ListItems $usedPath
}

function Add-UsedItem([string]$Text) {
    Add-Content -Path $usedPath -Value $Text -Encoding UTF8
}

function Get-UniqueUnused([object[]]$Items) {
    $used = @{}
    foreach ($u in (Get-UsedItems)) { $used[$u] = $true }
    $seen = @{}
    $out = @()
    foreach ($item in $Items) {
        if ($seen.ContainsKey($item)) { continue }
        $seen[$item] = $true
        if ($used.ContainsKey($item)) { continue }
        $out += $item
    }
    return $out
}

function Send-PasteEnter {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.SendKeys]::SendWait("^v")
    Start-Sleep -Milliseconds 40
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
}

function Start-SendSession {
    Add-Type -AssemblyName System.Windows.Forms
    if ($ResetUsed -and (Test-Path $usedPath)) { Remove-Item $usedPath -Force }

    $script:stopFlag = $false
    $form = New-Object System.Windows.Forms.Form
    $form.Text = "Auto-paste — STOP"
    $form.Size = New-Object System.Drawing.Size(460, 260)
    $form.StartPosition = "CenterScreen"
    $form.TopMost = $true
    $form.BackColor = [System.Drawing.Color]::FromArgb(28, 29, 33)
    $form.FormBorderStyle = "FixedDialog"
    $form.MaximizeBox = $false

    $title = New-Object System.Windows.Forms.Label
    $title.Text = "AUTO-PASTE"
    $title.ForeColor = [System.Drawing.Color]::White
    $title.Font = New-Object System.Drawing.Font("Segoe UI", 14, [System.Drawing.FontStyle]::Bold)
    $title.Location = New-Object System.Drawing.Point(16, 12)
    $title.AutoSize = $true
    $form.Controls.Add($title)

    $hint = New-Object System.Windows.Forms.Label
    $hint.Text = "$RateCount unique strings every ${RateWindow}s  ·  copy → paste → Enter"
    $hint.ForeColor = [System.Drawing.Color]::Silver
    $hint.Location = New-Object System.Drawing.Point(16, 42)
    $hint.AutoSize = $true
    $form.Controls.Add($hint)

    $status = New-Object System.Windows.Forms.Label
    $status.Text = "Click START, then click the text box (Chrome, Discord, Word…)."
    $status.ForeColor = [System.Drawing.Color]::Khaki
    $status.Location = New-Object System.Drawing.Point(16, 70)
    $status.Size = New-Object System.Drawing.Size(420, 40)
    $form.Controls.Add($status)

    $startBtn = New-Object System.Windows.Forms.Button
    $startBtn.Text = "START"
    $startBtn.BackColor = [System.Drawing.Color]::FromArgb(43, 93, 255)
    $startBtn.ForeColor = [System.Drawing.Color]::White
    $startBtn.FlatStyle = "Flat"
    $startBtn.Location = New-Object System.Drawing.Point(16, 130)
    $startBtn.Size = New-Object System.Drawing.Size(100, 56)
    $form.Controls.Add($startBtn)

    $stopBtn = New-Object System.Windows.Forms.Button
    $stopBtn.Text = "STOP"
    $stopBtn.BackColor = [System.Drawing.Color]::FromArgb(208, 18, 45)
    $stopBtn.ForeColor = [System.Drawing.Color]::White
    $stopBtn.FlatStyle = "Flat"
    $stopBtn.Font = New-Object System.Drawing.Font("Segoe UI", 16, [System.Drawing.FontStyle]::Bold)
    $stopBtn.Location = New-Object System.Drawing.Point(126, 130)
    $stopBtn.Size = New-Object System.Drawing.Size(200, 56)
    $form.Controls.Add($stopBtn)

    $stopBtn.Add_Click({ $script:stopFlag = $true; $status.Text = "STOP" })
    $form.Add_FormClosing({ $script:stopFlag = $true })

    $startBtn.Add_Click({
        $startBtn.Enabled = $false
        $items = Get-UniqueUnused (Get-ListItems $ListFile)
        if ($items.Count -eq 0) {
            $status.Text = "Nothing left to send. Edit the list or delete .auto-paste-used."
            $startBtn.Enabled = $true
            return
        }
        $interval = $RateWindow / [Math]::Max(1, $RateCount)
        $script:stopFlag = $false
        for ($t = [int]$Countdown; $t -gt 0; $t--) {
            if ($script:stopFlag) { $status.Text = "STOP"; return }
            $status.Text = "Click the text box now — sending in $t…"
            [System.Windows.Forms.Application]::DoEvents()
            Start-Sleep -Seconds 1
        }
        $n = 0
        foreach ($item in $items) {
            if ($script:stopFlag) { $status.Text = "STOP — sent $n"; return }
            $n++
            $status.Text = "Sending $n / $($items.Count): $item"
            [System.Windows.Forms.Application]::DoEvents()
            Set-Clipboard -Value $item
            if (-not $DryRun) { Send-PasteEnter }
            Add-UsedItem $item
            if ($n -lt $items.Count) {
                $waited = 0.0
                while ($waited -lt $interval) {
                    if ($script:stopFlag) { $status.Text = "STOP — sent $n"; return }
                    Start-Sleep -Milliseconds 100
                    $waited += 0.1
                    [System.Windows.Forms.Application]::DoEvents()
                }
            }
        }
        $status.Text = "Done. Sent $n unique line(s)."
    })

    [void]$form.ShowDialog()
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
