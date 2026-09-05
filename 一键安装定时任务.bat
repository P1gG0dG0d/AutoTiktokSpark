@echo off
title 抖音续火花 - 安装定时任务
echo ============================================
echo   一键安装定时任务（每晚 20:00 自动续火花）
echo   笔记本友好：用电池也运行、错过自动补跑
echo   只需要运行这一次！
echo ============================================
echo.

powershell -NoProfile -Command "$a = New-ScheduledTaskAction -Execute 'D:\Projects\AutoTiktokSpark\run_daily.bat' -WorkingDirectory 'D:\Projects\AutoTiktokSpark'; $t = New-ScheduledTaskTrigger -Daily -At 20:00; $s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -WakeToRun -ExecutionTimeLimit (New-TimeSpan -Hours 2); Register-ScheduledTask -TaskName 'AutoTiktokSpark_Huohua' -Action $a -Trigger $t -Settings $s -Force | Out-Null; if ($?) { Write-Host OK } else { exit 1 }"

if %errorlevel% equ 0 (
    echo.
    echo 安装成功！任务名: AutoTiktokSpark_Huohua
    echo 时间: 每天 20:00 自动开始（随机延迟后发送）
) else (
    echo.
    echo 安装失败，请截图本窗口联系助手排查。
)
echo.
pause
