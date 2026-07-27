@echo off
chcp 65001 >nul
title Podcast Suite - Motor
cd /d "%~dp0engine"

where python >nul 2>nul
if errorlevel 1 (
  echo [XATO] Python topilmadi.
  echo.
  echo   1. https://www.python.org/downloads/ dan Python o'rnating
  echo   2. O'rnatishda "Add python.exe to PATH" katagini BELGILANG
  echo   3. Shu faylni qayta ishga tushiring
  echo.
  pause
  exit /b 1
)

python -c "import numpy" >nul 2>nul
if errorlevel 1 (
  echo numpy o'rnatilmoqda - bir martalik, ozgina kuting...
  python -m pip install numpy
)

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo.
  echo [OGOHLANTIRISH] ffmpeg topilmadi - sinxronlash hali ishlamaydi.
  echo   1. https://www.gyan.dev/ffmpeg/builds/ dan "release essentials" ni yuklab oling
  echo   2. Ochib, ichidagi bin papkasini PATH ga qo'shing
  echo   3. Shu faylni qayta ishga tushiring
  echo.
)

echo.
python server.py
pause
