# download_face_models.ps1
#
# Run this once from your project root in PowerShell to pull the
# face-api.js model weights into static\models\
#
# Usage (from project root):
#   .\download_face_models.ps1
#
# If you get a "scripts disabled" error run this first (once):
#   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

$dest = "static\models"
$base = "https://raw.githubusercontent.com/justadudewhohacks/face-api.js/master/weights"

$files = @(
    "tiny_face_detector_model-shard1",
    "tiny_face_detector_model-weights_manifest.json",
    "face_landmark_68_tiny_model-shard1",
    "face_landmark_68_tiny_model-weights_manifest.json",
    "face_recognition_model-shard1",
    "face_recognition_model-shard2",
    "face_recognition_model-weights_manifest.json"
)

# Create destination directory if it doesn't exist
if (-not (Test-Path $dest)) {
    New-Item -ItemType Directory -Path $dest | Out-Null
    Write-Host "Created directory: $dest" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Downloading face-api.js model weights to $dest ..." -ForegroundColor Cyan
Write-Host ""

foreach ($file in $files) {
    $url     = "$base/$file"
    $outPath = "$dest\$file"
    Write-Host "  -> $file" -ForegroundColor Gray
    try {
        Invoke-WebRequest -Uri $url -OutFile $outPath -UseBasicParsing
    } catch {
        Write-Host "     FAILED: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Done. Model files saved to $dest\" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  python manage.py migrate" -ForegroundColor White
Write-Host "  python manage.py collectstatic" -ForegroundColor White
