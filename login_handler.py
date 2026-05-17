import time
from urllib.parse import urlencode

import requests
import urllib3

# 校园网环境常有自签名证书，禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LoginHandler:
    def __init__(self, profile: dict = None):
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

    def _get_portal_cookies(self, login_config: dict):
        """登录前预访问 portal 获取 session cookie"""
        url = login_config.get("url", "")
        if not url:
            return
        from urllib.parse import urlparse
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}/"
        try:
            self._session.get(base_url, timeout=10, allow_redirects=True)
        except requests.RequestException:
            pass

    def login(self, username: str, password: str) -> dict:
        """执行登录，返回结果"""
        results = []
        login_config = self.profile.get("login", {})
        if not login_config:
            return {"success": False, "message": "未配置登录接口", "results": []}

        # 预访问 portal 获取 session cookie (AUTHSESSID 等)
        self._get_portal_cookies(login_config)

        # IPv4 登录
        try:
            kwargs = self._build_request_kwargs(login_config, username, password)
            resp = self._session.request(
                method=login_config.get("method", "POST"),
                url=kwargs["url"],
                headers=kwargs.get("headers", {}),
                data=kwargs.get("data"),
                json=kwargs.get("json"),
                allow_redirects=False,
                timeout=10
            )
            success_kw = [k.lower() for k in login_config.get("success_keywords", ["success"])]
            resp_text = resp.text.lower()
            text_match = any(kw in resp_text for kw in success_kw)
            # 302/303 重定向通常表示登录成功
            redirect_ok = resp.status_code in (301, 302, 303) and resp.headers.get("Location")
            ok = text_match or redirect_ok
            results.append({
                "type": "IPv4",
                "url": login_config.get("url"),
                "success": ok,
                "status_code": resp.status_code,
                "message": resp.text[:500] if resp.text else f"Redirect → {resp.headers.get('Location', '')}"
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
                    data=kwargs.get("data"),
                    json=kwargs.get("json"),
                    allow_redirects=False,
                    timeout=10
                )
                success_kw = [k.lower() for k in ipv6.get("success_keywords", ["success"])]
                resp_text = resp.text.lower()
                text_match = any(kw in resp_text for kw in success_kw)
                redirect_ok = resp.status_code in (301, 302, 303) and resp.headers.get("Location")
                ok = text_match or redirect_ok
                results.append({
                    "type": "IPv6",
                    "url": ipv6.get("url"),
                    "success": ok,
                    "status_code": resp.status_code,
                    "message": resp.text[:500] if resp.text else f"Redirect → {resp.headers.get('Location', '')}"
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
