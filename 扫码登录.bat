@echo off
title 抖音续火花 - 扫码登录
cd /d D:\Projects\AutoTiktokSpark
set PYTHONIOENCODING=utf-8
echo ============================================
echo   抖音续火花 - 扫码登录（一次性操作）
echo   浏览器即将打开，请用手机抖音扫码
echo ============================================
".venv\Scripts\python.exe" huohua.py --login
echo.
echo 已结束，窗口可以关闭。
pause
