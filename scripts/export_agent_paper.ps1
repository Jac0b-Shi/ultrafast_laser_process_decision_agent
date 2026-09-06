param([switch]$SkipFigures)
$ErrorActionPreference='Stop'
$repoRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $repoRoot
try {
    if (-not $SkipFigures) {
        docker compose run --rm --no-deps -v "${repoRoot}:/workspace" -e PYTHONPATH=/workspace/apps/api api python /workspace/scripts/build_agent_paper.py
        if ($LASTEXITCODE) { throw 'Manuscript generation failed' }
    }
    $title='AI-Bridged Data-Knowledge Fusion for Intelligent Laser Parameter Recommendation in Ultrafast Laser Processing'
    $paperRoot=Join-Path $repoRoot 'docs/research/english'
    $docxPath=Join-Path $paperRoot "$title.docx"
    $pdfPath=Join-Path $paperRoot "$title.pdf"
    pandoc (Join-Path $paperRoot "$title.md") --from markdown --standalone --shift-heading-level-by=-1 "--resource-path=$paperRoot" -o $docxPath
    if ($LASTEXITCODE) { throw 'Pandoc conversion failed' }
    docker compose run --rm --no-deps -v "${repoRoot}:/workspace" api python /workspace/scripts/format_agent_docx.py
    if ($LASTEXITCODE) { throw 'DOCX formatting failed' }
    docker compose run --rm --no-deps -v "${repoRoot}:/workspace" api python /workspace/scripts/build_journal_figures.py
    if ($LASTEXITCODE) { throw 'Journal figures failed' }
    docker compose --profile paper run --build --rm paper
    if ($LASTEXITCODE) { throw 'Journal PDF export failed' }
    $pageRoot=Join-Path $paperRoot 'build/final-pages'
    New-Item -ItemType Directory -Force -Path $pageRoot | Out-Null
    pdftoppm -scale-to 1400 -png $pdfPath (Join-Path $pageRoot 'page')
    if ($LASTEXITCODE) { throw 'PDF rendering failed' }
    Write-Output $pdfPath
} finally { Pop-Location }
