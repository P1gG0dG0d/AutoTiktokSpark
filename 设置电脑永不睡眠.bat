@echo off
title 设置电脑永不睡眠
echo ============================================
echo   设置电脑永不睡眠（屏幕仍可自动关闭）
echo   会弹出"是否允许"窗口，请点"是"
echo   只需要运行这一次！
echo ============================================
echo.
powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList '/c powercfg /change standby-timeout-ac 0 & powercfg /change standby-timeout-dc 0 & powercfg /change hibernate-timeout-ac 0 & echo 设置完成！& timeout /t 3'"
if %errorlevel% equ 0 (
    echo 已提交设置：电脑永不睡眠/永不休眠
) else (
    echo 你点了"否"，没有设置成功，可以稍后再运行一次。
)
echo.
pause
