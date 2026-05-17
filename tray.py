import threading
from typing import Callable

from PIL import Image, ImageDraw
import pystray


def _create_icon_image(color: str = "#4A90D9") -> Image.Image:
    """生成一个简单的 64x64 图标"""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 圆角矩形背景
    draw.rounded_rectangle([4, 4, 60, 60], radius=12, fill=color)
    # WiFi 标志简化版
    draw.arc([16, 16, 48, 48], start=220, end=320, fill="white", width=4)
    draw.arc([20, 22, 44, 42], start=220, end=320, fill="white", width=4)
    draw.arc([24, 28, 40, 36], start=220, end=320, fill="white", width=4)
    # 小圆点
    draw.ellipse([55, 35, 59, 39], fill="white")
    return img


class SystemTray:
    def __init__(
        self,
        on_show: Callable,
        on_login: Callable,
        on_logout: Callable,
        on_exit: Callable,
    ):
        self.on_show = on_show
        self.on_login = on_login
        self.on_logout = on_logout
        self.on_exit = on_exit
        self._icon = None
        self._menu = None

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem("显示主窗口", self._on_show, default=True),
            pystray.MenuItem("立即登录", self._on_login),
            pystray.MenuItem("注销登录", self._on_logout),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._on_exit),
        )

    def _on_show(self, icon, item):
        self.on_show()

    def _on_login(self, icon, item):
        threading.Thread(target=self.on_login, daemon=True).start()

    def _on_logout(self, icon, item):
        threading.Thread(target=self.on_logout, daemon=True).start()

    def _on_exit(self, icon, item):
        self.stop()
        self.on_exit()

    def start(self):
        image = _create_icon_image()
        self._icon = pystray.Icon(
            "campus_login",
            image,
            "校园网自动登录",
            menu=self._build_menu(),
        )
        self._icon.run_detached()

    def stop(self):
        if self._icon:
            self._icon.stop()
            self._icon = None

    def notify(self, title: str, message: str):
        if self._icon and hasattr(self._icon, "notify"):
            try:
                self._icon.notify(message, title=title)
            except Exception:
                pass

    def update_icon(self, color: str):
        if self._icon:
            self._icon.icon = _create_icon_image(color)
