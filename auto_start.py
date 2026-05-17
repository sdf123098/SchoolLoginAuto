import os
import sys


def _get_startup_dir() -> str:
    appdata = os.environ.get("APPDATA", "")
    return os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")


def _get_shortcut_path() -> str:
    return os.path.join(_get_startup_dir(), "CampusLogin.lnk")


def is_enabled() -> bool:
    """检查是否已启用开机自启"""
    # 检查 lnk 快捷方式或 bat 文件
    startup_dir = _get_startup_dir()
    if not os.path.isdir(startup_dir):
        return False
    for name in ["CampusLogin.lnk", "CampusLogin.bat"]:
        if os.path.isfile(os.path.join(startup_dir, name)):
            return True
    return False


def enable():
    """启用开机自启 — 在启动文件夹创建快捷方式"""
    exe_path = sys.executable
    shortcut_path = _get_shortcut_path()
    startup_dir = _get_startup_dir()

    os.makedirs(startup_dir, exist_ok=True)

    # 删除旧的 bat 文件（如果有）
    old_bat = os.path.join(startup_dir, "CampusLogin.bat")
    if os.path.isfile(old_bat):
        os.remove(old_bat)

    # 使用 PowerShell 创建快捷方式
    ps_script = (
        f"$WScriptShell = New-Object -ComObject WScript.Shell; "
        f"$Shortcut = $WScriptShell.CreateShortcut('{shortcut_path}'); "
        f"$Shortcut.TargetPath = '{exe_path}'; "
        f"$Shortcut.WorkingDirectory = '{os.path.dirname(exe_path)}'; "
        f"$Shortcut.Arguments = '--hidden'; "
        f"$Shortcut.Save()"
    )
    import subprocess
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", ps_script],
        capture_output=True, shell=False
    )


def disable():
    """禁用开机自启"""
    shortcut_path = _get_shortcut_path()
    if os.path.isfile(shortcut_path):
        os.remove(shortcut_path)
    # 也清理可能的 bat 文件
    startup_dir = _get_startup_dir()
    old_bat = os.path.join(startup_dir, "CampusLogin.bat")
    if os.path.isfile(old_bat):
        os.remove(old_bat)
