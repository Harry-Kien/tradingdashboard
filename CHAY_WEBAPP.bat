@echo off
rem Mo webapp: chay may chu tren may nay (127.0.0.1:8769) roi mo trinh duyet khi may chu da san sang.
rem Neu webapp da chay san thi chi mo trinh duyet. Dong cua so nay la tat webapp.
chcp 65001 >nul
cd /d "%~dp0"
title Webapp (dong cua so nay la tat webapp)

netstat -ano | findstr /R /C:"127\.0\.0\.1:8769 .*LISTENING" >nul && (
  start "" http://127.0.0.1:8769
  exit /b 0
)

python -X utf8 -c "import pandas, numpy, MetaTrader5" >nul 2>nul
if errorlevel 1 (
  echo.
  echo  Chua cai du thu vien. Hay bam dup CAI_DAT.bat truoc, roi chay lai tep nay.
  echo.
  pause
  exit /b 1
)

start "" /min powershell -NoProfile -WindowStyle Hidden -Command "for($i=0;$i -lt 120;$i++){try{(New-Object Net.Sockets.TcpClient('127.0.0.1',8769)).Close();break}catch{Start-Sleep -Milliseconds 500}}; Start-Process 'http://127.0.0.1:8769'"
python -X utf8 -m so_cong_khai.launch_local
pause
