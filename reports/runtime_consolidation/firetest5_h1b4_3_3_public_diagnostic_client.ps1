$ErrorActionPreference='Continue'
$sw=[System.Diagnostics.Stopwatch]::StartNew()
$payload=Get-Content 'C:\Dev\AIpinho\reports\runtime_consolidation\firetest5_h1b4_3_3_public_diagnostic_request.json' -Raw
$result=[ordered]@{ok=$false; status=$null; ms=$null; bytes=0; body=$null; error=$null; started_at=(Get-Date).ToString('o'); finished_at=$null}
try {
  $resp=Invoke-WebRequest -Method Post -Uri 'http://127.0.0.1:8096/api/v1/chat' -ContentType 'application/json' -Body $payload -TimeoutSec 300
  $sw.Stop(); $result.ok=$true; $result.status=[int]$resp.StatusCode; $result.ms=$sw.ElapsedMilliseconds; $result.bytes=$resp.RawContentLength; $result.body=$resp.Content
} catch {
  $sw.Stop(); $result.ms=$sw.ElapsedMilliseconds; $result.error=$_.Exception.ToString()
}
$result.finished_at=(Get-Date).ToString('o')
$result | ConvertTo-Json -Depth 20 | Set-Content 'C:\Dev\AIpinho\reports\runtime_consolidation\firetest5_h1b4_3_3_public_diagnostic_chat_response.json' -Encoding UTF8
