import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from database.db import get_connection
from ui.login import PBKDF2_ITERATIONS, _parola_hash


class SystemPage:

    def __init__(self, app):
        self.app = app

    def create(self):

        self.app.show_page(
            "SİSTEM",
            "REDBOX OS Sistem Yönetimi"
        )

        frame = ctk.CTkFrame(self.app.content)
        frame.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=25
        )

        ctk.CTkLabel(
            frame,
            text="SİSTEM YÖNETİMİ",
            font=("Arial", 24, "bold")
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 10)
        )

        ctk.CTkButton(
            frame,
            text="VERİTABANINI YEDEKLE",
            width=260,
            height=42,
            command=self.backup_database
        ).pack(
            anchor="w",
            padx=20,
            pady=(10,5)
        )

        ctk.CTkButton(
            frame,
            text="VERİTABANINI GERİ YÜKLE",
            width=260,
            height=42,
            command=self.restore_database
        ).pack(
            anchor="w",
            padx=20,
            pady=5
        )


        ctk.CTkButton(
            frame,
            text="FİRMA BİLGİLERİ",
            width=260,
            height=42,
            command=self.company_info
        ).pack(
            anchor="w",
            padx=20,
            pady=5
        )

        if self._hesap_yonetim_yetkisi():
            ctk.CTkButton(
                frame,
                text="KULLANICI HESAPLARI",
                width=260,
                height=42,
                command=self.account_management,
            ).pack(
                anchor="w",
                padx=20,
                pady=5,
            )

        ctk.CTkButton(
            frame,
            text="AYARLAR",
            width=260,
            height=42,
            command=self.settings
        ).pack(
            anchor="w",
            padx=20,
            pady=5
        )

    def _hesap_yonetim_yetkisi(self):
        user = getattr(self.app, "current_user", {})
        return (
            bool(user.get("yonetici"))
            and user.get("ad_soyad") == "Fatih Ayaz"
            and user.get("kullanici_adi", "").lower() == "fatih"
        )

    def account_management(self):
        if not self._hesap_yonetim_yetkisi():
            messagebox.showerror(
                "Yetkisiz Erişim",
                "Kullanıcı hesaplarını yalnız Fatih Ayaz yönetebilir.",
            )
            return

        personeller = self._yonetilebilir_personeller()

        if not personeller:
            messagebox.showinfo(
                "Kullanıcı Hesapları",
                "Yönetilebilecek başka aktif personel bulunmuyor.",
            )
            return

        self.account_window = ctk.CTkToplevel(self.app)
        self.account_window.title("REDBOX OS — Kullanıcı Hesapları")
        self.account_window.geometry("560x650")
        self.account_window.resizable(False, False)
        self.account_window.transient(self.app)
        self.account_window.grab_set()
        self.account_window.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.account_window,
            text="KULLANICI HESAPLARI",
            font=("Arial", 25, "bold"),
        ).grid(
            row=0,
            column=0,
            padx=40,
            pady=(35, 5),
        )

        ctk.CTkLabel(
            self.account_window,
            text=(
                "Personel hesabı oluşturun veya mevcut "
                "hesabın parolasını yenileyin."
            ),
            font=("Arial", 12),
            text_color="#9CA3AF",
        ).grid(
            row=1,
            column=0,
            padx=40,
            pady=(0, 25),
        )

        form = ctk.CTkFrame(
            self.account_window,
            corner_radius=14,
        )
        form.grid(
            row=2,
            column=0,
            padx=45,
            pady=10,
            sticky="ew",
        )
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            form,
            text="Personel",
            font=("Arial", 12, "bold"),
            anchor="w",
        ).grid(
            row=0,
            column=0,
            padx=25,
            pady=(25, 5),
            sticky="ew",
        )

        self.account_personel = ctk.CTkOptionMenu(
            form,
            values=personeller,
            height=42,
            command=self._account_personel_secildi,
        )
        self.account_personel.grid(
            row=1,
            column=0,
            padx=25,
            pady=(0, 12),
            sticky="ew",
        )

        ctk.CTkLabel(
            form,
            text="Kullanıcı Adı",
            font=("Arial", 12, "bold"),
            anchor="w",
        ).grid(
            row=2,
            column=0,
            padx=25,
            pady=(5, 5),
            sticky="ew",
        )

        self.account_username = ctk.CTkEntry(
            form,
            placeholder_text="Örnek: eda",
            height=42,
        )
        self.account_username.grid(
            row=3,
            column=0,
            padx=25,
            pady=(0, 12),
            sticky="ew",
        )

        ctk.CTkLabel(
            form,
            text="Yeni Parola",
            font=("Arial", 12, "bold"),
            anchor="w",
        ).grid(
            row=4,
            column=0,
            padx=25,
            pady=(5, 5),
            sticky="ew",
        )

        self.account_password = ctk.CTkEntry(
            form,
            placeholder_text="En az 8 karakter",
            show="●",
            height=42,
        )
        self.account_password.grid(
            row=5,
            column=0,
            padx=25,
            pady=(0, 12),
            sticky="ew",
        )

        self.account_password_repeat = ctk.CTkEntry(
            form,
            placeholder_text="Yeni parola tekrar",
            show="●",
            height=42,
        )
        self.account_password_repeat.grid(
            row=6,
            column=0,
            padx=25,
            pady=(0, 12),
            sticky="ew",
        )

        self.account_status = ctk.CTkLabel(
            form,
            text="",
            font=("Arial", 12, "bold"),
            text_color="#F59E0B",
        )
        self.account_status.grid(
            row=7,
            column=0,
            padx=25,
            pady=(5, 5),
        )

        self.account_save_button = ctk.CTkButton(
            form,
            text="HESABI KAYDET",
            height=46,
            font=("Arial", 13, "bold"),
            command=self._account_save,
        )
        self.account_save_button.grid(
            row=8,
            column=0,
            padx=25,
            pady=(12, 25),
            sticky="ew",
        )

        self._account_personel_secildi(personeller[0])
        self.account_window.after(
            150,
            self.account_window.focus_force,
        )

    def _yonetilebilir_personeller(self):
        conn = get_connection()
        try:
            rows = conn.execute("""
                SELECT ad_soyad
                FROM personeller
                WHERE aktif = 1
                  AND ad_soyad <> 'Fatih Ayaz'
                ORDER BY ad_soyad
            """).fetchall()
            return [row["ad_soyad"] for row in rows]
        finally:
            conn.close()

    def _account_personel_secildi(self, personel):
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT
                    kh.kullanici_adi,
                    kh.aktif
                FROM kullanici_hesaplari kh
                JOIN personeller p
                  ON p.id = kh.personel_id
                WHERE p.ad_soyad = ?
                LIMIT 1
            """, (personel,)).fetchone()
        finally:
            conn.close()

        self.account_username.delete(0, "end")
        self.account_password.delete(0, "end")
        self.account_password_repeat.delete(0, "end")

        if row is None:
            suggested = personel.split()[0].lower()
            self.account_username.insert(0, suggested)
            self.account_status.configure(
                text="YENİ HESAP",
                text_color="#22C55E",
            )
            self.account_save_button.configure(
                text="HESABI OLUŞTUR",
            )
        else:
            self.account_username.insert(
                0,
                row["kullanici_adi"],
            )
            self.account_status.configure(
                text=(
                    "AKTİF HESAP"
                    if int(row["aktif"]) == 1
                    else "PASİF HESAP"
                ),
                text_color="#F59E0B",
            )
            self.account_save_button.configure(
                text="PAROLAYI VE HESABI GÜNCELLE",
            )

    def _account_save(self):
        if not self._hesap_yonetim_yetkisi():
            messagebox.showerror(
                "Yetkisiz Erişim",
                "Bu işlem için yönetici yetkisi gerekiyor.",
            )
            return

        personel = self.account_personel.get().strip()
        username = self.account_username.get().strip()
        password = self.account_password.get()
        password_repeat = self.account_password_repeat.get()

        if len(username) < 3:
            messagebox.showwarning(
                "Eksik Bilgi",
                "Kullanıcı adı en az 3 karakter olmalıdır.",
            )
            return

        if len(password) < 8:
            messagebox.showwarning(
                "Zayıf Parola",
                "Parola en az 8 karakter olmalıdır.",
            )
            return

        if password != password_repeat:
            messagebox.showwarning(
                "Parola Hatası",
                "Parolalar birbiriyle aynı değil.",
            )
            return

        salt = os.urandom(16).hex()
        password_hash = _parola_hash(
            password,
            salt,
            PBKDF2_ITERATIONS,
        )
        now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        conn = get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")

            personel_row = conn.execute("""
                SELECT id
                FROM personeller
                WHERE ad_soyad = ?
                  AND aktif = 1
            """, (personel,)).fetchone()

            if personel_row is None:
                raise RuntimeError(
                    "Seçilen aktif personel bulunamadı."
                )

            existing = conn.execute("""
                SELECT id
                FROM kullanici_hesaplari
                WHERE personel_id = ?
            """, (personel_row["id"],)).fetchone()

            if existing is None:
                conn.execute("""
                    INSERT INTO kullanici_hesaplari (
                        personel_id,
                        kullanici_adi,
                        parola_hash,
                        parola_tuzu,
                        iterasyon,
                        yonetici,
                        aktif,
                        kayit_zamani
                    )
                    VALUES (?, ?, ?, ?, ?, 0, 1, ?)
                """, (
                    personel_row["id"],
                    username,
                    password_hash,
                    salt,
                    PBKDF2_ITERATIONS,
                    now,
                ))
                action = "oluşturuldu"
            else:
                conn.execute("""
                    UPDATE kullanici_hesaplari
                    SET kullanici_adi = ?,
                        parola_hash = ?,
                        parola_tuzu = ?,
                        iterasyon = ?,
                        aktif = 1
                    WHERE id = ?
                """, (
                    username,
                    password_hash,
                    salt,
                    PBKDF2_ITERATIONS,
                    existing["id"],
                ))
                action = "güncellendi"

            conn.commit()

        except (sqlite3.Error, RuntimeError) as exc:
            conn.rollback()
            messagebox.showerror(
                "Hesap Kaydetme Hatası",
                str(exc),
            )
            return
        finally:
            conn.close()

        messagebox.showinfo(
            "Kullanıcı Hesabı",
            f"{personel} hesabı güvenli şekilde {action}.",
        )
        self._account_personel_secildi(personel)

    def backup_database(self):

        kaynak = Path("database/redbox_os.db")

        if not kaynak.exists():
            messagebox.showerror(
                "Hata",
                "Veritabanı bulunamadı."
            )
            return

        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)

        hedef = backup_dir / (
            "redbox_os_" +
            datetime.now().strftime("%Y%m%d_%H%M%S") +
            ".db"
        )

        shutil.copy2(kaynak, hedef)

        messagebox.showinfo(
            "Başarılı",
            f"Yedek oluşturuldu.\n\n{hedef.name}"
        )


    def restore_database(self):
        from pathlib import Path
        from tkinter import filedialog
        from tkinter import messagebox
        import shutil

        secilen = filedialog.askopenfilename(
            title="REDBOX OS Yedek Dosyası Seç",
            initialdir="backups",
            filetypes=[
                ("SQLite Database", "*.db"),
                ("Tüm Dosyalar", "*.*")
            ]
        )

        if not secilen:
            return

        hedef = Path("database/redbox_os.db")

        try:
            shutil.copy2(secilen, hedef)

            messagebox.showinfo(
                "Başarılı",
                "Veritabanı başarıyla geri yüklendi.\n\nProgramı yeniden başlatınız."
            )

        except Exception as e:
            messagebox.showerror(
                "Hata",
                str(e)
            )


    def company_info(self):
        from tkinter import messagebox

        messagebox.showinfo(
            "REDBOX GIDA",
            "Firma Bilgileri modülü Sprint 21F içerisinde tamamlanacaktır."
        )


    def settings(self):
        from tkinter import messagebox

        messagebox.showinfo(
            "Ayarlar",
            "Ayarlar modülü Sprint 21G içerisinde tamamlanacaktır."
        )
