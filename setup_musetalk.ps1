$VendorDir = "vendor\MuseTalk"

if (-Not (Test-Path $VendorDir)) {
    Write-Host ">>> Cloning MuseTalk..." -ForegroundColor Cyan
    git clone https://github.com/Tencent/MuseTalk.git $VendorDir
} else {
    Write-Host ">>> MuseTalk directory already exists." -ForegroundColor Green
}

Write-Host ">>> Check models in: vendor\MuseTalk\models" -ForegroundColor Yellow