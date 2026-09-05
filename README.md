# 🔥 AutoTiktokSpark · 抖音自动续火花

一个跑在 Windows 电脑上的全自动"续火花"工具：每晚定时用浏览器自动化操作
**抖音网页版**，自动给指定好友的私信会话发送一条你设定的话，让火花永不熄灭。

> 本项目仅供个人学习浏览器自动化技术使用。自动化操作违反平台用户协议的风险
> 由使用者自行评估；请将发送频率保持在本工具的默认量级（每天 1 条）。

## ✨ 特性

- **纯网页版方案**：不装模拟器、不装安卓 App，一台能上网的 Windows 电脑即可
- **系统 Edge 浏览器**：直接复用 Windows 自带的 Edge，无需额外下载浏览器
- **随机延迟**：每天在设定时间窗内（如 20:00–21:00）随机挑时间发送，贴近真人
- **失败自动重试**：单次运行最多 3 次尝试，间隔递增
- **登录失效报警**：检测到抖音要求重新登录时，截图 + 状态文件提醒，双击脚本重新扫码即可
- **全程留痕**：每次运行保存日志、截图证据，`latest_status.json` 一眼看结果
- **隐私隔离**：真实好友名/消息内容放在 `config.local.json`，已被 `.gitignore` 排除

## 🚀 快速开始

### 1. 环境要求

- Windows 10/11（自带 Edge 浏览器）
- Python 3.10+（安装时勾选 "Add Python to PATH"）

### 2. 安装依赖

```powershell
cd AutoTiktokSpark
python -m venv .venv --without-pip
python -m pip install --target .venv\Lib\site-packages playwright
# 国内网络可加镜像：-i https://mirrors.aliyun.com/pypi/simple/
```

> Playwright 只用于驱动浏览器，无需另下浏览器内核（脚本会调用系统 Edge）。

### 3. 配置你的好友和发送内容

把 `config.json` 复制一份命名为 `config.local.json`，修改：

```json
{
  "friend_name": "你要续火花的好友昵称（聊天列表里显示的名字）",
  "message": "每天固定发送的话",
  "random_delay_minutes": 55
}
```

`config.local.json` 已被 `.gitignore` 排除，不会被提交。

### 4. 扫码登录（一次性）

双击 `扫码登录.bat`（或命令行运行 `python huohua.py --login`），
在弹出的浏览器里用手机抖音扫码。登录状态保存在 `browser_profile/`。

### 5. 测试发送

双击 `立即测试发送.bat`（或 `python huohua.py --now`），
看到「✔ 发送成功」即打通全流程。

### 6. 设定每日自动运行

双击 `一键安装定时任务.bat`（注册 Windows 计划任务，每天 20:00 触发）。
它采用**电池友好**的注册方式——笔记本拔掉电源也按时运行、错过时间开机自动补跑：

```powershell
$action   = New-ScheduledTaskAction -Execute '<项目路径>\run_daily.bat' -WorkingDirectory '<项目路径>'
$trigger  = New-ScheduledTaskTrigger -Daily -At 20:00
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
  -StartWhenAvailable -WakeToRun -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName 'AutoTiktokSpark_Huohua' -Action $action -Trigger $trigger -Settings $settings -Force
```

> ⚠️ 不要用 `schtasks /create` 注册本任务：它默认"仅交流电时启动"，
> 笔记本用电池时任务会被静默跳过。

再双击 `设置电脑永不睡眠.bat`，保证晚上电脑不睡觉（锁屏、合盖均不影响运行）。

## 📖 使用与维护

- **怎么算成功**：`latest_status.json` 里 `"result": "SUCCESS"`
- **登录过期**（`NEED_LOGIN`）：重新双击 `扫码登录.bat`
- **发送失败**（`FAILED`）：看 `logs/` 最新日志和 `screenshots/` 截图排查
- **想暂停**：任务计划程序里禁用 `AutoTiktokSpark_Huohua` 任务
- 详细说明见 [`使用说明.md`](使用说明.md)

## 📁 目录结构

```
huohua.py               主脚本（登录检测/发送/重试/日志/截图）
config.json             公开示例配置（占位值）
config.local.json       本地真实配置（gitignore）
run_daily.bat           定时任务入口（无窗口等待）
扫码登录.bat / 立即测试发送.bat / 一键安装定时任务.bat / 设置电脑永不睡眠.bat
logs/                   运行日志与页面快照（gitignore）
screenshots/            发送证据截图（gitignore）
browser_profile/        Edge 登录状态（gitignore，删除后需重新扫码）
```

## ⚠️ 注意事项

1. **不要删除 `browser_profile/`**，也不要在自动化弹出的浏览器里点"退出登录"
2. 抖音网页版页面结构可能随版本变化，若失效请检查 `logs/` 里的页面快照并更新选择器
3. 保持每天 1 条的低频率，请勿改造为高频群发工具
