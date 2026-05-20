<p align="center">
  <a href="https://www.pixiv.net/artworks/142405299">
    <img src="assets/cover.png" alt="雨一直下Lv999 - MadYY" width="600">
  </a>
  <br>
  <em>Illustration by <a href="https://www.pixiv.net/en/users/118065">MadYY</a> — 「雨一直下Lv999」</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/platform-Windows%2010%2B-lightgrey.svg" alt="Windows 10+">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License">
</p>

---

# 校园网自动登录 · Campus Auto Login

自动检测校园网认证状态并完成登录/注销，支持 **Dr.COM (城市热点)**、**深澜 (Srun)** 等多品牌认证系统。

托盘最小化运行，开机自启，断线自动重连。

## 功能

- **自动检测** — DNS 解析判断是否在校园网内，HTTP 检测是否需要登录
- **自动登录** — 检测到需要认证时自动提交登录请求
- **IPv4/IPv6 双栈** — 支持同时向 IPv4 和 IPv6 认证接口发起登录
- **系统托盘** — 最小化到托盘，右键菜单快捷操作
- **多账号管理** — 加密存储多个账号，一键切换
- **Profile 系统** — JSON 配置文件定义认证接口，兼容不同学校/品牌
- **开机自启** — 创建启动文件夹快捷方式
- **代理绕过** — 可选忽略系统代理直连认证服务器
- **SSL 兼容** — 默认关闭 SSL 证书验证，适配校园网自签名证书

## 系统要求

- Windows 10+ (x64)
- Python 3.11+ (源码运行)
- 或直接使用打包好的 `CampusLogin.exe`

## 快速开始

### 直接运行 (EXE)

下载 [Releases](../../releases) 中的 `CampusLogin.exe`，双击启动。

### 从源码运行

```bash
pip install -r requirements.txt
python main.py
```

隐藏启动（仅托盘）：

```bash
python main.py --hidden
```

## 配置

### 账号管理

在「账号管理」页添加你的校园网账号，密码经 **Fernet 加密** 存储在本地 `data/` 目录。

### Profile 设置

Profile 定义了认证接口参数，位于 `profiles/` 目录。内置三种：

| Profile | 适用系统 |
|---------|---------|
| `stu.json` | 汕头大学 Dr.COM 6.x ac_portal |
| `drhot_generic.json` | 城市热点 Dr.COM 通用 (DDDDD/upass) |
| `srun_generic.json` | 深澜 Srun 通用 |

可在「Portal 设置」页切换、编辑、新建自定义 Profile。

### Profile JSON 结构

```json
{
  "name": "示例大学",
  "description": "Dr.COM 认证",
  "detect": {
    "dns_domains": ["a.example.edu.cn"],
    "test_url": "https://a.example.edu.cn/",
    "offline_keywords": ["login", "portal"],
    "online_keywords": ["success", "已在线"]
  },
  "login": {
    "method": "POST",
    "url": "https://a.example.edu.cn/ac_portal/login.php",
    "params": {
      "opr": "pwdLogin",
      "userName": "{username}",
      "pwd": "{password}"
    },
    "headers": { "Content-Type": "application/x-www-form-urlencoded" },
    "success_keywords": ["success", "登录成功"]
  },
  "logout": {
    "method": "POST",
    "url": "https://a.example.edu.cn/ac_portal/login.php",
    "params": { "opr": "pwdLogout" }
  }
}
```

占位符 `{username}` 和 `{password}` 在登录时自动替换。

## 打包为 EXE

```bash
pip install pyinstaller
pyinstaller --clean --noconfirm CampusLogin.spec
```

输出：`dist/CampusLogin.exe`（约 35MB，单文件）

## 项目结构

```
SchoolLogin/
├── main.py              # 入口，组装各模块
├── gui.py               # Tkinter 图形界面
├── login_handler.py     # 登录/注销请求
├── network_checker.py   # DNS + HTTP 网络状态检测
├── profile_manager.py   # Profile 读取/管理
├── credential_manager.py # 账号凭据加密存储
├── auto_start.py        # 开机自启管理
├── tray.py              # 系统托盘
├── profiles/            # 内置认证 Profile (JSON)
├── requirements.txt     # Python 依赖
├── CampusLogin.spec     # PyInstaller 打包配置
└── README.md
```

## 依赖

| 包 | 用途 |
|---|------|
| `requests` | HTTP 请求 |
| `cryptography` | 凭据加密 (Fernet) |
| `pystray` | 系统托盘 |
| `Pillow` | 托盘图标绘制 |
| `pywin32` | Windows API (开机自启) |

## 最近更新

**2026-05-17**
- 修复校园网 HTTPS 自签名证书导致连接失败的问题，新增 SSL 证书验证开关
- 优化网络检测逻辑：优先用 HTTP 重定向 (3xx) 判断在线状态，避免跟随重定向后页面关键词误判
- 修复 `--hidden` 模式首次登录成功后未自动退出的问题

## 许可

MIT License

---

<p align="center">
  <sub>Made with ☕ for campus life</sub>
</p>
