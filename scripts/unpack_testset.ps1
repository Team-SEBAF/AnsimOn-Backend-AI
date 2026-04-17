# testset-cases.tar.part-* 분할본을 이어 붙여 testset\ 아래에 풀기 (Windows / PowerShell 5.1+)
# 필요: Windows 10+ 내장 tar.exe
# 실행 예(저장소 루트에서):  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\unpack_testset.ps1

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $Root

$parts = @(Get-ChildItem -LiteralPath $Root -Filter 'testset-cases.tar.part-*' -File | Sort-Object Name)
if ($parts.Count -eq 0) {
    Write-Error 'testset-cases.tar.part-* 파일이 없습니다. 저장소에 분할 아카이브가 있는지 확인하세요.'
    exit 1
}

Write-Host '📂 testset-cases.tar.part-* → testset\'

$merged = Join-Path ([System.IO.Path]::GetTempPath()) ('testset-cases-merged-' + [Guid]::NewGuid().ToString() + '.tar')
try {
    $out = [System.IO.File]::Create($merged)
    try {
        foreach ($f in $parts) {
            $in = [System.IO.File]::OpenRead($f.FullName)
            try {
                $null = $in.CopyTo($out)
            }
            finally {
                $in.Dispose()
            }
        }
    }
    finally {
        $out.Dispose()
    }

    $dest = Join-Path $Root 'testset'
    if (-not (Test-Path -LiteralPath $dest)) {
        New-Item -ItemType Directory -Path $dest | Out-Null
    }

    $tar = Get-Command tar -ErrorAction SilentlyContinue
    if (-not $tar) {
        Write-Error 'tar.exe 를 찾을 수 없습니다. Windows 10 이상에서 사용하세요.'
        exit 1
    }

    & tar xf $merged -C $dest
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    if (Test-Path -LiteralPath $merged) {
        Remove-Item -LiteralPath $merged -Force -ErrorAction SilentlyContinue
    }
}

Write-Host '✅ 완료'
