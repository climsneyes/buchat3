@echo off
echo 앱을 시작하고 엣지 브라우저로 열기...
start /B python main.py
timeout /t 3 /nobreak >nul
start msedge http://localhost:8000
echo 완료!
pause 