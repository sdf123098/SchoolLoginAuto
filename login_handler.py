import time
from urllib.parse import urlencode

import requests


class LoginHandler:
    def __init__(self, profile: dict = None):
        self.profile = profile or {}
        self._session = requests.Session()
        self._session.timeout = 10

    def set_profile(self, profile: dict):
        self.profile = profile

    def _substitute_params(self, params: dict, username: str, password: str) -> dict:
        """替换占位符"""
        result = {}
        for k, v in params.items():
            v_str = str(v)
            v_str = v_str.replace("{username}", username)
            v_str = v_str.replace("{password}", password)
            result[k] = v_str
        return result

    def _build_request_kwargs(self, login_config: dict, username: str, password: str) -> dict:
        method = login_config.get("method", "POST").upper()
        url = login_config.get("url", "")
        params = self._substitute_params(login_config.get("params", {}), username, password)
        headers = dict(login_config.get("headers", {}))
        encoding = login_config.get("encoding", "utf-8")

        kwargs = {"headers": headers, "allow_redirects": False, "timeout": 10}
        if method == "POST":
            kwargs["url"] = url
            ct = headers.get("Content-Type", "")
            if "json" in ct:
                kwargs["json"] = params
            else:
                kwargs["data"] = urlencode(params, encoding=encoding) if params else ""
        else:
            if params:
                kwargs["url"] = url + ("&" if "?" in url else "?") + urlencode(params, encoding=encoding)
            else:
                kwargs["url"] = url
        return kwargs

    def login(self, username: str, password: str) -> dict:
        """执行登录，返回结果"""
        results = []
        login_config = self.profile.get("login", {})
        if not login_config:
            return {"success": False, "message": "未配置登录接口", "results": []}

        # IPv4 登录
        try:
            kwargs = self._build_request_kwargs(login_config, username, password)
            resp = self._session.request(
                method=login_config.get("method", "POST"),
                url=kwargs["url"],
                headers=kwargs.get("headers", {}),
                data=kwargs.get("data", ""),
                allow_redirects=False,
                timeout=10
            )
            success_kw = [k.lower() for k in login_config.get("success_keywords", ["success"])]
            resp_text = resp.text.lower()
            ok = any(kw in resp_text for kw in success_kw)
            results.append({
                "type": "IPv4",
                "url": login_config.get("url"),
                "success": ok,
                "status_code": resp.status_code,
                "message": resp.text[:500]
            })
        except requests.RequestException as e:
            results.append({
                "type": "IPv4",
                "url": login_config.get("url"),
                "success": False,
                "message": str(e)
            })

        # IPv6 登录
        ipv6 = self.profile.get("ipv6_login", {})
        if ipv6.get("enabled") and ipv6.get("url"):
            try:
                kwargs = self._build_request_kwargs(ipv6, username, password)
                resp = self._session.request(
                    method=ipv6.get("method", "POST"),
                    url=kwargs["url"],
                    headers=kwargs.get("headers", {}),
                    data=kwargs.get("data", ""),
                    allow_redirects=False,
                    timeout=10
                )
                success_kw = [k.lower() for k in ipv6.get("success_keywords", ["success"])]
                resp_text = resp.text.lower()
                ok = any(kw in resp_text for kw in success_kw)
                results.append({
                    "type": "IPv6",
                    "url": ipv6.get("url"),
                    "success": ok,
                    "status_code": resp.status_code,
                    "message": resp.text[:500]
                })
            except requests.RequestException as e:
                results.append({
                    "type": "IPv6",
                    "url": ipv6.get("url"),
                    "success": False,
                    "message": str(e)
                })

        overall_success = any(r["success"] for r in results)
        return {
            "success": overall_success,
            "message": "登录成功" if overall_success else "登录失败",
            "results": results
        }

    def logout(self) -> dict:
        """执行注销"""
        logout_config = self.profile.get("logout", {})
        if not logout_config or not logout_config.get("url"):
            return {"success": False, "message": "未配置注销接口"}

        try:
            method = logout_config.get("method", "GET").upper()
            url = logout_config.get("url", "")
            params = logout_config.get("params", {})
            headers = dict(logout_config.get("headers", {}))
            if method == "POST":
                resp = self._session.post(url, data=params, headers=headers, timeout=10)
            else:
                resp = self._session.get(url, params=params, headers=headers, timeout=10)
            return {"success": True, "message": f"注销请求已发送 (HTTP {resp.status_code})"}
        except requests.RequestException as e:
            return {"success": False, "message": str(e)}
