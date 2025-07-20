Write-Host "앱을 시작하고 엣지 브라우저로 열기..." -ForegroundColor Green

# 백그라운드에서 Python 앱 시작
Start-Process python -ArgumentList "main.py" -WindowStyle Hidden

# 3초 대기
Start-Sleep -Seconds 3

# 엣지 브라우저로 열기
Start-Process "msedge" -ArgumentList "http://localhost:8000"

Write-Host "완료! 엣지 브라우저가 열렸습니다." -ForegroundColor Green 