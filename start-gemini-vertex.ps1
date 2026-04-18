param(
    [string]$ProjectId = "project-9486ad0d-3ebc-4395-a7c",
    [string]$Location = "global"
)

Write-Host "Setting Vertex AI environment..." -ForegroundColor Cyan

# Set env vars for this session
$env:GOOGLE_CLOUD_PROJECT = $ProjectId
$env:GOOGLE_CLOUD_LOCATION = $Location
$env:GOOGLE_GENAI_USE_VERTEXAI = "true"

# Clear conflicting API-key auth if present
Remove-Item Env:GOOGLE_API_KEY -ErrorAction SilentlyContinue
Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue

Write-Host "Checking gcloud project..." -ForegroundColor Cyan
$currentProject = gcloud config get-value project 2>$null

if ($currentProject -ne $ProjectId) {
    Write-Host "Setting gcloud project to $ProjectId" -ForegroundColor Yellow
    gcloud config set project $ProjectId
}

Write-Host "Checking ADC login..." -ForegroundColor Cyan
$adcPath = Join-Path $env:APPDATA "gcloud\application_default_credentials.json"

if (-not (Test-Path $adcPath)) {
    Write-Host "No Application Default Credentials found. Opening login..." -ForegroundColor Yellow
    gcloud auth application-default login
}

Write-Host ""
Write-Host "Vertex AI Gemini environment ready." -ForegroundColor Green
Write-Host "Project:  $env:GOOGLE_CLOUD_PROJECT"
Write-Host "Location: $env:GOOGLE_CLOUD_LOCATION"
Write-Host ""
Write-Host "Starting Gemini CLI..." -ForegroundColor Cyan

gemini
