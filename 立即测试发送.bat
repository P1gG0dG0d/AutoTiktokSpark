@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d D:\Projects\AutoTiktokSpark
echo ============================================
echo   抖音续火花 - 立即测试发送（不等随机时间）
echo ============================================
".venv\Scripts\python.exe" huohua.py --now
echo.
echo 已结束，结果见上方提示 / screenshots 文件夹 / logs 文件夹。
pause
