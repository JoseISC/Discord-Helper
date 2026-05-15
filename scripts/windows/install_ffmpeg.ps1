Write-Host "Discord Helper — FFmpeg Bootstrap" -ForegroundColor Cyan

$target = "$HOME\\.local\\bin\\discord-helper\\ffmpeg"
$tempZip = "$env:TEMP\\ffmpeg-release.zip"

New-Item -ItemType Directory -Force -Path $target | Out-Null

$url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

Write-Host "Downloading FFmpeg..."
Invoke-WebRequest -Uri $url -OutFile $tempZip

Write-Host "Extracting FFmpeg..."
Expand-Archive -Force $tempZip $target

Write-Host "FFmpeg installed in: $target" -ForegroundColor Green
Write-Host "Add the ffmpeg /bin folder to your PATH if needed." -ForegroundColor Yellow
