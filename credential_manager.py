import json
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


class CredentialManager:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.creds_path = os.path.join(data_dir, "credentials.enc")
        self.key_path = os.path.join(data_dir, ".keyfile")
        self._fernet: Optional[Fernet] = None
        self._accounts: list[dict] = []
        self._ensure_key()
        self._load()

    def _ensure_key(self):
        if not os.path.isfile(self.key_path):
            key = Fernet.generate_key()
            with open(self.key_path, "wb") as f:
                f.write(key)
        with open(self.key_path, "rb") as f:
            self._fernet = Fernet(f.read())

    def _load(self):
        if not os.path.isfile(self.creds_path):
            self._accounts = []
            return
        try:
            with open(self.creds_path, "rb") as f:
                encrypted = f.read()
            decrypted = self._fernet.decrypt(encrypted)
            data = json.loads(decrypted.decode("utf-8"))
            self._accounts = data.get("accounts", [])
        except (InvalidToken, json.JSONDecodeError, IOError):
            self._accounts = []

    def _save(self):
        data = json.dumps({"accounts": self._accounts}, ensure_ascii=False)
        encrypted = self._fernet.encrypt(data.encode("utf-8"))
        with open(self.creds_path, "wb") as f:
            f.write(encrypted)

    # --- CRUD ---
    def list_accounts(self) -> list[dict]:
        """返回不含密码的账号列表"""
        return [
            {"name": a["name"], "username": a["username"], "is_default": a.get("is_default", False)}
            for a in self._accounts
        ]

    def get_account(self, name: str) -> Optional[dict]:
        for a in self._accounts:
            if a["name"] == name:
                return dict(a)
        return None

    def get_account_password(self, name: str) -> Optional[str]:
        for a in self._accounts:
            if a["name"] == name:
                return a.get("password", "")
        return None

    def add_account(self, name: str, username: str, password: str, is_default: bool = False):
        # 去重
        self._accounts = [a for a in self._accounts if a["name"] != name]
        if is_default:
            for a in self._accounts:
                a["is_default"] = False
        self._accounts.append({
            "name": name,
            "username": username,
            "password": password,
            "is_default": is_default
        })
        self._save()

    def update_account(self, name: str, username: Optional[str] = None, password: Optional[str] = None, is_default: Optional[bool] = None):
        for a in self._accounts:
            if a["name"] == name:
                if username is not None:
                    a["username"] = username
                if password is not None:
                    a["password"] = password
                if is_default:
                    for aa in self._accounts:
                        aa["is_default"] = False
                    a["is_default"] = True
                self._save()
                return True
        return False

    def delete_account(self, name: str):
        self._accounts = [a for a in self._accounts if a["name"] != name]
        self._save()

    def get_default_account(self) -> Optional[dict]:
        for a in self._accounts:
            if a.get("is_default"):
                return dict(a)
        if self._accounts:
            return dict(self._accounts[0])
        return None

    def set_default_account(self, name: str):
        found = False
        for a in self._accounts:
            if a["name"] == name:
                a["is_default"] = True
                found = True
            else:
                a["is_default"] = False
        if found:
            self._save()

    def clear_all(self):
        self._accounts = []
        if os.path.isfile(self.creds_path):
            os.remove(self.creds_path)

    def clear_all_data(self):
        """删除所有数据和密钥"""
        self._accounts = []
        for f in [self.creds_path, self.key_path]:
            if os.path.isfile(f):
                os.remove(f)
