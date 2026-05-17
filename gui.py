import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Callable, Optional
import threading
import time


class CampusLoginGUI:
    def __init__(
        self,
        # 回调函数由 main.py 注入
        on_login: Callable[[str, str], dict],
        on_logout: Callable[[], dict],
        on_check: Callable[[], dict],
        get_accounts: Callable[[], list],
        add_account: Callable[[str, str, str, bool], None],
        update_account: Callable[[str, Optional[str], Optional[str], Optional[bool]], bool],
        delete_account: Callable[[str], None],
        set_default_account: Callable[[str], None],
        get_profiles: Callable[[], list],
        get_current_profile: Callable[[], Optional[dict]],
        set_current_profile: Callable[[str], None],
        save_custom_profile: Callable[[str, dict], None],
        delete_custom_profile: Callable[[str], None],
        get_config: Callable[[], dict],
        save_config: Callable[[dict], None],
        get_auto_start: Callable[[], bool],
        set_auto_start: Callable[[bool], None],
        get_bypass_proxy: Callable[[], bool],
        set_bypass_proxy: Callable[[bool], None],
        get_verify_ssl: Callable[[], bool],
        set_verify_ssl: Callable[[bool], None],
        clear_all_credentials: Callable[[], None],
    ):
        self.on_login = on_login
        self.on_logout = on_logout
        self.on_check = on_check
        self.get_accounts = get_accounts
        self.add_account = add_account
        self.update_account = update_account
        self.delete_account = delete_account
        self.set_default_account = set_default_account
        self.get_profiles = get_profiles
        self.get_current_profile = get_current_profile
        self.set_current_profile = set_current_profile
        self.save_custom_profile = save_custom_profile
        self.delete_custom_profile = delete_custom_profile
        self.get_config = get_config
        self.save_config = save_config
        self.get_auto_start = get_auto_start
        self.set_auto_start = set_auto_start
        self.get_bypass_proxy = get_bypass_proxy
        self.set_bypass_proxy = set_bypass_proxy
        self.get_verify_ssl = get_verify_ssl
        self.set_verify_ssl = set_verify_ssl
        self.clear_all_credentials = clear_all_credentials

        self.root = tk.Tk()
        self.root.title("校园网自动登录 - Campus Auto Login")
        self.root.geometry("680x520")
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_notebook()
        self._refresh_all()

    # ===== Notebook =====
    def _build_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=4, pady=4)

        self.tab_dashboard = ttk.Frame(self.notebook)
        self.tab_accounts = ttk.Frame(self.notebook)
        self.tab_portal = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)
        self.tab_log = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_dashboard, text="仪表盘")
        self.notebook.add(self.tab_accounts, text="账号管理")
        self.notebook.add(self.tab_portal, text="Portal 设置")
        self.notebook.add(self.tab_settings, text="设置")
        self.notebook.add(self.tab_log, text="日志")

        self._build_dashboard()
        self._build_accounts()
        self._build_portal()
        self._build_settings()
        self._build_log()

    # ===== 仪表盘 =====
    def _build_dashboard(self):
        f = self.tab_dashboard
        f.columnconfigure(0, weight=1)

        # 状态卡片
        card = ttk.LabelFrame(f, text="网络状态", padding=15)
        card.grid(row=0, column=0, padx=15, pady=10, sticky="ew")

        self.lbl_campus_status = ttk.Label(card, text="检测中...", font=("", 14))
        self.lbl_campus_status.pack(pady=4)
        self.lbl_online_status = ttk.Label(card, text="", font=("", 12))
        self.lbl_online_status.pack(pady=2)

        # 账号选择
        acct_frame = ttk.Frame(f)
        acct_frame.grid(row=1, column=0, padx=15, pady=(10, 0), sticky="ew")
        ttk.Label(acct_frame, text="登录账号:").pack(side="left", padx=3)
        self.login_account_var = tk.StringVar()
        self.login_account_combo = ttk.Combobox(acct_frame, textvariable=self.login_account_var, state="readonly", width=28)
        self.login_account_combo.pack(side="left", padx=3)
        self.login_account_combo.bind("<<ComboboxSelected>>", self._on_login_account_selected)

        # 登录按钮区
        btn_frame = ttk.Frame(f)
        btn_frame.grid(row=2, column=0, padx=15, pady=10)

        self.btn_login = ttk.Button(btn_frame, text="立即登录", command=self._do_login, width=14)
        self.btn_login.pack(side="left", padx=8)

        self.btn_logout = ttk.Button(btn_frame, text="注销登录", command=self._do_logout, width=14)
        self.btn_logout.pack(side="left", padx=8)

        self.btn_refresh = ttk.Button(btn_frame, text="刷新状态", command=self._do_check, width=14)
        self.btn_refresh.pack(side="left", padx=8)

        # 当前账号与 profile 信息
        info = ttk.LabelFrame(f, text="当前配置", padding=10)
        info.grid(row=3, column=0, padx=15, pady=10, sticky="ew")

        self.lbl_current_account = ttk.Label(info, text="账号: 未选择")
        self.lbl_current_account.pack(anchor="w", pady=2)
        self.lbl_current_profile = ttk.Label(info, text="Profile: 未选择")
        self.lbl_current_profile.pack(anchor="w", pady=2)

    def _do_login(self):
        self.btn_login.config(state="disabled", text="登录中...")
        threading.Thread(target=self._login_thread, daemon=True).start()

    def _login_thread(self):
        try:
            account_name = self.login_account_var.get().strip()
            if not account_name:
                self.root.after(0, lambda: messagebox.showwarning("提示", "请先选择登录账号。"))
                return

            accounts = self.get_accounts()
            account = None
            for a in accounts:
                if a["name"] == account_name:
                    account = a
                    break

            if not account:
                self.root.after(0, lambda: messagebox.showwarning("提示", "未找到选中的账号，请刷新账号列表。"))
                return

            result = self.on_login(account["name"], account["username"])
            self.root.after(0, lambda: self._on_login_result(result))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
        finally:
            self.root.after(0, lambda: self.btn_login.config(state="normal", text="立即登录"))

    def _on_login_result(self, result):
        if result.get("success"):
            messagebox.showinfo("登录结果", "登录成功！")
        else:
            msg = result.get("message", "未知错误")
            details = result.get("results", [])
            detail_str = "\n".join(f"  {r['type']}: {r.get('message', '')[:100]}" for r in details)
            messagebox.showwarning("登录结果", f"{msg}\n{detail_str}")
        self._do_check()

    def _do_logout(self):
        self.btn_logout.config(state="disabled", text="注销中...")
        try:
            result = self.on_logout()
            messagebox.showinfo("注销结果", result.get("message", ""))
        except Exception as e:
            messagebox.showerror("错误", str(e))
        finally:
            self.btn_logout.config(state="normal", text="注销登录")
            self._do_check()

    def _do_check(self):
        try:
            status = self.on_check()
            self._update_status_display(status)
        except Exception as e:
            self.lbl_campus_status.config(text=f"检测异常: {e}")

    def _on_login_account_selected(self, event=None):
        pass  # 仅用于记录选择，实际登录时读取

    def _refresh_account_combo(self):
        accounts = self.get_accounts()
        names = [a["name"] for a in accounts]
        self.login_account_combo["values"] = names
        # 默认选中之前的账号，或默认账号，或第一个
        current = self.login_account_var.get()
        if current and current in names:
            return
        config = self.get_config()
        default_name = config.get("default_account", "")
        if default_name in names:
            self.login_account_var.set(default_name)
        elif names:
            self.login_account_var.set(names[0])

    def _update_status_display(self, status: dict):
        on_campus = status.get("on_campus", False)
        need_login = status.get("need_login", False)

        if not on_campus:
            self.lbl_campus_status.config(text="不在校园网内", foreground="gray")
            self.lbl_online_status.config(text="无需登录")
        elif need_login:
            self.lbl_campus_status.config(text="在校园网内", foreground="orange")
            self.lbl_online_status.config(text="需要登录", foreground="red")
        else:
            self.lbl_campus_status.config(text="在校园网内", foreground="green")
            self.lbl_online_status.config(text="已在线", foreground="green")

    # ===== 账号管理 =====
    def _build_accounts(self):
        f = self.tab_accounts
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)

        # 工具栏
        toolbar = ttk.Frame(f)
        toolbar.grid(row=0, column=0, sticky="ew", padx=8, pady=6)
        ttk.Button(toolbar, text="添加账号", command=self._add_account_dialog).pack(side="left", padx=3)
        ttk.Button(toolbar, text="编辑账号", command=self._edit_account_dialog).pack(side="left", padx=3)
        ttk.Button(toolbar, text="删除账号", command=self._delete_account).pack(side="left", padx=3)
        ttk.Button(toolbar, text="设为默认", command=self._set_default).pack(side="left", padx=3)

        # 账号列表
        cols = ("name", "username", "is_default")
        self.account_tree = ttk.Treeview(f, columns=cols, show="headings", selectmode="browse")
        self.account_tree.heading("name", text="名称")
        self.account_tree.heading("username", text="用户名")
        self.account_tree.heading("is_default", text="默认")
        self.account_tree.column("name", width=150)
        self.account_tree.column("username", width=200)
        self.account_tree.column("is_default", width=60)
        self.account_tree.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)

        scrollbar = ttk.Scrollbar(f, orient="vertical", command=self.account_tree.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.account_tree.configure(yscrollcommand=scrollbar.set)

    def _refresh_accounts(self):
        for item in self.account_tree.get_children():
            self.account_tree.delete(item)
        for a in self.get_accounts():
            default_mark = "✓" if a.get("is_default") else ""
            self.account_tree.insert("", "end", values=(a["name"], a["username"], default_mark))
        self._refresh_account_combo()

    def _add_account_dialog(self):
        dlg = _AccountDialog(self.root, "添加账号")
        if dlg.result:
            self.add_account(dlg.result["name"], dlg.result["username"], dlg.result["password"], dlg.result["is_default"])
            self._refresh_accounts()
            self.append_log(f"[账号] 添加账号: {dlg.result['name']}")

    def _edit_account_dialog(self):
        sel = self.account_tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个账号")
            return
        values = self.account_tree.item(sel[0], "values")
        name = values[0]
        account = None
        for a in self.get_accounts():
            if a["name"] == name:
                account = a
                break
        if not account:
            return
        dlg = _AccountDialog(self.root, "编辑账号", existing=account)
        if dlg.result:
            r = dlg.result
            self.update_account(name, username=r["username"], password=r["password"] or None, is_default=r["is_default"])
            self._refresh_accounts()
            self.append_log(f"[账号] 编辑账号: {r['name']}")

    def _delete_account(self):
        sel = self.account_tree.selection()
        if not sel:
            return
        values = self.account_tree.item(sel[0], "values")
        name = values[0]
        if messagebox.askyesno("确认", f"确定要删除账号 '{name}' 吗？"):
            self.delete_account(name)
            self._refresh_accounts()
            self.append_log(f"[账号] 删除账号: {name}")

    def _set_default(self):
        sel = self.account_tree.selection()
        if not sel:
            return
        values = self.account_tree.item(sel[0], "values")
        name = values[0]
        self.set_default_account(name)
        config = self.get_config()
        config["default_account"] = name
        self.save_config(config)
        self._refresh_accounts()
        self.append_log(f"[账号] 设为默认: {name}")

    # ===== Portal 设置 =====
    def _build_portal(self):
        f = self.tab_portal
        f.columnconfigure(0, weight=1)
        f.rowconfigure(2, weight=1)

        # Profile 选择
        sel_frame = ttk.Frame(f)
        sel_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=6)
        ttk.Label(sel_frame, text="当前 Portal:").pack(side="left", padx=3)
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(sel_frame, textvariable=self.profile_var, state="readonly", width=30)
        self.profile_combo.pack(side="left", padx=3)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_selected)
        ttk.Button(sel_frame, text="应用", command=self._apply_profile).pack(side="left", padx=3)
        ttk.Button(sel_frame, text="刷新", command=self._refresh_profiles).pack(side="left", padx=3)

        # Profile JSON 预览/编辑
        self.profile_text = scrolledtext.ScrolledText(f, wrap="none", font=("Consolas", 10))
        self.profile_text.grid(row=2, column=0, sticky="nsew", padx=8, pady=4)

        # 操作按钮
        btn_row = ttk.Frame(f)
        btn_row.grid(row=3, column=0, sticky="ew", padx=8, pady=6)
        ttk.Button(btn_row, text="保存修改", command=self._save_profile_edit).pack(side="left", padx=3)
        ttk.Button(btn_row, text="另存为新 Profile", command=self._save_as_new_profile).pack(side="left", padx=3)
        ttk.Button(btn_row, text="删除自定义 Profile", command=self._delete_custom_profile_action).pack(side="left", padx=3)

    def _refresh_profiles(self):
        profiles = self.get_profiles()
        names = [p["profile"].get("name", p["filename"]) for p in profiles]
        self.profile_combo["values"] = names
        config = self.get_config()
        current_name = config.get("current_profile", "")
        # 尝试匹配
        cur = self.get_current_profile()
        if cur:
            self.profile_var.set(cur.get("name", ""))

    def _on_profile_selected(self, event=None):
        name = self.profile_var.get()
        profiles = self.get_profiles()
        for p in profiles:
            if p["profile"].get("name") == name:
                self.profile_text.delete("1.0", "end")
                self.profile_text.insert("1.0", json.dumps(p["profile"], ensure_ascii=False, indent=2))
                break

    def _apply_profile(self):
        name = self.profile_var.get()
        profiles = self.get_profiles()
        for p in profiles:
            if p["profile"].get("name") == name:
                self.set_current_profile(p["filename"])
                config = self.get_config()
                config["current_profile"] = p["filename"]
                self.save_config(config)
                self.append_log(f"[Profile] 切换到: {name}")
                messagebox.showinfo("提示", f"已切换到 Profile: {name}")
                return

    def _save_profile_edit(self):
        try:
            new_profile = json.loads(self.profile_text.get("1.0", "end-1c"))
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON 格式错误", str(e))
            return
        name = self.profile_var.get()
        profiles = self.get_profiles()
        for p in profiles:
            if p["profile"].get("name") == name:
                if p["builtin"]:
                    messagebox.showinfo("提示", "内置 Profile 不可直接修改，请使用「另存为新 Profile」。")
                    return
                self.save_custom_profile(p["filename"], new_profile)
                self.append_log(f"[Profile] 保存: {name}")
                messagebox.showinfo("提示", f"Profile '{name}' 已保存")
                return

    def _save_as_new_profile(self):
        try:
            new_profile = json.loads(self.profile_text.get("1.0", "end-1c"))
        except json.JSONDecodeError as e:
            messagebox.showerror("JSON 格式错误", str(e))
            return
        dlg = _SimpleInputDialog(self.root, "另存为新 Profile", "文件名 (不含扩展名):")
        if dlg.result:
            fname = dlg.result + ".json"
            self.save_custom_profile(fname, new_profile)
            self._refresh_profiles()
            self.append_log(f"[Profile] 新建: {dlg.result}")

    def _delete_custom_profile_action(self):
        name = self.profile_var.get()
        profiles = self.get_profiles()
        for p in profiles:
            if p["profile"].get("name") == name:
                if p["builtin"]:
                    messagebox.showinfo("提示", "不能删除内置 Profile")
                    return
                if messagebox.askyesno("确认", f"确定要删除 Profile '{name}' 吗？"):
                    self.delete_custom_profile(p["filename"])
                    self._refresh_profiles()
                    self.profile_text.delete("1.0", "end")
                    self.append_log(f"[Profile] 删除: {name}")

    # ===== 设置 =====
    def _build_settings(self):
        f = self.tab_settings
        f.columnconfigure(0, weight=1)

        # 检测间隔
        row1 = ttk.Frame(f)
        row1.grid(row=0, column=0, sticky="ew", padx=15, pady=8)
        ttk.Label(row1, text="检测间隔 (秒):").pack(side="left")
        self.interval_var = tk.StringVar(value="30")
        ttk.Spinbox(row1, from_=5, to=600, textvariable=self.interval_var, width=8).pack(side="left", padx=8)
        ttk.Button(row1, text="应用", command=self._save_settings).pack(side="left", padx=4)

        # 开机自启
        row2 = ttk.Frame(f)
        row2.grid(row=1, column=0, sticky="ew", padx=15, pady=8)
        self.auto_start_var = tk.BooleanVar(value=self.get_auto_start())
        ttk.Checkbutton(row2, text="开机自动启动", variable=self.auto_start_var, command=self._toggle_auto_start).pack(anchor="w")

        # 启动时最小化
        row2b = ttk.Frame(f)
        row2b.grid(row=2, column=0, sticky="ew", padx=15, pady=8)
        self.start_minimized_var = tk.BooleanVar(value=self.get_config().get("start_minimized", True))
        ttk.Checkbutton(row2b, text="启动时最小化到托盘", variable=self.start_minimized_var, command=self._save_settings).pack(anchor="w")

        # 自动登录
        row3 = ttk.Frame(f)
        row3.grid(row=3, column=0, sticky="ew", padx=15, pady=8)
        self.auto_login_var = tk.BooleanVar(value=self.get_config().get("auto_login", True))
        ttk.Checkbutton(row3, text="检测到需要登录时自动登录", variable=self.auto_login_var, command=self._save_settings).pack(anchor="w")

        # 代理屏蔽
        row4 = ttk.Frame(f)
        row4.grid(row=4, column=0, sticky="ew", padx=15, pady=8)
        self.bypass_proxy_var = tk.BooleanVar(value=self.get_bypass_proxy())
        ttk.Checkbutton(row4, text="绕过所有代理 (忽略系统代理/环境变量代理)", variable=self.bypass_proxy_var, command=self._toggle_bypass_proxy).pack(anchor="w")

        # SSL 证书验证
        row5 = ttk.Frame(f)
        row5.grid(row=5, column=0, sticky="ew", padx=15, pady=8)
        self.verify_ssl_var = tk.BooleanVar(value=self.get_verify_ssl())
        ttk.Checkbutton(row5, text="验证 SSL 证书 (校园网环境通常需要关闭)", variable=self.verify_ssl_var, command=self._toggle_verify_ssl).pack(anchor="w")

        # 危险操作
        danger = ttk.LabelFrame(f, text="危险操作", padding=10)
        danger.grid(row=10, column=0, sticky="ew", padx=15, pady=15)

        ttk.Button(danger, text="清除所有凭据", command=self._clear_all_creds).pack(side="left", padx=6)
        ttk.Button(danger, text="清除所有数据 (含配置)", command=self._clear_all_data).pack(side="left", padx=6)

    def _save_settings(self):
        config = self.get_config()
        try:
            config["check_interval_seconds"] = int(self.interval_var.get())
        except ValueError:
            pass
        config["auto_login"] = self.auto_login_var.get()
        config["start_minimized"] = self.start_minimized_var.get()
        self.save_config(config)
        self.append_log("[设置] 设置已保存")

    def _toggle_auto_start(self):
        enabled = self.auto_start_var.get()
        self.set_auto_start(enabled)
        if enabled:
            self.append_log("[设置] 已启用开机自启")
        else:
            self.append_log("[设置] 已禁用开机自启")

    def _toggle_bypass_proxy(self):
        enabled = self.bypass_proxy_var.get()
        self.set_bypass_proxy(enabled)

    def _toggle_verify_ssl(self):
        enabled = self.verify_ssl_var.get()
        self.set_verify_ssl(enabled)

    def _clear_all_creds(self):
        if messagebox.askyesno("警告", "确定要清除所有保存的账号凭据吗？此操作不可撤销。"):
            self.clear_all_credentials()
            self._refresh_accounts()
            self.append_log("[设置] 已清除所有凭据")
            messagebox.showinfo("提示", "凭据已清除")

    def _clear_all_data(self):
        if messagebox.askyesno("警告", "确定要清除所有数据（包括配置和凭据）吗？\n程序将恢复到初始状态。此操作不可撤销。"):
            self.clear_all_credentials()
            config = self.get_config()
            for k in list(config.keys()):
                config[k] = None
            self.save_config({})
            self._refresh_all()
            self.append_log("[设置] 已清除所有数据")
            messagebox.showinfo("提示", "所有数据已清除，请重新配置。")

    # ===== 日志 =====
    def _build_log(self):
        f = self.tab_log
        f.columnconfigure(0, weight=1)
        f.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(f, wrap="word", font=("Consolas", 9), state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

    def append_log(self, msg: str):
        def _write():
            ts = time.strftime("%H:%M:%S")
            try:
                self.log_text.config(state="normal")
                self.log_text.insert("end", f"[{ts}] {msg}\n")
                self.log_text.see("end")
                self.log_text.config(state="disabled")
            except tk.TclError:
                pass
        try:
            self.root.after(0, _write)
        except tk.TclError:
            pass

    # ===== 全局刷新 =====
    def _refresh_all(self):
        self._refresh_accounts()
        self._refresh_account_combo()
        self._refresh_profiles()
        self._on_profile_selected()
        # 更新配置相关控件
        config = self.get_config()
        self.interval_var.set(str(config.get("check_interval_seconds", 30)))
        self.auto_login_var.set(config.get("auto_login", True))
        self.start_minimized_var.set(config.get("start_minimized", True))
        self.auto_start_var.set(self.get_auto_start())
        self.bypass_proxy_var.set(self.get_bypass_proxy())
        self.verify_ssl_var.set(self.get_verify_ssl())
        # 更新仪表盘信息
        cur = self.get_current_profile()
        self.lbl_current_profile.config(text=f"Profile: {cur.get('name', '未选择')}" if cur else "Profile: 未选择")
        default_account = ""
        for a in self.get_accounts():
            if a.get("is_default"):
                default_account = f"{a['name']} ({a['username']})"
                break
        self.lbl_current_account.config(text=f"账号: {default_account or '未选择'}")

    def _on_close(self):
        self.root.withdraw()

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self._do_check()
        self._refresh_all()

    def hide(self):
        self.root.withdraw()

    def mainloop(self):
        self.root.mainloop()

    def destroy(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def is_visible(self):
        try:
            return self.root.winfo_viewable()
        except tk.TclError:
            return False

    def quit(self):
        self.root.quit()


# ============ 工具对话框 ============

class _AccountDialog(tk.Toplevel):
    def __init__(self, parent, title, existing=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("350x250")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = None

        f = ttk.Frame(self, padding=15)
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="显示名称:").grid(row=0, column=0, sticky="w", pady=4)
        self.entry_name = ttk.Entry(f, width=30)
        self.entry_name.grid(row=0, column=1, pady=4)

        ttk.Label(f, text="用户名:").grid(row=1, column=0, sticky="w", pady=4)
        self.entry_user = ttk.Entry(f, width=30)
        self.entry_user.grid(row=1, column=1, pady=4)

        ttk.Label(f, text="密码:").grid(row=2, column=0, sticky="w", pady=4)
        self.entry_pass = ttk.Entry(f, width=30, show="*")
        self.entry_pass.grid(row=2, column=1, pady=4)

        self.is_default_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="设为默认账号", variable=self.is_default_var).grid(row=3, column=0, columnspan=2, pady=6, sticky="w")

        btn_row = ttk.Frame(f)
        btn_row.grid(row=4, column=0, columnspan=2, pady=10)
        ttk.Button(btn_row, text="确定", command=self._ok).pack(side="left", padx=5)
        ttk.Button(btn_row, text="取消", command=self.destroy).pack(side="left", padx=5)

        if existing:
            self.entry_name.insert(0, existing.get("name", ""))
            self.entry_user.insert(0, existing.get("username", ""))
            self.is_default_var.set(existing.get("is_default", False))
            self.entry_name.config(state="disabled")

        self.entry_user.focus_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self._ok())
        self.wait_window()

    def _ok(self):
        name = self.entry_name.get().strip()
        username = self.entry_user.get().strip()
        password = self.entry_pass.get()
        if not name or not username:
            messagebox.showwarning("提示", "名称和用户名不能为空")
            return
        self.result = {
            "name": name,
            "username": username,
            "password": password,
            "is_default": self.is_default_var.get()
        }
        self.destroy()


class _SimpleInputDialog(tk.Toplevel):
    def __init__(self, parent, title, prompt):
        super().__init__(parent)
        self.title(title)
        self.geometry("330x130")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = None

        f = ttk.Frame(self, padding=15)
        f.pack(fill="both", expand=True)

        ttk.Label(f, text=prompt).pack(anchor="w", pady=4)
        self.entry = ttk.Entry(f, width=35)
        self.entry.pack(fill="x", pady=4)
        self.entry.focus_set()

        btn_row = ttk.Frame(f)
        btn_row.pack(pady=8)
        ttk.Button(btn_row, text="确定", command=self._ok).pack(side="left", padx=5)
        ttk.Button(btn_row, text="取消", command=self.destroy).pack(side="left", padx=5)

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_window()

    def _ok(self):
        val = self.entry.get().strip()
        if val:
            self.result = val
        self.destroy()
