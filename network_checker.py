import socket
import time
from typing import Optional

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class NetworkChecker:
    def __init__(self, profile: Optional[dict] = None):
        self.profile = profile or {}
        self._bypass_proxy = False
        self._session = requests.Session()
        self._session.verify = False
        self._session.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

    def set_profile(self, profile: dict):
        self.profile = profile

    def set_bypass_proxy(self, enabled: bool):
        self._bypass_proxy = enabled
        self._session.trust_env = not enabled

    def set_verify_ssl(self, enabled: bool):
        self._session.verify = enabled

    def _dns_resolve(self, domain: str) -> bool:
        try:
            socket.getaddrinfo(domain, 80, socket.AF_INET, socket.SOCK_STREAM)
            return True
        except (socket.gaierror, socket.herror):
            return False

    def is_on_campus(self) -> bool:
        """通过 DNS 解析判断是否在校园网内"""
        detect = self.profile.get("detect", {})
        domains = detect.get("dns_domains", [])
        if not domains:
            return True  # 没有配置域名，默认认为是校内
        for domain in domains:
            if self._dns_resolve(domain):
                return True
        return False

    def check_need_login(self) -> bool:
        """HTTP 检测是否需要登录"""
        detect = self.profile.get("detect", {})
        test_url = detect.get("test_url", "")
        offline_keywords = detect.get("offline_keywords", [])
        online_keywords = detect.get("online_keywords", [])

        if not test_url or not offline_keywords:
            return False

        try:
            resp = self._session.get(test_url, timeout=5, allow_redirects=True)
            text = resp.text.lower()
            # 检查是否包含需要登录的关键词
            for kw in offline_keywords:
                if kw.lower() in text:
                    # 同时检查不在线
                    for okw in online_keywords:
                        if okw.lower() in text:
                            return False
                    return True
            return False
        except requests.RequestException:
            # 无法连接检测 URL，可能不在校内
            return False

    def check(self) -> dict:
        """完整检测，返回状态"""
        if not self.is_on_campus():
            return {"on_campus": False, "need_login": False, "status": "off_campus"}
        if self.check_need_login():
            return {"on_campus": True, "need_login": True, "status": "need_login"}
        return {"on_campus": True, "need_login": False, "status": "online"}
