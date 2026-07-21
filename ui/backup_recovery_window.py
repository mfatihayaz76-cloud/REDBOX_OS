from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from database.backup_recovery_engine import (
    geri_yuklemeyi_hazirla,
    manuel_yedek_olustur,
    veritabani_durumunu_getir,
    yedegi_dogrula,
    yedekleme_gecmisini_getir,
    yedekleme_politikasini_getir,
    yedekleme_politikasini_guncelle,
)
from database.db import (
    BACKUP_DIR,
    DB_PATH,
    RECOVERY_DIR,
    get_connection,
)


class BackupRecoveryWindow(ctk.CTkToplevel):

    def __init__(self, app, initial_action=None):
        super().__init__(app)
        self.app = app
        self.initial_action = initial_action
        self.title(
            "REDBOX OS — Yedekleme ve Kurtarma Merkezi"
        )
        self.geometry("1080x820")
        self.minsize(900, 680)
        self.transient(app)
        self.grab_set()
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.policy_active = ctk.BooleanVar(value=True)
        self.frequency_value = ctk.StringVar(value="24")
        self.retention_value = ctk.StringVar(value="14")
        self.status_value = ctk.StringVar(
            value="Durum kontrol ediliyor..."
        )
        self.schedule_value = ctk.StringVar(value="-")

        self._build()
        self._refresh()

        self.after(150, self.focus_force)

    def _build(self):
        main = ctk.CTkScrollableFrame(
            self,
            corner_radius=14,
        )
        main.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=24,
            pady=24,
        )
        main.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            main,
            text="YEDEKLEME VE KURTARMA MERKEZİ",
            font=ctk.CTkFont(
                size=30,
                weight="bold",
            ),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=(18, 4),
        )

        ctk.CTkLabel(
            main,
            text=(
                "Doğrulanmış yedek oluşturun, otomatik "
                "yedek politikasını yönetin ve kontrollü "
                "geri yükleme hazırlayın."
            ),
            text_color="#A3A3A3",
            wraplength=900,
            justify="left",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 18),
        )

        self._status_panel(main, 2)
        self._policy_panel(main, 3)
        self._operations_panel(main, 4)
        self._history_panel(main, 5)

        ctk.CTkButton(
            main,
            text="KAPAT",
            height=44,
            fg_color="#525252",
            command=self.destroy,
        ).grid(
            row=6,
            column=0,
            sticky="ew",
            padx=20,
            pady=(12, 22),
        )

    def _panel(self, master, row, title):
        panel = ctk.CTkFrame(master)
        panel.grid(
            row=row,
            column=0,
            sticky="ew",
            padx=20,
            pady=8,
        )
        panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            panel,
            text=title,
            font=ctk.CTkFont(
                size=19,
                weight="bold",
            ),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=18,
            pady=(16, 10),
        )
        return panel

    def _status_panel(self, master, row):
        panel = self._panel(
            master,
            row,
            "CANLI VERİTABANI DURUMU",
        )

        ctk.CTkLabel(
            panel,
            textvariable=self.status_value,
            justify="left",
            anchor="w",
            wraplength=880,
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 8),
        )

        ctk.CTkLabel(
            panel,
            textvariable=self.schedule_value,
            text_color="#60A5FA",
            justify="left",
            anchor="w",
            wraplength=880,
        ).grid(
            row=2,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 16),
        )

    def _policy_panel(self, master, row):
        panel = self._panel(
            master,
            row,
            "OTOMATİK YEDEKLEME POLİTİKASI",
        )
        panel.grid_columnconfigure((0, 1, 2), weight=1)

        self.active_switch = ctk.CTkSwitch(
            panel,
            text="Otomatik yedekleme aktif",
            variable=self.policy_active,
            onvalue=True,
            offvalue=False,
        )
        self.active_switch.grid(
            row=1,
            column=0,
            sticky="w",
            padx=18,
            pady=10,
        )

        frequency_frame = ctk.CTkFrame(
            panel,
            fg_color="transparent",
        )
        frequency_frame.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=8,
            pady=10,
        )
        ctk.CTkLabel(
            frequency_frame,
            text="Sıklık (saat)",
        ).pack(anchor="w")
        self.frequency_entry = ctk.CTkEntry(
            frequency_frame,
            textvariable=self.frequency_value,
        )
        self.frequency_entry.pack(
            fill="x",
            pady=(4, 0),
        )

        retention_frame = ctk.CTkFrame(
            panel,
            fg_color="transparent",
        )
        retention_frame.grid(
            row=1,
            column=2,
            sticky="ew",
            padx=(8, 18),
            pady=10,
        )
        ctk.CTkLabel(
            retention_frame,
            text="Saklanacak otomatik yedek",
        ).pack(anchor="w")
        self.retention_entry = ctk.CTkEntry(
            retention_frame,
            textvariable=self.retention_value,
        )
        self.retention_entry.pack(
            fill="x",
            pady=(4, 0),
        )

        ctk.CTkButton(
            panel,
            text="POLİTİKAYI KAYDET",
            height=42,
            command=self._save_policy,
        ).grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=18,
            pady=(8, 18),
        )

    def _operations_panel(self, master, row):
        panel = self._panel(
            master,
            row,
            "YEDEKLEME VE GERİ YÜKLEME İŞLEMLERİ",
        )
        panel.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            panel,
            text="DOĞRULANMIŞ MANUEL YEDEK OLUŞTUR",
            height=46,
            command=self._manual_backup,
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(18, 6),
            pady=(6, 18),
        )

        ctk.CTkButton(
            panel,
            text="KONTROLLÜ GERİ YÜKLEME HAZIRLA",
            height=46,
            fg_color="#B45309",
            command=self._prepare_restore,
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(6, 18),
            pady=(6, 18),
        )

    def _history_panel(self, master, row):
        panel = self._panel(
            master,
            row,
            "SON YEDEKLER",
        )

        self.history_text = ctk.CTkTextbox(
            panel,
            height=180,
            wrap="none",
        )
        self.history_text.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 18),
        )
        self.history_text.configure(state="disabled")

    def _connection(self):
        return get_connection()

    def _refresh(self):
        connection = self._connection()

        try:
            policy = yedekleme_politikasini_getir(
                connection
            )
            history = yedekleme_gecmisini_getir(
                connection,
                limit=20,
            )
        finally:
            connection.close()

        status = veritabani_durumunu_getir(DB_PATH)

        self.policy_active.set(policy["aktif"])
        self.frequency_value.set(
            str(policy["siklik_saat"])
        )
        self.retention_value.set(
            str(policy["saklama_adedi"])
        )

        self.status_value.set(
            "Bütünlük: "
            f"{status['integrity'].upper()}  |  "
            "FK ihlali: "
            f"{status['foreign_key_violations']}  |  "
            "Şema: "
            f"{status['schema_version']}  |  "
            "Boyut: "
            f"{status['size_bytes'] / 1024:.1f} KB"
        )

        self.schedule_value.set(
            "Son otomatik yedek: "
            f"{policy['son_otomatik_yedek_zamani'] or '-'}  |  "
            "Sonraki otomatik yedek: "
            f"{policy['sonraki_otomatik_yedek_zamani'] or 'ilk başlangıçta'}"
        )

        lines = []

        for item in history:
            lines.append(
                f"{item['olusturma_zamani']} | "
                f"{item['yedek_turu']} | "
                f"{item['durum']} | "
                f"{item['dosya_adi']} | "
                f"SHA {item['database_sha256'][:12]}..."
            )

        if not lines:
            lines.append(
                "Henüz kayıtlı yedek bulunmuyor."
            )

        self.history_text.configure(state="normal")
        self.history_text.delete("1.0", "end")
        self.history_text.insert(
            "1.0",
            "\n".join(lines),
        )
        self.history_text.configure(state="disabled")

    def _save_policy(self):
        confirmation = messagebox.askyesno(
            "Yedekleme Politikası",
            (
                "Otomatik yedekleme politikası "
                "güncellenecek. Devam edilsin mi?"
            ),
            parent=self,
        )

        if not confirmation:
            return

        connection = self._connection()

        try:
            yedekleme_politikasini_guncelle(
                connection,
                aktif=self.policy_active.get(),
                siklik_saat=self.frequency_value.get(),
                saklama_adedi=self.retention_value.get(),
                kullanici=self.app.current_user,
                oturum_id=self.app.current_user.get(
                    "oturum_id"
                ),
            )
        except Exception as exc:
            messagebox.showerror(
                "Yedekleme Politikası",
                str(exc),
                parent=self,
            )
            return
        finally:
            connection.close()

        self._refresh()
        messagebox.showinfo(
            "Yedekleme Politikası",
            "Politika güvenli şekilde güncellendi.",
            parent=self,
        )

    def _manual_backup(self):
        confirmation = messagebox.askyesno(
            "Manuel Veritabanı Yedeği",
            (
                "Canlı veritabanının doğrulanmış manuel "
                "yedeği oluşturulsun mu?"
            ),
            parent=self,
        )

        if not confirmation:
            return

        connection = self._connection()

        try:
            result = manuel_yedek_olustur(
                connection,
                DB_PATH,
                BACKUP_DIR,
                kullanici=self.app.current_user,
                oturum_id=self.app.current_user.get(
                    "oturum_id"
                ),
            )
        except Exception as exc:
            messagebox.showerror(
                "Manuel Veritabanı Yedeği",
                str(exc),
                parent=self,
            )
            return
        finally:
            connection.close()

        self._refresh()
        messagebox.showinfo(
            "Manuel Veritabanı Yedeği",
            (
                "Yedek oluşturuldu ve doğrulandı.\n\n"
                f"Dosya: {Path(result['backup_path']).name}\n"
                f"SHA-256: {result['sha256']}"
            ),
            parent=self,
        )

    def _prepare_restore(self):
        selected = filedialog.askopenfilename(
            title="REDBOX OS Doğrulanmış Yedeği Seç",
            initialdir=str(BACKUP_DIR),
            filetypes=[
                ("REDBOX OS Database", "*.db"),
            ],
            parent=self,
        )

        if not selected:
            return

        selected_path = Path(selected)
        manifest_path = selected_path.with_suffix(
            ".manifest.json"
        )

        try:
            validation = yedegi_dogrula(
                selected_path,
                manifest_path,
            )
        except Exception as exc:
            messagebox.showerror(
                "Geri Yükleme Doğrulaması",
                str(exc),
                parent=self,
            )
            return

        confirmation = messagebox.askyesno(
            "Kontrollü Geri Yükleme",
            (
                "Seçilen doğrulanmış yedek bir sonraki "
                "başlangıçta geri yüklenecek.\n\n"
                f"Dosya: {selected_path.name}\n"
                f"Şema: {validation['schema_version']}\n"
                f"SHA-256: {validation['sha256']}\n\n"
                "Önce canlı veritabanının emniyet yedeği "
                "alınacaktır. Devam edilsin mi?"
            ),
            parent=self,
        )

        if not confirmation:
            return

        try:
            result = geri_yuklemeyi_hazirla(
                DB_PATH,
                selected_path,
                manifest_path,
                BACKUP_DIR,
                RECOVERY_DIR,
                kullanici=self.app.current_user,
                oturum_id=self.app.current_user.get(
                    "oturum_id"
                ),
            )
        except Exception as exc:
            messagebox.showerror(
                "Kontrollü Geri Yükleme",
                str(exc),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Kontrollü Geri Yükleme",
            (
                "Geri yükleme güvenli biçimde hazırlandı.\n\n"
                "Uygulamayı kapatıp yeniden açın. İşlem, "
                "veritabanı bağlantıları açılmadan önce "
                "uygulanacaktır.\n\n"
                "Emniyet yedeği: "
                f"{Path(result['safety_backup_path']).name}"
            ),
            parent=self,
        )
