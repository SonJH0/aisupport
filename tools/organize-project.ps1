param([string]$ProjectPath = (Split-Path -Parent $PSScriptRoot), [switch]$Preview, [switch]$Undo)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($ProjectPath).TrimEnd([IO.Path]::DirectorySeparatorChar)
$assets = Join-Path $PSScriptRoot 'cleanup-assets'
$manifest = Get-Content -LiteralPath (Join-Path $assets 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$stateFile = Join-Path $root 'tools/cleanup-state.json'
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Local-Path([string]$Relative) {
    $path = [IO.Path]::GetFullPath((Join-Path $root $Relative))
    if (-not $path.StartsWith($root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Path escapes project root.' }
    return $path
}
function Make-Parent([string]$Path) { [IO.Directory]::CreateDirectory((Split-Path -Parent $Path)) | Out-Null }
function Save-State($State) { [IO.File]::WriteAllText($stateFile, ($State | ConvertTo-Json -Depth 10), $utf8) }
function Restore-Operations($Operations) {
    $items = @($Operations)
    [array]::Reverse($items)
    foreach ($op in $items) {
        $target = Local-Path $op.target
        if ($op.type -eq 'move') {
            $source = Local-Path $op.source
            if (Test-Path -LiteralPath $source) { throw ('Cannot restore over existing file: ' + $op.source) }
            Make-Parent $source
            Move-Item -LiteralPath $target -Destination $source
        } elseif ($op.backup) {
            [IO.File]::Copy((Local-Path $op.backup), $target, $true)
        } elseif (Test-Path -LiteralPath $target) {
            Remove-Item -LiteralPath $target
        }
    }
}

if (-not (Test-Path -LiteralPath (Join-Path $root '.git'))) { throw 'Open the actual ai-job-assistant-git repository.' }
if ($Undo) {
    if (-not (Test-Path -LiteralPath $stateFile)) { throw 'No cleanup state was found.' }
    $state = Get-Content -LiteralPath $stateFile -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($op in $state.operations) {
        $target = Local-Path $op.target
        if (-not (Test-Path -LiteralPath $target)) { throw ('Missing file: ' + $op.target) }
        if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -ne $op.hash) { throw ('File edited after cleanup; refusing to overwrite: ' + $op.target) }
        if ($op.type -eq 'move' -and (Test-Path -LiteralPath (Local-Path $op.source))) { throw ('Original path already exists: ' + $op.source) }
        if ($op.backup -and -not (Test-Path -LiteralPath (Local-Path $op.backup))) { throw ('Backup missing: ' + $op.backup) }
    }
    if ($Preview) { Write-Host 'Undo preflight passed. No files changed.'; exit 0 }
    Restore-Operations $state.operations
    Remove-Item -LiteralPath $stateFile
    Write-Host 'Restored original paths and documents. Backups remain in docs/archive/pre-cleanup.'
    exit 0
}

if (Test-Path -LiteralPath $stateFile) { throw 'Cleanup already applied. Use -Undo to restore.' }
$head = (& git -C $root rev-parse HEAD | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $head -ne $manifest.base_commit) { throw ('Repository revision differs from reviewed version ' + $manifest.base_commit + '. Stop and review before applying.') }
& git -C $root diff --quiet
if ($LASTEXITCODE -ne 0) { throw 'Tracked files have local changes. Commit or preserve your changes first.' }
& git -C $root diff --cached --quiet
if ($LASTEXITCODE -ne 0) { throw 'Staged changes exist. Finish that work first.' }

foreach ($move in $manifest.moves) {
    if (-not (Test-Path -LiteralPath (Local-Path $move.source))) { throw ('Source missing: ' + $move.source) }
    if (Test-Path -LiteralPath (Local-Path $move.target)) { throw ('Destination already exists: ' + $move.target) }
}
foreach ($write in $manifest.writes) {
    if (-not (Test-Path -LiteralPath (Join-Path $assets $write.asset))) { throw ('Payload missing: ' + $write.asset) }
    $exists = Test-Path -LiteralPath (Local-Path $write.target)
    if ($write.backup -and -not $exists) { throw ('Document missing: ' + $write.target) }
    if (-not $write.backup -and $exists) { throw ('New document already exists: ' + $write.target) }
    if ($write.backup -and (Test-Path -LiteralPath (Local-Path $write.backup))) { throw ('Backup already exists: ' + $write.backup) }
}
Write-Host ('Reviewed moves: ' + $manifest.moves.Count + '; document writes: ' + $manifest.writes.Count)
foreach ($move in $manifest.moves) { Write-Host ($move.source + ' -> ' + $move.target) }
if ($Preview) { Write-Host 'Preview only. No project files changed.'; exit 0 }

$state = @{ base_commit = $head; operations = @() }
Make-Parent $stateFile
try {
    foreach ($write in $manifest.writes) {
        if ($write.backup) {
            $backup = Local-Path $write.backup
            Make-Parent $backup
            [IO.File]::Copy((Local-Path $write.target), $backup, $false)
        }
    }
    foreach ($move in $manifest.moves) {
        $source = Local-Path $move.source
        $target = Local-Path $move.target
        Make-Parent $target
        Move-Item -LiteralPath $source -Destination $target
        $state.operations += @{ type = 'move'; source = $move.source; target = $move.target; hash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash }
        Save-State $state
    }
    foreach ($write in $manifest.writes) {
        $target = Local-Path $write.target
        Make-Parent $target
        # Record the operation first so a failed write can be restored too.
        $op = @{ type = 'write'; target = $write.target; backup = $write.backup; hash = '' }
        $state.operations += $op
        Save-State $state
        [IO.File]::Copy((Join-Path $assets $write.asset), $target, $true)
        $op.hash = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
        Save-State $state
    }
    Write-Host 'Cleanup complete. Service code, data, tests and environment were preserved.'
    Write-Host 'Review with: git --no-pager diff --stat'
} catch {
    $failure = $_
    try {
        Restore-Operations $state.operations
        if (Test-Path -LiteralPath $stateFile) { Remove-Item -LiteralPath $stateFile }
    } catch { throw ('Cleanup failed; automatic restore also failed. Keep backups and state file. ' + $_.Exception.Message) }
    throw ('Cleanup stopped and original paths were restored. ' + $failure.Exception.Message)
}
