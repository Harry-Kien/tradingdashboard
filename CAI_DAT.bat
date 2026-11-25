@echo off
rem Cai dat lan dau: kiem tra Python, cai cac thu vien can thiet, tao cau-hinh.json tu ban mau.
rem Khong tai hay chay gi khac. Chay lai bao nhieu lan cung duoc.
chcp 65001 >nul
cd /d "%~dp0"
title Cai dat webapp

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo  Chua thay Python tren may nay.
  echo  Hay cai Python 3.11 tro len tu https://www.python.org/downloads/windows/
  echo  va nho tick o "Add python.exe to PATH" khi cai. Xong thi chay lai tep nay.
  echo.
  pause
  exit /b 1
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 (
  echo.
  echo  Python tren may dang qua cu. Can Python 3.11 tro len.
  python --version
  echo.
  pause
  exit /b 1
)

echo.
echo  Dang cai thu vien (pandas, numpy, MetaTrader5, defusedxml)...
python -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo.
  echo  Cai thu vien KHONG thanh cong. Kiem tra ket noi mang roi chay lai tep nay.
  echo.
  pause
  exit /b 1
)

if not exist cau-hinh.json copy /y cau-hinh.mau.json cau-hinh.json >nul

echo.
echo  Cai dat xong.
echo  1. Mo MetaTrader 5 va dang nhap tai khoan DEMO.
echo  2. Bam dup CHAY_WEBAPP.bat de mo webapp.
echo  Doc them HUONG_DAN.md neu can.
echo.
pause
