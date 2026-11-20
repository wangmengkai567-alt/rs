$ErrorActionPreference = 'Stop'
$filename = (Get-Item -LiteralPath '课程提交/Gowalla签到数据管理系统_实施报告.docx').FullName
$out = Join-Path (Get-Location) 'output/course-build/doc-render'
[void][IO.Directory]::CreateDirectory($out)
$pdf = Join-Path $out 'report.pdf'
$wps = New-Object -ComObject KWPS.Application
$none = [Type]::Missing
$doc = $wps.Documents.Open($filename, $false, $true, $false, $none, $none, $none, $none, $none, $none, $none, $false)
try {
    $doc.ExportAsFixedFormat($pdf, 17)
} finally {
    $doc.Close(0)
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc)
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($wps)
}
if (-not (Test-Path -LiteralPath $pdf -PathType Leaf)) { throw 'WPS did not export the DOCX to PDF' }
$poppler = 'C:/Users/Dell/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin'
& "$poppler/pdfinfo.exe" $pdf
& "$poppler/pdftoppm.exe" -r 122 -png $pdf (Join-Path $out 'page')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
