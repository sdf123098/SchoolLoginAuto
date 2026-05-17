import os
import sys
import threading
import time
from typing import Optional

from profile_manager import ProfileManager
from credential_manager import CredentialManager
from network_checker import NetworkChecker
from login_handler import LoginHandler
from auto_start import is_enabled as auto_start_enabled, enable as auto_start_enable, disable as auto_start_disable
from gui import CampusLoginGUI
from tray import SystemTray


def get_app_dir() -> str:
    """获取程序所在目录（兼容 EXE 打包和直接运行）"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def get_data_dir() -> str:
    """获取数据目录"""
    d = os.path.join(get_app_dir(), "data")
    os.makedirs(d, exist_ok=True)
    return d


def get_builtin_profiles_dir() -> str:
    """获取内置 profiles 目录"""
    if getattr(sys, "frozen", False):
        # PyInstaller 打包后，profiles 在 sys._MEIPASS 中
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        return os.path.join(base, "profiles")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles")


class App:
    def __init__(self):
        self.data_dir = get_data_dir()
        self.profiles_dir = get_builtin_profiles_dir()

        # 核心模块
        self.profile_mgr = ProfileManager(self.data_dir, self.profiles_dir)
        self.credential_mgr = CredentialManager(self.data_dir)
        self.network_checker = NetworkChecker()
        self.login_handler = LoginHandler()

        # 加载当前 profile
        self._apply_current_profile()

        # 加载 bypass_proxy / verify_ssl 设置
        config = self.profile_mgr.load_config()
        self._set_bypass_proxy(config.get("bypass_proxy", False))
        self._set_verify_ssl(config.get("verify_ssl", False))

        # GUI
        self.gui = CampusLoginGUI(
            on_login=self._login,
            on_logout=self._logout,
            on_check=self._check,
            get_accounts=self.credential_mgr.list_accounts,
            add_account=self.credential_mgr.add_account,
            update_account=self.credential_mgr.update_account,
            delete_account=self.credential_mgr.delete_account,
            set_default_account=self.credential_mgr.set_default_account,
            get_profiles=self.profile_mgr.list_profiles,
            get_current_profile=self.profile_mgr.get_current_profile,
            set_current_profile=self._set_current_profile_name,
            save_custom_profile=self.profile_mgr.save_custom_profile,
            delete_custom_profile=self.profile_mgr.delete_custom_profile,
            get_config=self.profile_mgr.load_config,
            save_config=self.profile_mgr.save_config,
            get_auto_start=auto_start_enabled,
            set_auto_start=self._set_auto_start,
            get_bypass_proxy=lambda: self.profile_mgr.load_config().get("bypass_proxy", False),
            set_bypass_proxy=self._set_bypass_proxy,
            get_verify_ssl=lambda: self.profile_mgr.load_config().get("verify_ssl", False),
            set_verify_ssl=self._set_verify_ssl,
            clear_all_credentials=self.credential_mgr.clear_all,
        )

        # 托盘
        self.tray = SystemTray(
            on_show=self.gui.show,
            on_login=self._tray_login,
            on_logout=self._tray_logout,
            on_exit=self._shutdown,
        )

        # 后台检测
        self._running = True
        self._last_status = None
        self._detector_thread = threading.Thread(target=self._detector_loop, daemon=True)
        self._detector_thread.start()

    def _apply_current_profile(self):
        profile = self.profile_mgr.get_current_profile()
        if profile:
            self.network_checker.set_profile(profile)
            self.login_handler.set_profile(profile)

    def _set_current_profile_name(self, filename: str):
        profile = self.profile_mgr.get_profile(filename)
        if profile:
            self.network_checker.set_profile(profile)
            self.login_handler.set_profile(profile)

    def _set_auto_start(self, enabled: bool):
        if enabled:
            auto_start_enable()
        else:
            auto_start_disable()

    def _set_bypass_proxy(self, enabled: bool):
        self.network_checker.set_bypass_proxy(enabled)
        self.login_handler.set_bypass_proxy(enabled)
        config = self.profile_mgr.load_config()
        config["bypass_proxy"] = enabled
        self.profile_mgr.save_config(config)
        if hasattr(self, "gui"):
            self.gui.append_log(f"[代理] {'已屏蔽' if enabled else '已恢复'}系统代理")

    def _set_verify_ssl(self, enabled: bool):
        self.network_checker.set_verify_ssl(enabled)
        self.login_handler.set_verify_ssl(enabled)
        config = self.profile_mgr.load_config()
        config["verify_ssl"] = enabled
        self.profile_mgr.save_config(config)
        if hasattr(self, "gui"):
            self.gui.append_log(f"[SSL] {'已启用' if enabled else '已禁用'}SSL证书验证")

    # --- 桥接 GUI/托盘 到业务逻辑 ---
    def _login(self, account_name: str, username: str) -> dict:
        password = self.credential_mgr.get_account_password(account_name)
        if not password:
            return {"success": False, "message": "未找到密码"}
        result = self.login_handler.login(username, password)
        self.gui.append_log(f"[登录] 账号 {account_name}: {result['message']}")
        if result["success"]:
            self.tray.update_icon("#27AE60")
            self.tray.notify("登录成功", f"账号 {account_name} 已登录")
        return result

    def _logout(self) -> dict:
        result = self.login_handler.logout()
        self.gui.append_log(f"[注销] {result['message']}")
        if result["success"]:
            self.tray.update_icon("#4A90D9")
        return result

    def _check(self) -> dict:
        status = self.network_checker.check()
        # 更新托盘图标颜色
        if not status["on_campus"]:
            self.tray.update_icon("#95A5A6")  # 灰色
        elif status["need_login"]:
            self.tray.update_icon("#E67E22")  # 橙色
        else:
            self.tray.update_icon("#27AE60")  # 绿色
        return status

    def _tray_login(self):
        config = self.profile_mgr.load_config()
        account = self.credential_mgr.get_default_account()
        if account:
            self._login(account["name"], account["username"])

    def _tray_logout(self):
        self._logout()

    # --- 后台检测线程 ---
    def _detector_loop(self):
        while self._running:
            try:
                config = self.profile_mgr.load_config()
                interval = config.get("check_interval_seconds", 30)
                auto_login = config.get("auto_login", True)

                status = self._check()
                # 状态变化时记录日志
                if status != self._last_status:
                    self._last_status = status
                    if not status["on_campus"]:
                        self.gui.append_log("[检测] 不在校园网内")
                    elif status["need_login"]:
                        self.gui.append_log("[检测] 在校园网内，需要登录")
                        if auto_login:
                            self.gui.append_log("[自动] 尝试自动登录...")
                            account = self.credential_mgr.get_default_account()
                            if account:
                                self._login(account["name"], account["username"])
                            else:
                                self.gui.append_log("[自动] 无可用账号，跳过自动登录")
                    else:
                        self.gui.append_log("[检测] 已在线")

                time.sleep(interval)
            except Exception as e:
                self.gui.append_log(f"[错误] 检测异常: {e}")
                time.sleep(30)

    # --- 启动 ---
    def run(self):
        self.gui.append_log("[启动] 校园网自动登录程序已启动")
        self.tray.start()

        config = self.profile_mgr.load_config()
        if config.get("start_minimized", True):
            self.gui.hide()
        else:
            self.gui.show()

        # 首次检测
        threading.Thread(target=self._initial_check, daemon=True).start()

        self.gui.mainloop()

    def _initial_check(self):
        time.sleep(2)
        status = self._check()
        self._last_status = status
        self.gui.append_log(f"[初始检测] {status['status']}")

    def _shutdown(self):
        self._running = False
        self.gui.append_log("[退出] 程序正在退出...")
        self.tray.stop()
        # Tkinter 操作必须在主线程执行，用 after 投递到主线程
        self.gui.root.after(0, self._do_exit)

    def _do_exit(self):
        self.gui.quit()
        self.gui.destroy()
        os._exit(0)


def main():
    # 解析命令行
    start_minimized = "--hidden" in sys.argv

    if start_minimized:
        # 覆盖配置，以隐藏方式启动
        pass

    app = App()
    if start_minimized:
        app.gui.hide()
    app.run()


if __name__ == "__main__":
    main()
