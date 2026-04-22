"""
╔══════════════════════════════════════════════════════════════════╗
║           NEXUS ATM - Complete Banking Simulation                ║
║           Object-Oriented | GUI | File Persistence              ║
╚══════════════════════════════════════════════════════════════════╝

Features:
  - PIN authentication with 3-attempt lockout
  - Deposit, Withdraw, Transfer
  - Transaction History (mini-statement)
  - Admin Panel (create/view accounts)
  - Currency selection
  - Dark/Light theme toggle
  - Account info dashboard
  - File-based persistence
  - Receipt generation
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
import datetime


# ─────────────────────────────────────────────────────────────────
# CONSTANTS & CONFIGURATION (Tuple for immutable config)
# ─────────────────────────────────────────────────────────────────
APP_CONFIG = (
    "NEXUS ATM",          # 0: App title
    "1.0.0",              # 1: Version
    3,                    # 2: Max login attempts
    "accounts.json",      # 3: Accounts file
    "transactions.json",  # 4: Transactions file
    10,                   # 5: Mini-statement count
)

# Currency dictionary: symbol -> (name, rate_from_USD)
CURRENCIES: dict = {
    "USD": ("US Dollar",        1.00),
    "EUR": ("Euro",             0.92),
    "GBP": ("British Pound",    0.79),
    "INR": ("Indian Rupee",    83.12),
    "JPY": ("Japanese Yen",   149.50),
    "CAD": ("Canadian Dollar",  1.36),
    "AUD": ("Australian Dollar",1.53),
    "PKR": ("Pakistani Rupee", 278.0),
}

# ─────────────────────────────────────────────────────────────────
# THEME DEFINITIONS
# ─────────────────────────────────────────────────────────────────
THEMES: dict = {
    "dark": {
        "bg":          "#0A0E1A",
        "panel":       "#111827",
        "card":        "#1E2A3A",
        "accent":      "#00D4FF",
        "accent2":     "#7C3AED",
        "success":     "#10B981",
        "danger":      "#EF4444",
        "warning":     "#F59E0B",
        "text":        "#F0F6FF",
        "subtext":     "#8899AA",
        "border":      "#2A3A4A",
        "btn_fg":      "#0A0E1A",
        "entry_bg":    "#162030",
        "entry_fg":    "#00D4FF",
        "highlight":   "#00D4FF22",
        "header_bg":   "#07111F",
    },
    "light": {
        "bg":          "#EEF2F7",
        "panel":       "#FFFFFF",
        "card":        "#F8FAFC",
        "accent":      "#2563EB",
        "accent2":     "#7C3AED",
        "success":     "#059669",
        "danger":      "#DC2626",
        "warning":     "#D97706",
        "text":        "#0F172A",
        "subtext":     "#64748B",
        "border":      "#CBD5E1",
        "btn_fg":      "#FFFFFF",
        "entry_bg":    "#FFFFFF",
        "entry_fg":    "#0F172A",
        "highlight":   "#2563EB22",
        "header_bg":   "#1E3A5F",
    },
}


# ─────────────────────────────────────────────────────────────────
# DATA MODELS (OOP)
# ─────────────────────────────────────────────────────────────────

class Transaction:
    """Represents a single bank transaction."""

    def __init__(self, txn_type: str, amount: float, currency: str,
                 note: str = "", balance_after: float = 0.0):
        self.txn_type: str = txn_type          # e.g. "DEPOSIT", "WITHDRAW"
        self.amount: float = amount
        self.currency: str = currency
        self.note: str = note
        self.balance_after: float = balance_after
        self.timestamp: str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        """Convert transaction to dictionary for JSON storage."""
        return {
            "type":          self.txn_type,
            "amount":        self.amount,
            "currency":      self.currency,
            "note":          self.note,
            "balance_after": self.balance_after,
            "timestamp":     self.timestamp,
        }

    @staticmethod
    def from_dict(data: dict) -> "Transaction":
        """Reconstruct transaction from dictionary."""
        t = Transaction(
            txn_type=data["type"],
            amount=data["amount"],
            currency=data.get("currency", "USD"),
            note=data.get("note", ""),
            balance_after=data.get("balance_after", 0.0),
        )
        t.timestamp = data.get("timestamp", "N/A")
        return t

    def receipt_text(self) -> str:
        """Return a formatted receipt string."""
        sym = data_manager_ref.accounts.get  # resolved at runtime
        lines = [
            "=" * 38,
            "       NEXUS ATM — RECEIPT",
            "=" * 38,
            f"  Date  : {self.timestamp}",
            f"  Type  : {self.txn_type}",
            f"  Amount: {self.currency} {self.amount:,.2f}",
            f"  Note  : {self.note or 'N/A'}",
            f"  Bal   : {self.currency} {self.balance_after:,.2f}",
            "=" * 38,
            "    Thank you for using NEXUS ATM",
            "=" * 38,
        ]
        return "\n".join(lines)


class Account:
    """Represents a bank account with all its data and operations."""

    def __init__(self, acc_number: str, pin: str, name: str,
                 balance: float = 0.0, currency: str = "USD",
                 is_admin: bool = False):
        self.acc_number: str   = acc_number
        self.pin: str          = pin            # stored as plain string (demo only)
        self.name: str         = name
        self.balance: float    = balance
        self.currency: str     = currency
        self.is_admin: bool    = is_admin
        self.is_locked: bool   = False
        self.failed_attempts: int = 0
        self.transactions: list[Transaction] = []

    # ── Balance operations ──────────────────────────────────────

    def deposit(self, amount: float, note: str = "") -> Transaction:
        """Add funds to the account."""
        self.balance += amount
        txn = Transaction("DEPOSIT", amount, self.currency, note, self.balance)
        self.transactions.append(txn)
        return txn

    def withdraw(self, amount: float, note: str = "") -> Transaction:
        """Deduct funds; raises ValueError if insufficient balance."""
        if amount > self.balance:
            raise ValueError("Insufficient funds")
        self.balance -= amount
        txn = Transaction("WITHDRAWAL", amount, self.currency, note, self.balance)
        self.transactions.append(txn)
        return txn

    def transfer_out(self, amount: float, target_acc: str) -> Transaction:
        """Transfer funds out; balance check included."""
        if amount > self.balance:
            raise ValueError("Insufficient funds for transfer")
        self.balance -= amount
        note = f"Transfer to {target_acc}"
        txn = Transaction("TRANSFER OUT", amount, self.currency, note, self.balance)
        self.transactions.append(txn)
        return txn

    def transfer_in(self, amount: float, from_acc: str) -> Transaction:
        """Receive transferred funds."""
        self.balance += amount
        note = f"Transfer from {from_acc}"
        txn = Transaction("TRANSFER IN", amount, self.currency, note, self.balance)
        self.transactions.append(txn)
        return txn

    # ── PIN management ──────────────────────────────────────────

    def verify_pin(self, entered_pin: str) -> bool:
        """Check PIN and track failed attempts (max 3 → lock)."""
        if self.is_locked:
            return False
        if self.pin == entered_pin:
            self.failed_attempts = 0    # reset on success
            return True
        self.failed_attempts += 1
        if self.failed_attempts >= APP_CONFIG[2]:   # index 2 = max attempts
            self.is_locked = True
        return False

    def change_pin(self, old_pin: str, new_pin: str) -> bool:
        """Change PIN after verifying the old one."""
        if self.pin == old_pin:
            self.pin = new_pin
            return True
        return False

    # ── Serialization ───────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "acc_number":      self.acc_number,
            "pin":             self.pin,
            "name":            self.name,
            "balance":         self.balance,
            "currency":        self.currency,
            "is_admin":        self.is_admin,
            "is_locked":       self.is_locked,
            "failed_attempts": self.failed_attempts,
            "transactions":    [t.to_dict() for t in self.transactions],
        }

    @staticmethod
    def from_dict(data: dict) -> "Account":
        acc = Account(
            acc_number=data["acc_number"],
            pin=data["pin"],
            name=data["name"],
            balance=data.get("balance", 0.0),
            currency=data.get("currency", "USD"),
            is_admin=data.get("is_admin", False),
        )
        acc.is_locked       = data.get("is_locked", False)
        acc.failed_attempts = data.get("failed_attempts", 0)
        acc.transactions    = [Transaction.from_dict(t) for t in data.get("transactions", [])]
        return acc

    def mini_statement(self) -> list:
        """Return last N transactions."""
        return self.transactions[-APP_CONFIG[5]:]   # APP_CONFIG[5] = 10


# ─────────────────────────────────────────────────────────────────
# DATA MANAGER  (Handles file I/O)
# ─────────────────────────────────────────────────────────────────

class DataManager:
    """Manages loading/saving of accounts to JSON files."""

    def __init__(self):
        self.accounts: dict[str, Account] = {}   # acc_number → Account
        self.load_accounts()

    def load_accounts(self):
        """Load accounts from JSON file on startup."""
        filename = APP_CONFIG[3]    # "accounts.json"
        if os.path.exists(filename):
            with open(filename, "r") as f:
                raw: dict = json.load(f)
            for acc_no, data in raw.items():
                self.accounts[acc_no] = Account.from_dict(data)
        else:
            # Create default accounts if file missing
            self._create_default_accounts()

    def save_accounts(self):
        """Persist all accounts to JSON file."""
        filename = APP_CONFIG[3]
        data = {acc_no: acc.to_dict() for acc_no, acc in self.accounts.items()}
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

    def _create_default_accounts(self):
        """Seed demo accounts for first-time run."""
        defaults = [
            ("1001", "1234", "Alice Johnson",  5000.00, "USD", False),
            ("1002", "5678", "Bob Smith",      3200.50, "EUR", False),
            ("1003", "9999", "Carol White",   12000.00, "GBP", False),
            ("9999", "0000", "Admin User",    99999.99, "USD", True),
        ]
        for acc_no, pin, name, bal, cur, admin in defaults:
            acc = Account(acc_no, pin, name, bal, cur, admin)
            self.accounts[acc_no] = acc
        self.save_accounts()

    def get_account(self, acc_number: str):
        """Return Account object or None."""
        return self.accounts.get(acc_number)

    def create_account(self, acc_number: str, pin: str, name: str,
                       initial_balance: float, currency: str) -> bool:
        """Create new account; return False if number already exists."""
        if acc_number in self.accounts:
            return False
        new_acc = Account(acc_number, pin, name, initial_balance, currency)
        self.accounts[acc_number] = new_acc
        self.save_accounts()
        return True


# Global DataManager instance (singleton pattern)
data_manager_ref = DataManager()


# ─────────────────────────────────────────────────────────────────
# MAIN APPLICATION (Tkinter GUI)
# ─────────────────────────────────────────────────────────────────

class ATMApp(tk.Tk):
    """Root application window — manages all screens (frames)."""

    def __init__(self):
        super().__init__()

        # ── App-level state ──────────────────────────────────────
        self.data: DataManager     = data_manager_ref
        self.current_user: Account = None       # logged-in account
        self.theme_name: str       = "dark"
        self.theme: dict           = THEMES["dark"]
        self.selected_currency: str = "USD"

        # ── Window setup ─────────────────────────────────────────
        self.title(APP_CONFIG[0])               # "NEXUS ATM"
        self.geometry("520x680")
        self.resizable(False, False)
        self.configure(bg=self.theme["bg"])

        # Dictionary mapping screen names → Frame classes
        self.frames: dict = {}
        self._build_all_frames()
        self.show_frame("LoginScreen")

    # ── Frame Management ─────────────────────────────────────────

    def _build_all_frames(self):
        """Instantiate all screen frames and stack them."""
        container = tk.Frame(self, bg=self.theme["bg"])
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # All screen classes listed here
        screen_classes = (
            LoginScreen,
            CreateAccountScreen,
            DashboardScreen,
            DepositScreen,
            WithdrawScreen,
            TransferScreen,
            HistoryScreen,
            AccountInfoScreen,
            ChangePinScreen,
            AdminPanelScreen,
            ReceiptScreen,
        )

        for ScreenClass in screen_classes:
            frame = ScreenClass(container, self)
            self.frames[ScreenClass.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

    def show_frame(self, name: str):
        """Bring a frame to the front and refresh it."""
        frame = self.frames[name]
        frame.tkraise()
        # Call refresh hook if the screen defines one
        if hasattr(frame, "on_show"):
            frame.on_show()

    def logout(self):
        """Clear session and return to login."""
        self.current_user = None
        self.data.save_accounts()
        self.show_frame("LoginScreen")

    def apply_theme(self, theme_name: str):
        """Switch between dark/light themes (rebuilds all frames)."""
        self.theme_name = theme_name
        self.theme = THEMES[theme_name]
        self.configure(bg=self.theme["bg"])
        # Destroy and rebuild all frames with new theme
        for widget in self.winfo_children():
            widget.destroy()
        self.frames.clear()
        self._build_all_frames()
        # Go back to dashboard if user is still logged in
        if self.current_user:
            self.show_frame("DashboardScreen")
        else:
            self.show_frame("LoginScreen")

    # ── Utility helpers ──────────────────────────────────────────

    def format_balance(self, amount: float, currency: str = None) -> str:
        """Format balance with currency symbol."""
        cur = currency or (self.current_user.currency if self.current_user else "USD")
        return f"{cur} {amount:,.2f}"


# ─────────────────────────────────────────────────────────────────
# BASE SCREEN
# ─────────────────────────────────────────────────────────────────

class BaseScreen(tk.Frame):
    """Parent class for all ATM screens — shared helpers."""

    def __init__(self, parent, app: ATMApp):
        self.app = app
        super().__init__(parent, bg=app.theme["bg"])

    @property
    def T(self) -> dict:
        """Shortcut to current theme dict."""
        return self.app.theme

    # ── Reusable UI widgets ──────────────────────────────────────

    def make_header(self, title: str, subtitle: str = ""):
        """Render branded top header bar."""
        header = tk.Frame(self, bg=self.T["header_bg"], height=72)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Brand name
        tk.Label(
            header,
            text="◈ NEXUS ATM",
            font=("Courier New", 14, "bold"),
            bg=self.T["header_bg"],
            fg=self.T["accent"],
        ).place(x=14, y=10)

        # Screen title
        tk.Label(
            header,
            text=title,
            font=("Courier New", 11),
            bg=self.T["header_bg"],
            fg=self.T["text"],
        ).place(x=14, y=36)

        if subtitle:
            tk.Label(
                header,
                text=subtitle,
                font=("Courier New", 8),
                bg=self.T["header_bg"],
                fg=self.T["subtext"],
            ).place(x=14, y=56)

        # Theme toggle button
        theme_label = "☀ Light" if self.app.theme_name == "dark" else "● Dark"
        tk.Button(
            header,
            text=theme_label,
            font=("Courier New", 8),
            bg=self.T["card"],
            fg=self.T["subtext"],
            relief="flat",
            cursor="hand2",
            command=self._toggle_theme,
        ).place(relx=1.0, x=-8, y=24, anchor="ne")

        return header

    def _toggle_theme(self):
        new_theme = "light" if self.app.theme_name == "dark" else "dark"
        self.app.apply_theme(new_theme)

    def make_label(self, parent, text: str, size: int = 10,
                   bold: bool = False, color: str = None) -> tk.Label:
        weight = "bold" if bold else "normal"
        fg = color or self.T["text"]
        lbl = tk.Label(
            parent,
            text=text,
            font=("Courier New", size, weight),
            bg=parent["bg"],
            fg=fg,
        )
        return lbl

    def make_entry(self, parent, show: str = None,
                   width: int = 28) -> tk.Entry:
        """Styled input field."""
        e = tk.Entry(
            parent,
            font=("Courier New", 11),
            bg=self.T["entry_bg"],
            fg=self.T["entry_fg"],
            insertbackground=self.T["accent"],
            relief="flat",
            width=width,
            show=show,
            highlightthickness=1,
            highlightbackground=self.T["border"],
            highlightcolor=self.T["accent"],
        )
        return e

    def make_button(self, parent, text: str, command,
                    style: str = "primary", width: int = 22) -> tk.Button:
        """
        Styled button.
        style options: 'primary', 'success', 'danger', 'secondary', 'warning'
        """
        colors: dict = {
            "primary":   (self.T["accent"],   self.T["btn_fg"]),
            "success":   (self.T["success"],  self.T["btn_fg"]),
            "danger":    (self.T["danger"],   self.T["btn_fg"]),
            "secondary": (self.T["card"],     self.T["text"]),
            "warning":   (self.T["warning"],  self.T["btn_fg"]),
        }
        bg, fg = colors.get(style, colors["primary"])
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Courier New", 10, "bold"),
            bg=bg,
            fg=fg,
            relief="flat",
            cursor="hand2",
            width=width,
            pady=6,
            activebackground=self.T["accent2"],
            activeforeground=self.T["btn_fg"],
        )
        return btn

    def make_card(self, parent, padx: int = 20, pady: int = 14) -> tk.Frame:
        """Rounded-style card panel."""
        card = tk.Frame(
            parent,
            bg=self.T["card"],
            highlightthickness=1,
            highlightbackground=self.T["border"],
        )
        return card

    def show_success(self, msg: str):
        messagebox.showinfo("✔ Success", msg)

    def show_error(self, msg: str):
        messagebox.showerror("✘ Error", msg)

    def show_warning(self, msg: str):
        messagebox.showwarning("⚠ Warning", msg)

    def ask_confirm(self, title: str, msg: str) -> bool:
        return messagebox.askyesno(title, msg)

    def validate_amount(self, value: str) -> float:
        """
        Validate that a string is a positive number.
        Returns float or raises ValueError with helpful message.
        """
        value = value.strip()
        if not value:
            raise ValueError("Amount cannot be empty")
        try:
            amount = float(value)
        except ValueError:
            raise ValueError("Please enter a valid numeric amount")
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        if amount > 1_000_000:
            raise ValueError("Amount exceeds single-transaction limit (1,000,000)")
        return round(amount, 2)


# ─────────────────────────────────────────────────────────────────
# SCREEN 1 — LOGIN
# ─────────────────────────────────────────────────────────────────

class LoginScreen(BaseScreen):
    """PIN authentication screen with attempt tracking."""

    def __init__(self, parent, app: ATMApp):
        super().__init__(parent, app)
        self._attempts_left = APP_CONFIG[2]     # 3
        self._build_ui()

    def _build_ui(self):
        self.make_header("Login", "Enter your credentials to continue")

        body = tk.Frame(self, bg=self.T["bg"])
        body.pack(fill="both", expand=True, padx=30, pady=20)

        # ── Welcome banner ───────────────────────────────────────
        banner = self.make_card(body)
        banner.pack(fill="x", pady=(0, 16))
        tk.Label(
            banner,
            text="◈  Welcome to NEXUS ATM",
            font=("Courier New", 13, "bold"),
            bg=self.T["card"],
            fg=self.T["accent"],
            pady=10,
        ).pack()
        tk.Label(
            banner,
            text=f"v{APP_CONFIG[1]}  |  Secure Banking Terminal",
            font=("Courier New", 8),
            bg=self.T["card"],
            fg=self.T["subtext"],
            pady=4,
        ).pack()

        # ── Form card ────────────────────────────────────────────
        form = self.make_card(body)
        form.pack(fill="x")

        inner = tk.Frame(form, bg=self.T["card"])
        inner.pack(padx=24, pady=20)

        # Account number
        self.make_label(inner, "Account Number", bold=True).pack(anchor="w")
        self.acc_entry = self.make_entry(inner)
        self.acc_entry.pack(fill="x", pady=(4, 12))

        # PIN
        self.make_label(inner, "PIN", bold=True).pack(anchor="w")
        self.pin_entry = self.make_entry(inner, show="●")
        self.pin_entry.pack(fill="x", pady=(4, 4))

        # Attempt counter label
        self.attempt_label = tk.Label(
            inner,
            text=f"Attempts remaining: {self._attempts_left}",
            font=("Courier New", 8),
            bg=self.T["card"],
            fg=self.T["subtext"],
        )
        self.attempt_label.pack(anchor="e", pady=(0, 12))

        # Login button
        self.make_button(inner, "► LOGIN", self._login,
                         style="primary", width=30).pack(pady=4)

        # Separator
        tk.Frame(inner, bg=self.T["border"], height=1).pack(fill="x", pady=12)

        # Create account
        tk.Label(
            inner,
            text="New customer?",
            font=("Courier New", 8),
            bg=self.T["card"],
            fg=self.T["subtext"],
        ).pack()
        self.make_button(inner, "Create New Account",
                         lambda: self.app.show_frame("CreateAccountScreen"),
                         style="secondary", width=30).pack(pady=6)

        # Bind Enter key
        self.acc_entry.bind("<Return>", lambda e: self.pin_entry.focus())
        self.pin_entry.bind("<Return>", lambda e: self._login())

    def on_show(self):
        """Reset form when screen is shown."""
        self._attempts_left = APP_CONFIG[2]
        self.acc_entry.delete(0, "end")
        self.pin_entry.delete(0, "end")
        self.attempt_label.config(text=f"Attempts remaining: {self._attempts_left}")
        self.acc_entry.focus()

    def _login(self):
        acc_no: str = self.acc_entry.get().strip()
        pin: str    = self.pin_entry.get().strip()

        # ── Input validation ─────────────────────────────────────
        if not acc_no:
            self.show_error("Account number cannot be empty")
            return
        if not pin:
            self.show_error("PIN cannot be empty")
            return
        if not pin.isdigit():
            self.show_error("PIN must contain digits only")
            return

        # ── Lookup account ───────────────────────────────────────
        account: Account = self.app.data.get_account(acc_no)
        if account is None:
            self._decrement_attempts()
            self.show_error("Account not found. Check your account number.")
            return

        # ── Check lock ───────────────────────────────────────────
        if account.is_locked:
            self.show_error("This account is LOCKED after too many failed attempts.\nContact your bank.")
            return

        # ── Verify PIN ───────────────────────────────────────────
        if account.verify_pin(pin):
            self.app.current_user = account
            self.app.selected_currency = account.currency
            self.app.data.save_accounts()
            self.app.show_frame("DashboardScreen")
        else:
            self._decrement_attempts()
            remaining = APP_CONFIG[2] - account.failed_attempts
            if account.is_locked:
                self.show_error("Too many failed attempts. Account LOCKED.")
            else:
                self.show_error(f"Incorrect PIN. {remaining} attempt(s) left.")
            self.pin_entry.delete(0, "end")

    def _decrement_attempts(self):
        self._attempts_left -= 1
        if self._attempts_left <= 0:
            self._attempts_left = 0
        color = self.T["danger"] if self._attempts_left <= 1 else self.T["subtext"]
        self.attempt_label.config(
            text=f"Attempts remaining: {self._attempts_left}",
            fg=color,
        )


# ─────────────────────────────────────────────────────────────────
# SCREEN 2 — CREATE ACCOUNT
# ─────────────────────────────────────────────────────────────────

class CreateAccountScreen(BaseScreen):

    def __init__(self, parent, app: ATMApp):
        super().__init__(parent, app)
        self._build_ui()

    def _build_ui(self):
        self.make_header("Create Account", "Open a new bank account")

        body = tk.Frame(self, bg=self.T["bg"])
        body.pack(fill="both", expand=True, padx=30, pady=16)

        form = self.make_card(body)
        form.pack(fill="x")
        inner = tk.Frame(form, bg=self.T["card"])
        inner.pack(padx=24, pady=18)

        # Fields: label → (attribute, show, placeholder)
        fields = (
            ("Full Name",       "name_entry",    None, "e.g. John Doe"),
            ("Account Number",  "acc_entry",     None, "e.g. 2001"),
            ("PIN (4 digits)",  "pin_entry",     "●",  "4-digit PIN"),
            ("Confirm PIN",     "cpin_entry",    "●",  "Repeat PIN"),
            ("Initial Deposit", "deposit_entry", None, "Minimum 0"),
        )
        for label, attr, show, hint in fields:
            self.make_label(inner, label, bold=True).pack(anchor="w")
            e = self.make_entry(inner, show=show)
            e.pack(fill="x", pady=(4, 10))
            setattr(self, attr, e)

        # Currency selection
        self.make_label(inner, "Currency", bold=True).pack(anchor="w")
        self.cur_var = tk.StringVar(value="USD")
        cur_frame = tk.Frame(inner, bg=self.T["card"])
        cur_frame.pack(fill="x", pady=(4, 12))
        # Loop over currencies to build radio buttons
        for code in list(CURRENCIES.keys())[:6]:   # show first 6 for space
            tk.Radiobutton(
                cur_frame,
                text=code,
                value=code,
                variable=self.cur_var,
                bg=self.T["card"],
                fg=self.T["text"],
                selectcolor=self.T["entry_bg"],
                font=("Courier New", 9),
                activebackground=self.T["card"],
            ).pack(side="left", padx=4)

        tk.Frame(inner, bg=self.T["border"], height=1).pack(fill="x", pady=8)

        btn_row = tk.Frame(inner, bg=self.T["card"])
        btn_row.pack(fill="x")
        self.make_button(btn_row, "✔ CREATE ACCOUNT", self._create,
                         style="success", width=18).pack(side="left", padx=(0, 8))
        self.make_button(btn_row, "← Back", lambda: self.app.show_frame("LoginScreen"),
                         style="secondary", width=10).pack(side="left")

    def on_show(self):
        """Clear all fields when shown."""
        for attr in ("name_entry", "acc_entry", "pin_entry", "cpin_entry", "deposit_entry"):
            getattr(self, attr).delete(0, "end")

    def _create(self):
        name    = self.name_entry.get().strip()
        acc_no  = self.acc_entry.get().strip()
        pin     = self.pin_entry.get().strip()
        cpin    = self.cpin_entry.get().strip()
        dep_str = self.deposit_entry.get().strip()
        currency = self.cur_var.get()

        # ── Validation loop ──────────────────────────────────────
        validations = (
            (not name,                    "Full name cannot be empty"),
            (not acc_no,                  "Account number cannot be empty"),
            (not acc_no.isdigit(),        "Account number must be numeric"),
            (not pin,                     "PIN cannot be empty"),
            (not pin.isdigit(),           "PIN must be digits only"),
            (len(pin) != 4,               "PIN must be exactly 4 digits"),
            (pin != cpin,                 "PINs do not match"),
        )
        for condition, msg in validations:
            if condition:
                self.show_error(msg)
                return

        # Validate deposit amount
        try:
            deposit = self.validate_amount(dep_str) if dep_str else 0.0
        except ValueError as e:
            self.show_error(str(e))
            return

        # ── Create account ───────────────────────────────────────
        success = self.app.data.create_account(acc_no, pin, name, deposit, currency)
        if success:
            self.show_success(
                f"Account created!\n\nAccount Number: {acc_no}\nName: {name}"
                f"\nInitial Balance: {currency} {deposit:,.2f}"
            )
            self.app.show_frame("LoginScreen")
        else:
            self.show_error(f"Account number {acc_no} already exists.")


# ─────────────────────────────────────────────────────────────────
# SCREEN 3 — DASHBOARD
# ─────────────────────────────────────────────────────────────────

class DashboardScreen(BaseScreen):

    def __init__(self, parent, app: ATMApp):
        super().__init__(parent, app)
        self._build_ui()

    def _build_ui(self):
        self.make_header("Dashboard", "Main Menu")

        self.body = tk.Frame(self, bg=self.T["bg"])
        self.body.pack(fill="both", expand=True, padx=24, pady=14)

        # ── Balance card ─────────────────────────────────────────
        self.balance_card = self.make_card(self.body)
        self.balance_card.pack(fill="x", pady=(0, 14))
        bal_inner = tk.Frame(self.balance_card, bg=self.T["card"])
        bal_inner.pack(padx=20, pady=14)

        self.greeting_lbl = tk.Label(
            bal_inner, text="", font=("Courier New", 10),
            bg=self.T["card"], fg=self.T["subtext"]
        )
        self.greeting_lbl.pack(anchor="w")

        self.balance_lbl = tk.Label(
            bal_inner, text="",
            font=("Courier New", 22, "bold"),
            bg=self.T["card"], fg=self.T["accent"]
        )
        self.balance_lbl.pack(anchor="w", pady=4)

        self.acc_info_lbl = tk.Label(
            bal_inner, text="", font=("Courier New", 8),
            bg=self.T["card"], fg=self.T["subtext"]
        )
        self.acc_info_lbl.pack(anchor="w")

        # ── Menu buttons grid ────────────────────────────────────
        menu_card = self.make_card(self.body)
        menu_card.pack(fill="x")
        grid = tk.Frame(menu_card, bg=self.T["card"])
        grid.pack(padx=16, pady=14)

        # Menu items: (label, screen_name, style, row, col)
        menu_items = (
            ("💰  Deposit",      "DepositScreen",    "success",   0, 0),
            ("💸  Withdraw",     "WithdrawScreen",   "danger",    0, 1),
            ("↔  Transfer",     "TransferScreen",   "primary",   1, 0),
            ("📋  History",      "HistoryScreen",    "secondary", 1, 1),
            ("👤  Account Info", "AccountInfoScreen","secondary", 2, 0),
            ("🔑  Change PIN",   "ChangePinScreen",  "warning",   2, 1),
        )
        for label, screen, style, row, col in menu_items:
            btn = self.make_button(
                grid, label,
                lambda s=screen: self.app.show_frame(s),
                style=style, width=16
            )
            btn.grid(row=row, column=col, padx=6, pady=5)

        # ── Bottom row ───────────────────────────────────────────
        bottom = tk.Frame(self.body, bg=self.T["bg"])
        bottom.pack(fill="x", pady=12)
        self.make_button(bottom, "⚙  Admin Panel",
                         self._goto_admin, style="secondary", width=16).pack(side="left")
        self.make_button(bottom, "⏻  Logout",
                         self._logout, style="danger", width=14).pack(side="right")

    def on_show(self):
        """Refresh balance display on each visit."""
        u = self.app.current_user
        if u is None:
            return
        self.greeting_lbl.config(text=f"Good day, {u.name}")
        self.balance_lbl.config(
            text=self.app.format_balance(u.balance, u.currency)
        )
        self.acc_info_lbl.config(
            text=f"Account: {u.acc_number}  |  Currency: {u.currency}"
                 f"  |  Txns: {len(u.transactions)}"
        )

    def _goto_admin(self):
        u = self.app.current_user
        if u and u.is_admin:
            self.app.show_frame("AdminPanelScreen")
        else:
            self.show_error("Admin access only.\nPlease login as an admin account.")

    def _logout(self):
        if self.ask_confirm("Logout", "Are you sure you want to logout?"):
            self.app.logout()


# ─────────────────────────────────────────────────────────────────
# SCREEN 4 — DEPOSIT
# ─────────────────────────────────────────────────────────────────

class DepositScreen(BaseScreen):

    def __init__(self, parent, app: ATMApp):
        super().__init__(parent, app)
        self._build_ui()

    def _build_ui(self):
        self.make_header("Deposit", "Add funds to your account")

        body = tk.Frame(self, bg=self.T["bg"])
        body.pack(fill="both", expand=True, padx=30, pady=20)

        form = self.make_card(body)
        form.pack(fill="x")
        inner = tk.Frame(form, bg=self.T["card"])
        inner.pack(padx=24, pady=20)

        # Quick-amount buttons
        self.make_label(inner, "Quick Select", bold=True).pack(anchor="w")
        quick_row = tk.Frame(inner, bg=self.T["card"])
        quick_row.pack(fill="x", pady=(6, 14))

        # Tuple of quick amounts
        quick_amounts = (50, 100, 200, 500, 1000)
        for amt in quick_amounts:
            tk.Button(
                quick_row,
                text=f"+{amt}",
                font=("Courier New", 9, "bold"),
                bg=self.T["entry_bg"],
                fg=self.T["success"],
                relief="flat",
                cursor="hand2",
                padx=8, pady=4,
                command=lambda a=amt: self._set_quick(a),
            ).pack(side="left", padx=3)

        self.make_label(inner, "Amount", bold=True).pack(anchor="w")
        self.amount_entry = self.make_entry(inner)
        self.amount_entry.pack(fill="x", pady=(4, 10))

        self.make_label(inner, "Note / Description (optional)", bold=True).pack(anchor="w")
        self.note_entry = self.make_entry(inner)
        self.note_entry.pack(fill="x", pady=(4, 16))

        tk.Frame(inner, bg=self.T["border"], height=1).pack(fill="x", pady=4)

        btn_row = tk.Frame(inner, bg=self.T["card"])
        btn_row.pack(fill="x", pady=10)
        self.make_button(btn_row, "✔ DEPOSIT", self._deposit,
                         style="success", width=16).pack(side="left", padx=(0, 8))
        self.make_button(btn_row, "← Back", lambda: self.app.show_frame("DashboardScreen"),
                         style="secondary", width=10).pack(side="left")

    def on_show(self):
        self.amount_entry.delete(0, "end")
        self.note_entry.delete(0, "end")

    def _set_quick(self, amount: int):
        self.amount_entry.delete(0, "end")
        self.amount_entry.insert(0, str(amount))

    def _deposit(self):
        try:
            amount = self.validate_amount(self.amount_entry.get())
        except ValueError as e:
            self.show_error(str(e))
            return

        note = self.note_entry.get().strip()
        u = self.app.current_user

        # Confirm action
        if not self.ask_confirm(
            "Confirm Deposit",
            f"Deposit {u.currency} {amount:,.2f} into account {u.acc_number}?"
        ):
            return

        txn = u.deposit(amount, note)
        self.app.data.save_accounts()
        self.app.frames["ReceiptScreen"].set_receipt(txn)
        self.show_success(f"Deposited {u.currency} {amount:,.2f} successfully!")
        self.on_show()
        self.app.show_frame("ReceiptScreen")


# ─────────────────────────────────────────────────────────────────
# SCREEN 5 — WITHDRAW
# ─────────────────────────────────────────────────────────────────

class WithdrawScreen(BaseScreen):

    def __init__(self, parent, app: ATMApp):
        super().__init__(parent, app)
        self._build_ui()

    def _build_ui(self):
        self.make_header("Withdraw", "Take out cash from your account")

        body = tk.Frame(self, bg=self.T["bg"])
        body.pack(fill="both", expand=True, padx=30, pady=20)

        form = self.make_card(body)
        form.pack(fill="x")
        inner = tk.Frame(form, bg=self.T["card"])
        inner.pack(padx=24, pady=20)

        # Balance display
        self.bal_lbl = tk.Label(
            inner, text="",
            font=("Courier New", 10), bg=self.T["card"], fg=self.T["subtext"]
        )
        self.bal_lbl.pack(anchor="w", pady=(0, 12))

        # Quick withdraw buttons
        self.make_label(inner, "Quick Withdraw", bold=True).pack(anchor="w")
        quick_row = tk.Frame(inner, bg=self.T["card"])
        quick_row.pack(fill="x", pady=(6, 14))
        for amt in (20, 50, 100, 200, 500):
            tk.Button(
                quick_row,
                text=f"{amt}",
                font=("Courier New", 9, "bold"),
                bg=self.T["entry_bg"],
                fg=self.T["danger"],
                relief="flat", cursor="hand2",
                padx=8, pady=4,
                command=lambda a=amt: self._set_quick(a),
            ).pack(side="left", padx=3)

        self.make_label(inner, "Amount", bold=True).pack(anchor="w")
        self.amount_entry = self.make_entry(inner)
        self.amount_entry.pack(fill="x", pady=(4, 10))

        self.make_label(inner, "Note (optional)", bold=True).pack(anchor="w")
        self.note_entry = self.make_entry(inner)
        self.note_entry.pack(fill="x", pady=(4, 14))

        tk.Frame(inner, bg=self.T["border"], height=1).pack(fill="x", pady=4)

        btn_row = tk.Frame(inner, bg=self.T["card"])
        btn_row.pack(fill="x", pady=10)
        self.make_button(btn_row, "✔ WITHDRAW", self._withdraw,
                         style="danger", width=16).pack(side="left", padx=(0, 8))
        self.make_button(btn_row, "← Back", lambda: self.app.show_frame("DashboardScreen"),
                         style="secondary", width=10).pack(side="left")

    def on_show(self):
        self.amount_entry.delete(0, "end")
        self.note_entry.delete(0, "end")
        u = self.app.current_user
        if u:
            self.bal_lbl.config(text=f"Available: {self.app.format_balance(u.balance, u.currency)}")

    def _set_quick(self, amount: int):
        self.amount_entry.delete(0, "end")
        self.amount_entry.insert(0, str(amount))

    def _withdraw(self):
        try:
            amount = self.validate_amount(self.amount_entry.get())
        except ValueError as e:
            self.show_error(str(e))
            return

        note = self.note_entry.get().strip()
        u = self.app.current_user

        # Confirm
        if not self.ask_confirm(
            "Confirm Withdrawal",
            f"Withdraw {u.currency} {amount:,.2f} from account {u.acc_number}?"
        ):
            return

        try:
            txn = u.withdraw(amount, note)
        except ValueError as e:
            self.show_error(str(e))
            return

        self.app.data.save_accounts()
        self.app.frames["ReceiptScreen"].set_receipt(txn)
        self.show_success(f"Withdrew {u.currency} {amount:,.2f} successfully!")
        self.on_show()
        self.app.show_frame("ReceiptScreen")


# ─────────────────────────────────────────────────────────────────
# SCREEN 6 — TRANSFER
# ─────────────────────────────────────────────────────────────────

class TransferScreen(BaseScreen):

    def __init__(self, parent, app: ATMApp):
        super().__init__(parent, app)
        self._build_ui()

    def _build_ui(self):
        self.make_header("Transfer", "Send funds to another account")

        body = tk.Frame(self, bg=self.T["bg"])
        body.pack(fill="both", expand=True, padx=30, pady=20)

        form = self.make_card(body)
        form.pack(fill="x")
        inner = tk.Frame(form, bg=self.T["card"])
        inner.pack(padx=24, pady=20)

        self.bal_lbl = tk.Label(
            inner, text="", font=("Courier New", 10),
            bg=self.T["card"], fg=self.T["subtext"]
        )
        self.bal_lbl.pack(anchor="w", pady=(0, 12))

        self.make_label(inner, "Recipient Account Number", bold=True).pack(anchor="w")
        self.to_entry = self.make_entry(inner)
        self.to_entry.pack(fill="x", pady=(4, 10))

        self.make_label(inner, "Amount", bold=True).pack(anchor="w")
        self.amount_entry = self.make_entry(inner)
        self.amount_entry.pack(fill="x", pady=(4, 10))

        self.make_label(inner, "Note (optional)", bold=True).pack(anchor="w")
        self.note_entry = self.make_entry(inner)
        self.note_entry.pack(fill="x", pady=(4, 14))

        # Recipient name preview
        self.recipient_lbl = tk.Label(
            inner, text="", font=("Courier New", 9),
            bg=self.T["card"], fg=self.T["success"]
        )
        self.recipient_lbl.pack(anchor="w")
        self.to_entry.bind("<FocusOut>", self._lookup_recipient)

        tk.Frame(inner, bg=self.T["border"], height=1).pack(fill="x", pady=10)

        btn_row = tk.Frame(inner, bg=self.T["card"])
        btn_row.pack(fill="x", pady=4)
        self.make_button(btn_row, "✔ TRANSFER", self._transfer,
                         style="primary", width=16).pack(side="left", padx=(0, 8))
        self.make_button(btn_row, "← Back", lambda: self.app.show_frame("DashboardScreen"),
                         style="secondary", width=10).pack(side="left")

    def on_show(self):
        self.to_entry.delete(0, "end")
        self.amount_entry.delete(0, "end")
        self.note_entry.delete(0, "end")
        self.recipient_lbl.config(text="")
        u = self.app.current_user
        if u:
            self.bal_lbl.config(text=f"Available: {self.app.format_balance(u.balance, u.currency)}")

    def _lookup_recipient(self, event=None):
        """Show recipient name as user types account number."""
        acc_no = self.to_entry.get().strip()
        if acc_no:
            target = self.app.data.get_account(acc_no)
            if target:
                self.recipient_lbl.config(
                    text=f"✔ Recipient: {target.name}",
                    fg=self.T["success"]
                )
            else:
                self.recipient_lbl.config(
                    text="✘ Account not found",
                    fg=self.T["danger"]
                )

    def _transfer(self):
        to_acc_no = self.to_entry.get().strip()
        note      = self.note_entry.get().strip()
        u = self.app.current_user

        if not to_acc_no:
            self.show_error("Recipient account number is required")
            return
        if to_acc_no == u.acc_number:
            self.show_error("Cannot transfer to your own account")
            return

        target: Account = self.app.data.get_account(to_acc_no)
        if target is None:
            self.show_error(f"Account {to_acc_no} not found")
            return

        try:
            amount = self.validate_amount(self.amount_entry.get())
        except ValueError as e:
            self.show_error(str(e))
            return

        # ── Confirmation dialog ───────────────────────────────────
        if not self.ask_confirm(
            "Confirm Transfer",
            f"Transfer {u.currency} {amount:,.2f}\n"
            f"To: {target.name} ({to_acc_no})\n\nProceed?"
        ):
            return

        try:
            txn_out = u.transfer_out(amount, to_acc_no)
            target.transfer_in(amount, u.acc_number)
        except ValueError as e:
            self.show_error(str(e))
            return

        self.app.data.save_accounts()
        self.app.frames["ReceiptScreen"].set_receipt(txn_out)
        self.show_success(
            f"Transferred {u.currency} {amount:,.2f} to {target.name} successfully!"
        )
        self.on_show()
        self.app.show_frame("ReceiptScreen")


# ─────────────────────────────────────────────────────────────────
# SCREEN 7 — TRANSACTION HISTORY
# ─────────────────────────────────────────────────────────────────

class HistoryScreen(BaseScreen):

    def __init__(self, parent, app: ATMApp):
        super().__init__(parent, app)
        self._build_ui()

    def _build_ui(self):
        self.make_header("Transaction History", "Your last transactions")

        body = tk.Frame(self, bg=self.T["bg"])
        body.pack(fill="both", expand=True, padx=14, pady=12)

        # Filter row
        filter_row = tk.Frame(body, bg=self.T["bg"])
        filter_row.pack(fill="x", pady=(0, 8))
        self.make_label(filter_row, "Filter:", bold=True).pack(side="left", padx=(0, 8))
        self.filter_var = tk.StringVar(value="ALL")
        for option in ("ALL", "DEPOSIT", "WITHDRAWAL", "TRANSFER OUT", "TRANSFER IN"):
            tk.Radiobutton(
                filter_row,
                text=option,
                value=option,
                variable=self.filter_var,
                bg=self.T["bg"],
                fg=self.T["subtext"],
                selectcolor=self.T["entry_bg"],
                font=("Courier New", 7),
                activebackground=self.T["bg"],
                command=self._refresh_list,
            ).pack(side="left", padx=3)

        # Treeview table
        cols = ("Date/Time", "Type", "Amount", "Balance", "Note")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "ATM.Treeview",
            background=self.T["card"],
            fieldbackground=self.T["card"],
            foreground=self.T["text"],
            font=("Courier New", 8),
            rowheight=22,
        )
        style.configure(
            "ATM.Treeview.Heading",
            background=self.T["header_bg"],
            foreground=self.T["accent"],
            font=("Courier New", 8, "bold"),
        )
        self.tree = ttk.Treeview(
            body,
            columns=cols,
            show="headings",
            style="ATM.Treeview",
            height=14,
        )
        col_widths = (130, 100, 90, 90, 120)
        for col, w in zip(cols, col_widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")

        # Scrollbar
        sb = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Bottom buttons
        btn_row = tk.Frame(self, bg=self.T["bg"])
        btn_row.pack(fill="x", padx=14, pady=8)
        self.make_button(btn_row, "← Back", lambda: self.app.show_frame("DashboardScreen"),
                         style="secondary", width=14).pack(side="left")
        self.summary_lbl = tk.Label(
            btn_row, text="", font=("Courier New", 8),
            bg=self.T["bg"], fg=self.T["subtext"]
        )
        self.summary_lbl.pack(side="right")

    def on_show(self):
        self._refresh_list()

    def _refresh_list(self):
        """Populate treeview with filtered transactions."""
        # Clear existing rows
        for row in self.tree.get_children():
            self.tree.delete(row)

        u = self.app.current_user
        if u is None:
            return

        selected_filter = self.filter_var.get()
        txns = list(reversed(u.transactions))   # newest first

        # Apply filter using conditional
        if selected_filter != "ALL":
            txns = [t for t in txns if t.txn_type == selected_filter]

        # Populate rows using loop
        for i, txn in enumerate(txns):
            tag = "even" if i % 2 == 0 else "odd"
            color = self.T["success"] if "DEPOSIT" in txn.txn_type or "IN" in txn.txn_type \
                    else self.T["danger"]
            self.tree.insert(
                "", "end",
                values=(
                    txn.timestamp,
                    txn.txn_type,
                    f"{txn.currency} {txn.amount:,.2f}",
                    f"{txn.currency} {txn.balance_after:,.2f}",
                    txn.note or "—",
                ),
                tags=(tag,),
            )
            self.tree.tag_configure(tag, foreground=self.T["text"])

        self.summary_lbl.config(text=f"Showing {len(txns)} transaction(s)")


# ─────────────────────────────────────────────────────────────────
# SCREEN 8 — ACCOUNT INFO
# ─────────────────────────────────────────────────────────────────

class AccountInfoScreen(BaseScreen):

    def __init__(self, parent, app: ATMApp):
        super().__init__(parent, app)
        self._build_ui()

    def _build_ui(self):
        self.make_header("Account Info", "Your profile summary")

        body = tk.Frame(self, bg=self.T["bg"])
        body.pack(fill="both", expand=True, padx=26, pady=16)

        # Info card
        card = self.make_card(body)
        card.pack(fill="x", pady=(0, 14))
        self.info_inner = tk.Frame(card, bg=self.T["card"])
        self.info_inner.pack(padx=22, pady=18, fill="x")

        # Dynamic labels
        self.labels = {}
        rows = (
            ("Account Number", "acc"),
            ("Account Holder", "name"),
            ("Account Type",   "type"),
            ("Balance",        "bal"),
            ("Currency",       "cur"),
            ("Total Txns",     "txns"),
            ("Account Status", "status"),
        )
        for i, (label, key) in enumerate(rows):
            row = tk.Frame(self.info_inner, bg=self.T["card"])
            row.pack(fill="x", pady=3)
            tk.Label(
                row, text=f"{label}:",
                font=("Courier New", 9),
                bg=self.T["card"], fg=self.T["subtext"],
                width=18, anchor="w"
            ).pack(side="left")
            val_lbl = tk.Label(
                row, text="",
                font=("Courier New", 9, "bold"),
                bg=self.T["card"], fg=self.T["text"],
                anchor="w"
            )
            val_lbl.pack(side="left", fill="x", expand=True)
            self.labels[key] = val_lbl

            # Divider between rows
            if i < len(rows) - 1:
                tk.Frame(self.info_inner, bg=self.T["border"], height=1).pack(fill="x")

        # Mini-statement section
        ms_card = self.make_card(body)
        ms_card.pack(fill="x")
        ms_inner = tk.Frame(ms_card, bg=self.T["card"])
        ms_inner.pack(padx=22, pady=14, fill="x")
        self.make_label(ms_inner, "Mini Statement (last 5)", bold=True).pack(anchor="w", pady=(0, 6))
        self.mini_text = tk.Text(
            ms_inner,
            font=("Courier New", 8),
            bg=self.T["entry_bg"],
            fg=self.T["text"],
            height=7,
            relief="flat",
            state="disabled",
        )
        self.mini_text.pack(fill="x")

        self.make_button(body, "← Back to Dashboard",
                         lambda: self.app.show_frame("DashboardScreen"),
                         style="secondary", width=24).pack(pady=12)

    def on_show(self):
        u = self.app.current_user
        if u is None:
            return

        # Update info labels
        status_color = self.T["success"] if not u.is_locked else self.T["danger"]
        status_text  = "✔ Active" if not u.is_locked else "✘ Locked"

        self.labels["acc"].config(text=u.acc_number)
        self.labels["name"].config(text=u.name)
        self.labels["type"].config(text="Admin" if u.is_admin else "Standard")
        self.labels["bal"].config(
            text=self.app.format_balance(u.balance, u.currency),
            fg=self.T["accent"]
        )
        self.labels["cur"].config(text=f"{u.currency} — {CURRENCIES[u.currency][0]}")
        self.labels["txns"].config(text=str(len(u.transactions)))
        self.labels["status"].config(text=status_text, fg=status_color)

        # Mini-statement: last 5 transactions
        self.mini_text.config(state="normal")
        self.mini_text.delete("1.0", "end")
        mini = u.mini_statement()[-5:]
        if mini:
            for t in reversed(mini):
                line = f"{t.timestamp[:16]}  {t.txn_type:<14} {t.currency} {t.amount:>10,.2f}\n"
                self.mini_text.insert("end", line)
        else:
            self.mini_text.insert("end", "  No transactions yet.")
        self.mini_text.config(state="disabled")


# ─────────────────────────────────────────────────────────────────
# SCREEN 9 — CHANGE PIN
# ─────────────────────────────────────────────────────────────────

class ChangePinScreen(BaseScreen):

    def __init__(self, parent, app: ATMApp):
        super().__init__(parent, app)
        self._build_ui()

    def _build_ui(self):
        self.make_header("Change PIN", "Update your secret PIN")

        body = tk.Frame(self, bg=self.T["bg"])
        body.pack(fill="both", expand=True, padx=30, pady=20)

        form = self.make_card(body)
        form.pack(fill="x")
        inner = tk.Frame(form, bg=self.T["card"])
        inner.pack(padx=24, pady=22)

        fields = (
            ("Current PIN",     "old_pin",  "●"),
            ("New PIN",         "new_pin",  "●"),
            ("Confirm New PIN", "cnew_pin", "●"),
        )
        for label, attr, show in fields:
            self.make_label(inner, label, bold=True).pack(anchor="w")
            e = self.make_entry(inner, show=show)
            e.pack(fill="x", pady=(4, 12))
            setattr(self, attr, e)

        # PIN requirements hint
        tk.Label(
            inner,
            text="PIN must be 4 numeric digits",
            font=("Courier New", 8),
            bg=self.T["card"],
            fg=self.T["subtext"],
        ).pack(anchor="w", pady=(0, 12))

        tk.Frame(inner, bg=self.T["border"], height=1).pack(fill="x", pady=4)

        btn_row = tk.Frame(inner, bg=self.T["card"])
        btn_row.pack(fill="x", pady=10)
        self.make_button(btn_row, "✔ UPDATE PIN", self._change_pin,
                         style="warning", width=16).pack(side="left", padx=(0, 8))
        self.make_button(btn_row, "← Back", lambda: self.app.show_frame("DashboardScreen"),
                         style="secondary", width=10).pack(side="left")

    def on_show(self):
        for attr in ("old_pin", "new_pin", "cnew_pin"):
            getattr(self, attr).delete(0, "end")

    def _change_pin(self):
        old  = self.old_pin.get().strip()
        new  = self.new_pin.get().strip()
        cnew = self.cnew_pin.get().strip()

        # Validation tuple
        checks = (
            (not old,           "Current PIN is required"),
            (not new,           "New PIN is required"),
            (not new.isdigit(), "New PIN must be digits only"),
            (len(new) != 4,     "New PIN must be exactly 4 digits"),
            (new != cnew,       "New PINs do not match"),
            (new == old,        "New PIN must differ from current PIN"),
        )
        for condition, msg in checks:
            if condition:
                self.show_error(msg)
                return

        u = self.app.current_user
        if u.change_pin(old, new):
            self.app.data.save_accounts()
            self.show_success("PIN changed successfully!")
            self.app.show_frame("DashboardScreen")
        else:
            self.show_error("Current PIN is incorrect")


# ─────────────────────────────────────────────────────────────────
# SCREEN 10 — ADMIN PANEL
# ─────────────────────────────────────────────────────────────────

class AdminPanelScreen(BaseScreen):

    def __init__(self, parent, app: ATMApp):
        super().__init__(parent, app)
        self._build_ui()

    def _build_ui(self):
        self.make_header("Admin Panel", "Manage accounts and system")

        body = tk.Frame(self, bg=self.T["bg"])
        body.pack(fill="both", expand=True, padx=14, pady=12)

        # Top controls
        ctrl = tk.Frame(body, bg=self.T["bg"])
        ctrl.pack(fill="x", pady=(0, 8))
        self.make_button(ctrl, "⟳ Refresh", self.on_show,
                         style="primary", width=12).pack(side="left", padx=(0, 6))
        self.make_button(ctrl, "🔓 Unlock Account", self._unlock_account,
                         style="warning", width=16).pack(side="left", padx=(0, 6))
        self.make_button(ctrl, "+ New Account", self._new_account,
                         style="success", width=14).pack(side="left")

        # Accounts table
        cols = ("Acc #", "Name", "Balance", "Currency", "Status", "Txns")
        style = ttk.Style()
        style.configure(
            "Admin.Treeview",
            background=self.T["card"],
            fieldbackground=self.T["card"],
            foreground=self.T["text"],
            font=("Courier New", 8),
            rowheight=22,
        )
        style.configure(
            "Admin.Treeview.Heading",
            background=self.T["header_bg"],
            foreground=self.T["accent"],
            font=("Courier New", 8, "bold"),
        )
        self.tree = ttk.Treeview(
            body, columns=cols, show="headings",
            style="Admin.Treeview", height=16,
        )
        widths = (60, 140, 100, 70, 70, 50)
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")

        sb = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self.make_button(self, "← Back to Dashboard",
                         lambda: self.app.show_frame("DashboardScreen"),
                         style="secondary", width=24).pack(pady=8)

    def on_show(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Loop through all accounts dictionary
        for acc_no, acc in self.app.data.accounts.items():
            status = "LOCKED" if acc.is_locked else ("ADMIN" if acc.is_admin else "Active")
            self.tree.insert(
                "", "end",
                values=(
                    acc_no,
                    acc.name,
                    f"{acc.currency} {acc.balance:,.2f}",
                    acc.currency,
                    status,
                    len(acc.transactions),
                ),
            )

    def _unlock_account(self):
        acc_no = simpledialog.askstring("Unlock Account", "Enter account number to unlock:")
        if not acc_no:
            return
        acc = self.app.data.get_account(acc_no.strip())
        if acc is None:
            self.show_error(f"Account {acc_no} not found")
            return
        acc.is_locked = False
        acc.failed_attempts = 0
        self.app.data.save_accounts()
        self.show_success(f"Account {acc_no} unlocked successfully!")
        self.on_show()

    def _new_account(self):
        self.app.show_frame("CreateAccountScreen")


# ─────────────────────────────────────────────────────────────────
# SCREEN 11 — RECEIPT
# ─────────────────────────────────────────────────────────────────

class ReceiptScreen(BaseScreen):

    def __init__(self, parent, app: ATMApp):
        super().__init__(parent, app)
        self._txn: Transaction = None
        self._build_ui()

    def _build_ui(self):
        self.make_header("Transaction Receipt", "Your transaction summary")

        body = tk.Frame(self, bg=self.T["bg"])
        body.pack(fill="both", expand=True, padx=30, pady=20)

        card = self.make_card(body)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=self.T["card"])
        inner.pack(padx=24, pady=20, fill="x")

        self.make_label(inner, "═" * 36, color=self.T["border"]).pack()
        self.make_label(inner, "  NEXUS ATM  —  RECEIPT",
                        size=11, bold=True, color=self.T["accent"]).pack(pady=4)
        self.make_label(inner, "═" * 36, color=self.T["border"]).pack()

        # Dynamic fields (dictionary)
        self.receipt_fields: dict = {}
        field_keys = ("Date", "Type", "Amount", "New Balance", "Note")
        for key in field_keys:
            row = tk.Frame(inner, bg=self.T["card"])
            row.pack(fill="x", pady=3)
            tk.Label(
                row, text=f"  {key:<14}:",
                font=("Courier New", 9),
                bg=self.T["card"], fg=self.T["subtext"],
            ).pack(side="left")
            val = tk.Label(
                row, text="",
                font=("Courier New", 9, "bold"),
                bg=self.T["card"], fg=self.T["text"],
            )
            val.pack(side="left")
            self.receipt_fields[key] = val

        self.make_label(inner, "═" * 36, color=self.T["border"]).pack(pady=6)
        self.make_label(inner, "Thank you for using NEXUS ATM",
                        size=9, color=self.T["subtext"]).pack()
        self.make_label(inner, "═" * 36, color=self.T["border"]).pack()

        btn_row = tk.Frame(body, bg=self.T["bg"])
        btn_row.pack(pady=16)
        self.make_button(btn_row, "⌂ Back to Dashboard",
                         lambda: self.app.show_frame("DashboardScreen"),
                         style="primary", width=20).pack(side="left", padx=(0, 8))
        self.make_button(btn_row, "💳 Another Transaction",
                         lambda: self.app.show_frame("DashboardScreen"),
                         style="secondary", width=20).pack(side="left")

    def set_receipt(self, txn: Transaction):
        """Populate receipt with transaction data."""
        self._txn = txn

    def on_show(self):
        if self._txn is None:
            return
        t = self._txn
        # Conditional formatting for amount color
        color = self.T["success"] if "DEPOSIT" in t.txn_type or "IN" in t.txn_type \
                else self.T["danger"]

        self.receipt_fields["Date"].config(text=t.timestamp)
        self.receipt_fields["Type"].config(text=t.txn_type)
        self.receipt_fields["Amount"].config(
            text=f"{t.currency} {t.amount:,.2f}", fg=color
        )
        self.receipt_fields["New Balance"].config(
            text=f"{t.currency} {t.balance_after:,.2f}",
            fg=self.T["accent"]
        )
        self.receipt_fields["Note"].config(text=t.note or "—")


# ─────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = ATMApp()
    app.mainloop()