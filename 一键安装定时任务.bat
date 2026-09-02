@echo off
chcp 65001 >nul
echo ============================================
echo   一键安装定时任务（每晚 20:00 自动续火花）
echo   只需要运行这一次！
echo ============================================
echo.

schtasks /create /tn "AutoTiktokSpark_Huohua" /tr "D:\Projects\AutoTiktokSpark\run_daily.bat" /sc daily /st 20:00 /f

if %errorlevel% equ 0 (
    echo.
    echo ✅ 定时任务安装成功！
    echo    任务名: AutoTiktokSpark_Huohua
    echo    时间:   每天 20:00 自动开始（随机延迟后发送）
) else (
    echo.
    echo ❌ 安装失败，错误码 %errorlevel%
    echo    请截图黑窗口内容，联系助手排查。
)
echo.
echo 已有的同名任务信息：
schtasks /query /tn "AutoTiktokSpark_Huohua"
echo.
pause
