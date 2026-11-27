@echo off
rem BAT DAU: bam dup mot lan la xong. Tu kiem Python (chua co thi hoi roi cai bang winget cua Windows), tu cai thu vien,
rem tao cau-hinh.json, tao loi tat "Harry Gold Research" ngoai man hinh, roi mo webapp. Chay lai bao nhieu lan cung duoc.
rem Webapp chi doc MetaTrader 5 (khong dat lenh) va chi nghe tren may nay (127.0.0.1). Dong cua so nay la tat webapp.
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title Harry Gold Research (dong cua so nay la tat webapp)

netstat -ano | findstr /R /C:"127\.0\.0\.1:8769 .*LISTENING" >nul && (
  start "" http://127.0.0.1:8769
  exit /b 0
)

rem ---- 1. Tim Python 3.11 tro len
set "PY="
call :thu_py python
if not defined PY call :thu_py py -3
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" call :thu_py "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY (
  echo.
  echo  Chua co Python 3.11 tro len tren may nay.
  where winget >nul 2>nul
  if errorlevel 1 (
    echo  Hay cai Python tu https://www.python.org/downloads/windows/ ^(tick "Add python.exe to PATH"^), roi bam dup lai tep nay.
    echo.
    pause
    exit /b 1
  )
  choice /C CK /M " Cai Python 3.12 tu nguon chinh thuc bang winget cua Windows? C = Co, K = Khong"
  if errorlevel 2 exit /b 1
  winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
  call :thu_py "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  if not defined PY call :thu_py py -3
  if not defined PY (
    echo.
    echo  Cai Python chua xong. Dong cua so nay, mo lai roi bam dup BAT_DAU.bat lan nua.
    echo.
    pause
    exit /b 1
  )
)

rem ---- 2. Thu vien
%PY% -X utf8 -c "import pandas, numpy, MetaTrader5, defusedxml" >nul 2>nul
if errorlevel 1 (
  echo.
  echo  Dang cai thu vien lan dau ^(pandas, numpy, MetaTrader5, defusedxml^)... mat vai phut.
  %PY% -m pip install --disable-pip-version-check --quiet -r requirements.txt
  if errorlevel 1 (
    echo.
    echo  Cai thu vien KHONG thanh cong. Kiem tra ket noi mang roi bam dup lai tep nay.
    echo.
    pause
    exit /b 1
  )
)

rem ---- 3. Cau hinh va loi tat ngoai man hinh (chi tao mot lan)
if not exist cau-hinh.json copy /y cau-hinh.mau.json cau-hinh.json >nul
if not exist "%USERPROFILE%\Desktop\Harry Gold Research.lnk" (
  powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Harry Gold Research.lnk');$s.TargetPath='%~dp0BAT_DAU.bat';$s.WorkingDirectory='%~dp0';$s.IconLocation='%~dp0tinh\logo.ico';$s.Description='Harry Gold Research - bang dieu khien giao dich (chi doc MT5)';$s.Save()" >nul 2>nul
)

rem ---- 4. Mo webapp
echo.
echo  Mo MetaTrader 5 va dang nhap tai khoan DEMO neu chua mo. Trang se tu mo trong trinh duyet.
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "for($i=0;$i -lt 120;$i++){try{(New-Object Net.Sockets.TcpClient('127.0.0.1',8769)).Close();break}catch{Start-Sleep -Milliseconds 500}}; Start-Process 'http://127.0.0.1:8769'"
%PY% -X utf8 -m so_cong_khai.launch_local
pause
exit /b 0

:thu_py
%* -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 set "PY=%*"
exit /b 0
