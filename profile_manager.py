import json
import os
import shutil
from typing import Optional

class ProfileManager:
    def __init__(self, data_dir: str, builtin_profiles_dir: str):
        self.data_dir = data_dir
        self.builtin_profiles_dir = builtin_profiles_dir
        self.user_profiles_dir = os.path.join(data_dir, "profiles")
        self.config_path = os.path.join(data_dir, "config.json")
        os.makedirs(self.user_profiles_dir, exist_ok=True)

    def list_profiles(self) -> list[dict]:
        profiles = []
        seen = set()
        # 用户自定义优先
        for d in [self.user_profiles_dir, self.builtin_profiles_dir]:
            if not os.path.isdir(d):
                continue
            for fname in sorted(os.listdir(d)):
                if not fname.endswith(".json"):
                    continue
                path = os.path.join(d, fname)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        p = json.load(f)
                    name = p.get("name", fname)
                    if name not in seen:
                        seen.add(name)
                        profiles.append({"filename": fname, "path": path, "profile": p, "builtin": d == self.builtin_profiles_dir})
                except (json.JSONDecodeError, IOError):
                    continue
        return profiles

    def get_profile(self, name_or_filename: str) -> Optional[dict]:
        for p in self.list_profiles():
            if p["profile"].get("name") == name_or_filename or p["filename"] == name_or_filename:
                return p["profile"]
        return None

    def save_custom_profile(self, filename: str, profile: dict):
        if not filename.endswith(".json"):
            filename += ".json"
        path = os.path.join(self.user_profiles_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)

    def delete_custom_profile(self, filename: str):
        path = os.path.join(self.user_profiles_dir, filename)
        if os.path.isfile(path):
            os.remove(path)

    def duplicate_builtin_profile(self, filename: str) -> Optional[str]:
        src = os.path.join(self.builtin_profiles_dir, filename)
        if not os.path.isfile(src):
            return None
        dst = os.path.join(self.user_profiles_dir, filename)
        shutil.copy2(src, dst)
        return dst

    # --- 用户配置（当前选择的 profile、检测间隔等）---
    def load_config(self) -> dict:
        defaults = {
            "current_profile": "stu.json",
            "check_interval_seconds": 30,
            "auto_login": True,
            "default_account": "",
            "start_minimized": True
        }
        if os.path.isfile(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                defaults.update(data)
            except (json.JSONDecodeError, IOError):
                pass
        return defaults

    def save_config(self, config: dict):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def get_current_profile(self) -> Optional[dict]:
        config = self.load_config()
        profile_name = config.get("current_profile", "")
        return self.get_profile(profile_name) or self.get_profile("stu.json")
