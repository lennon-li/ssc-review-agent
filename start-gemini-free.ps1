Write-Host "Switching to Gemini free sign-in mode..." -ForegroundColor Cyan

Remove-Item Env:GOOGLE_CLOUD_PROJECT -ErrorAction SilentlyContinue
Remove-Item Env:GOOGLE_CLOUD_LOCATION -ErrorAction SilentlyContinue
Remove-Item Env:GOOGLE_GENAI_USE_VERTEXAI -ErrorAction SilentlyContinue
Remove-Item Env:GOOGLE_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue

gemini
