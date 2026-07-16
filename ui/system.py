import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

import customtkinter as ctk

from database.db import get_connection
from database.audit_engine import (
    denetim_kaydi_ekle,
    denetim_kayitlarini_getir,
)
from database.migrations import run_migrations
from ui.login import PBKDF2_ITERATIONS, _parola_hash


class SystemPage:

    def __init__(self, app):
        self.app = app

    def create(self):
        self.app.show_page(
            "SİSTEM",
            "REDBOX OS sistem yönetimi ve güvenli bakım merkezi"
        )

        ana = ctk.CTkScrollableFrame(
            self.app.content,
            corner_radius=14,
        )
        ana.pack(
            fill="both",
            expand=True,
            padx=40,
            pady=(0, 30),
        )

        stats = self._system_stats()

        baslik = ctk.CTkFrame(
            ana,
            fg_color="transparent",
        )
        baslik.pack(
            fill="x",
            padx=20,
            pady=(20, 12),
        )

        ctk.CTkLabel(
            baslik,
            text="SİSTEM YÖNETİM MERKEZİ",
            font=("Arial", 22, "bold"),
        ).pack(side="left")

        ctk.CTkLabel(
            baslik,
            text=(
                f'Aktif kullanıcı: '
                f'{getattr(self.app, "current_user", {}).get("ad_soyad", "-")}'
            ),
            font=("Arial", 12),
            text_color="#A3A3A3",
        ).pack(side="right")

        kpi_alani = ctk.CTkFrame(
            ana,
            fg_color="transparent",
        )
        kpi_alani.pack(
            fill="x",
            padx=15,
            pady=(0, 15),
        )

        kpi_verileri = (
            ("VERİTABANI", stats["integrity"].upper()),
            ("DB BOYUTU", stats["db_size"]),
            ("YEDEK SAYISI", stats["backup_count"]),
            ("AKTİF HESAP", stats["active_accounts"]),
        )

        for index in range(len(kpi_verileri)):
            kpi_alani.grid_columnconfigure(
                index,
                weight=1,
                uniform="system_kpi",
            )

        for index, (kart_basligi, deger) in enumerate(
            kpi_verileri
        ):
            kart = ctk.CTkFrame(
                kpi_alani,
                height=82,
            )
            kart.grid(
                row=0,
                column=index,
                sticky="nsew",
                padx=5,
            )
            kart.grid_propagate(False)

            ctk.CTkLabel(
                kart,
                text=kart_basligi,
                font=("Arial", 10, "bold"),
                text_color="#A3A3A3",
            ).pack(pady=(12, 3))

            ctk.CTkLabel(
                kart,
                text=str(deger),
                font=("Arial", 19, "bold"),
                text_color=(
                    "#22C55E"
                    if kart_basligi == "VERİTABANI"
                    and str(deger).lower() == "ok"
                    else None
                ),
            ).pack()

        moduller = ctk.CTkFrame(
            ana,
            fg_color="transparent",
        )
        moduller.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 20),
        )

        for column in range(2):
            moduller.grid_columnconfigure(
                column,
                weight=1,
                uniform="system_modules",
            )

        for row in range(2):
            moduller.grid_rowconfigure(
                row,
                weight=1,
            )

        db_kart = ctk.CTkFrame(moduller)
        db_kart.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=5,
            pady=5,
        )

        self._module_header(
            db_kart,
            "VERİTABANI VE YEDEKLEME",
            (
                "Canlı veritabanını doğrulanmış şekilde "
                "yedekleyin veya güvenli geri yükleyin."
            ),
        )

        db_butonlar = ctk.CTkFrame(
            db_kart,
            fg_color="transparent",
        )
        db_butonlar.pack(
            fill="x",
            padx=20,
            pady=(10, 20),
        )

        ctk.CTkButton(
            db_butonlar,
            text="VERİTABANINI YEDEKLE",
            height=42,
            command=self.backup_database,
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 5),
        )

        ctk.CTkButton(
            db_butonlar,
            text="GÜVENLİ GERİ YÜKLE",
            height=42,
            fg_color="#B45309",
            command=self.restore_database,
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=(5, 0),
        )

        hesap_kart = ctk.CTkFrame(moduller)
        hesap_kart.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=5,
            pady=5,
        )

        self._module_header(
            hesap_kart,
            "KULLANICI HESAPLARI",
            (
                "Personel giriş hesaplarını ve güvenli "
                "parola yenileme işlemlerini yönetin."
            ),
        )

        if self._hesap_yonetim_yetkisi():
            ctk.CTkButton(
                hesap_kart,
                text="KULLANICI HESAPLARINI YÖNET",
                height=42,
                command=self.account_management,
            ).pack(
                fill="x",
                padx=20,
                pady=(10, 20),
            )
        else:
            ctk.CTkLabel(
                hesap_kart,
                text="Yalnız Fatih Ayaz yönetebilir.",
                text_color="#F59E0B",
            ).pack(
                anchor="w",
                padx=20,
                pady=(15, 25),
            )

        firma_kart = ctk.CTkFrame(moduller)
        firma_kart.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=5,
            pady=5,
        )

        self._module_header(
            firma_kart,
            "FİRMA BİLGİLERİ",
            (
                "REDBOX Gıda ve Long Potato operasyon "
                "kimlik bilgilerini görüntüleyin."
            ),
        )

        ctk.CTkButton(
            firma_kart,
            text="FİRMA BİLGİLERİNİ GÖRÜNTÜLE",
            height=42,
            command=self.company_info,
        ).pack(
            fill="x",
            padx=20,
            pady=(10, 20),
        )

        ayar_kart = ctk.CTkFrame(moduller)
        ayar_kart.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=5,
            pady=5,
        )

        self._module_header(
            ayar_kart,
            "OPERASYON AYARLARI",
            (
                "Aktif ambalaj, parti, proses suyu ve "
                "depolama parametrelerini görüntüleyin."
            ),
        )

        ctk.CTkButton(
            ayar_kart,
            text="SİSTEM AYARLARINI GÖRÜNTÜLE",
            height=42,
            command=self.settings,
        ).pack(
            fill="x",
            padx=20,
            pady=(10, 20),
        )

        if self._hesap_yonetim_yetkisi():
            self._audit_panel(ana)

    def _audit_panel(self, parent):
        panel = ctk.CTkFrame(
            parent,
            corner_radius=12,
        )
        panel.pack(
            fill="x",
            padx=20,
            pady=(0, 25),
        )

        header = ctk.CTkFrame(
            panel,
            fg_color="transparent",
        )
        header.pack(
            fill="x",
            padx=18,
            pady=(18, 8),
        )

        ctk.CTkLabel(
            header,
            text="DENETİM KAYITLARI",
            font=("Arial", 17, "bold"),
        ).pack(side="left")

        self.audit_count_label = ctk.CTkLabel(
            header,
            text="0 kayıt",
            font=("Arial", 11, "bold"),
            text_color="#A3A3A3",
        )
        self.audit_count_label.pack(side="right")

        ctk.CTkLabel(
            panel,
            text=(
                "Giriş, stok, üretim, reçete, personel ve "
                "sistem işlemlerinin değiştirilemez operasyon izi."
            ),
            font=("Arial", 12),
            text_color="#A3A3A3",
        ).pack(
            anchor="w",
            padx=18,
            pady=(0, 12),
        )

        controls = ctk.CTkFrame(
            panel,
            fg_color="transparent",
        )
        controls.pack(
            fill="x",
            padx=18,
            pady=(0, 12),
        )
        controls.grid_columnconfigure(0, weight=1)

        self.audit_search = ctk.CTkEntry(
            controls,
            placeholder_text=(
                "Denetimde ara: kullanıcı, modül, "
                "işlem, kayıt, açıklama..."
            ),
            height=38,
        )
        self.audit_search.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 8),
        )
        self.audit_search.bind(
            "<KeyRelease>",
            lambda _event: self._audit_refresh(),
        )

        self.audit_module_filter = ctk.CTkComboBox(
            controls,
            values=[
                "TÜM MODÜLLER",
                "GUVENLIK",
                "DEPO_KABUL",
                "URETIM",
                "PAKETLEME",
                "SEVKIYAT",
                "TEMIZLIK",
                "RECETE",
                "PERSONEL",
                "SISTEM",
            ],
            width=155,
            height=38,
            state="readonly",
            command=lambda _value: self._audit_refresh(),
        )
        self.audit_module_filter.grid(
            row=0,
            column=1,
            padx=4,
        )
        self.audit_module_filter.set("TÜM MODÜLLER")

        self.audit_action_filter = ctk.CTkComboBox(
            controls,
            values=[
                "TÜM İŞLEMLER",
                "GIRIS_BASARILI",
                "GIRIS_BASARISIZ",
                "OLUSTURMA",
                "GUNCELLEME",
                "SILME",
                "AKTIFLIK_DEGISIKLIGI",
                "YETKI_DEGISIKLIGI",
                "DURUM_DEGISIKLIGI",
                "YEDEKLEME",
                "GERI_YUKLEME",
            ],
            width=190,
            height=38,
            state="readonly",
            command=lambda _value: self._audit_refresh(),
        )
        self.audit_action_filter.grid(
            row=0,
            column=2,
            padx=(4, 0),
        )
        self.audit_action_filter.set("TÜM İŞLEMLER")

        table_frame = ctk.CTkFrame(
            panel,
            fg_color="transparent",
        )
        table_frame.pack(
            fill="both",
            expand=True,
            padx=18,
            pady=(0, 18),
        )
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure(
            "SystemAudit.Treeview",
            background="#252525",
            fieldbackground="#252525",
            foreground="#E5E7EB",
            rowheight=34,
            borderwidth=0,
            font=("Arial", 11),
        )
        style.configure(
            "SystemAudit.Treeview.Heading",
            background="#343434",
            foreground="#F3F4F6",
            relief="flat",
            font=("Arial", 11, "bold"),
        )
        style.map(
            "SystemAudit.Treeview",
            background=[("selected", "#1F6AA5")],
            foreground=[("selected", "#FFFFFF")],
        )

        columns = (
            "time",
            "user",
            "module",
            "action",
            "record",
            "description",
        )

        self.audit_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="SystemAudit.Treeview",
            height=10,
            selectmode="browse",
        )

        headings = (
            ("time", "TARİH / SAAT", 145, "w"),
            ("user", "KULLANICI", 130, "w"),
            ("module", "MODÜL", 100, "w"),
            ("action", "İŞLEM", 155, "w"),
            ("record", "KAYIT", 145, "w"),
            ("description", "AÇIKLAMA", 330, "w"),
        )

        for column, title, width, anchor in headings:
            self.audit_tree.heading(
                column,
                text=title,
                anchor=anchor,
            )
            self.audit_tree.column(
                column,
                width=width,
                minwidth=80,
                anchor=anchor,
                stretch=(
                    column == "description"
                ),
            )

        self.audit_tree.tag_configure(
            "even",
            background="#252525",
        )
        self.audit_tree.tag_configure(
            "odd",
            background="#2D2D2D",
        )
        self.audit_tree.tag_configure(
            "security",
            foreground="#FBBF24",
        )
        self.audit_tree.tag_configure(
            "delete",
            foreground="#FCA5A5",
        )

        vertical = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.audit_tree.yview,
        )
        horizontal = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.audit_tree.xview,
        )

        self.audit_tree.configure(
            yscrollcommand=vertical.set,
            xscrollcommand=horizontal.set,
        )

        self.audit_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        vertical.grid(
            row=0,
            column=1,
            sticky="ns",
        )
        horizontal.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        self._audit_refresh()

    def _audit_refresh(self):
        if not self._hesap_yonetim_yetkisi():
            return

        search_text = self.audit_search.get().strip()

        module_value = (
            self.audit_module_filter.get().strip()
        )
        action_value = (
            self.audit_action_filter.get().strip()
        )

        module_filter = (
            None
            if module_value == "TÜM MODÜLLER"
            else module_value
        )
        action_filter = (
            None
            if action_value == "TÜM İŞLEMLER"
            else action_value
        )

        conn = get_connection()

        try:
            rows = denetim_kayitlarini_getir(
                conn,
                modul=module_filter,
                islem=action_filter,
                arama=search_text or None,
                limit=500,
            )
        finally:
            conn.close()

        for item in self.audit_tree.get_children():
            self.audit_tree.delete(item)

        for index, row in enumerate(rows):
            tags = [
                "even" if index % 2 == 0 else "odd"
            ]

            if row["modul"] == "GUVENLIK":
                tags.append("security")

            if row["islem"] == "SILME":
                tags.append("delete")

            user_text = (
                row["ad_soyad"]
                or row["kullanici_adi"]
                or "Bilinmiyor"
            )

            record_text = row["kayit_turu"] or "-"

            if row["kayit_id"] is not None:
                record_text += f' #{row["kayit_id"]}'

            self.audit_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row["olay_zamani"],
                    user_text,
                    row["modul"],
                    row["islem"],
                    record_text,
                    row["aciklama"] or "-",
                ),
                tags=tuple(tags),
            )

        self.audit_count_label.configure(
            text=f"{len(rows)} kayıt"
        )

    def _module_header(self, parent, title, description):
        ctk.CTkLabel(
            parent,
            text=title,
            font=("Arial", 16, "bold"),
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 5),
        )

        ctk.CTkLabel(
            parent,
            text=description,
            font=("Arial", 12),
            text_color="#A3A3A3",
            justify="left",
            wraplength=520,
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 5),
        )

    def _system_stats(self):
        db_path = Path("database/redbox_os.db")
        integrity = "missing"
        active_accounts = 0

        if db_path.exists():
            conn = sqlite3.connect(
                f"file:{db_path.resolve()}?mode=ro",
                uri=True,
            )
            try:
                integrity = conn.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0]
                active_accounts = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM kullanici_hesaplari
                    WHERE aktif = 1
                    """
                ).fetchone()[0]
            finally:
                conn.close()

        size_bytes = (
            db_path.stat().st_size
            if db_path.exists()
            else 0
        )
        db_size = f"{size_bytes / 1024:.1f} KB"

        backup_dir = Path("backups")
        backup_count = (
            len(list(backup_dir.glob("*.db")))
            if backup_dir.exists()
            else 0
        )

        return {
            "integrity": integrity,
            "db_size": db_size,
            "backup_count": backup_count,
            "active_accounts": active_accounts,
        }

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
                SELECT
                    id,
                    kullanici_adi,
                    yonetici,
                    aktif
                FROM kullanici_hesaplari
                WHERE personel_id = ?
            """, (personel_row["id"],)).fetchone()

            if existing is None:
                account_id = conn.execute("""
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
                )).lastrowid

                action = "oluşturuldu"
                audit_action = "OLUSTURMA"
                old_value = None
            else:
                account_id = existing["id"]

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
                    account_id,
                ))

                action = "güncellendi"
                audit_action = "GUNCELLEME"
                old_value = {
                    "kullanici_adi": (
                        existing["kullanici_adi"]
                    ),
                    "yonetici": bool(
                        existing["yonetici"]
                    ),
                    "aktif": bool(existing["aktif"]),
                }

            denetim_kaydi_ekle(
                conn,
                modul="SISTEM",
                islem=audit_action,
                kullanici=self.app.current_user,
                kayit_turu="kullanici_hesaplari",
                kayit_id=account_id,
                aciklama=(
                    "Kullanıcı hesabı oluşturuldu veya "
                    "güvenli şekilde güncellendi."
                ),
                eski_deger=old_value,
                yeni_deger={
                    "personel_id": personel_row["id"],
                    "personel": personel,
                    "kullanici_adi": username,
                    "yonetici": (
                        bool(existing["yonetici"])
                        if existing is not None
                        else False
                    ),
                    "aktif": True,
                    "parola_degisikligi": True,
                    "parola_verisi_kaydedildi": False,
                },
                oturum_id=self.app.current_user.get(
                    "oturum_id"
                ),
            )

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

    def _database_integrity(self, db_path):
        conn = sqlite3.connect(
            f"file:{Path(db_path).resolve()}?mode=ro",
            uri=True,
        )
        try:
            return conn.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
        finally:
            conn.close()

    def _verified_database_backup(
        self,
        source,
        target,
    ):
        source = Path(source)
        target = Path(target)
        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        source_integrity = self._database_integrity(
            source
        )

        if source_integrity != "ok":
            raise RuntimeError(
                "Canlı veritabanı bütünlük kontrolü "
                f"başarısız: {source_integrity}"
            )

        source_conn = sqlite3.connect(
            str(source)
        )
        target_conn = sqlite3.connect(
            str(target)
        )

        try:
            source_conn.backup(target_conn)
            target_conn.commit()
        finally:
            target_conn.close()
            source_conn.close()

        backup_integrity = self._database_integrity(
            target
        )

        if backup_integrity != "ok":
            target.unlink(missing_ok=True)
            raise RuntimeError(
                "Oluşturulan yedeğin bütünlük "
                f"kontrolü başarısız: {backup_integrity}"
            )

        return target

    def backup_database(self):
        source = Path("database/redbox_os.db")

        if not source.exists():
            messagebox.showerror(
                "Veritabanı Yedeği",
                "Canlı veritabanı bulunamadı.",
            )
            return

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
        target = Path("backups") / (
            f"redbox_os_manual_{timestamp}.db"
        )

        audit_conn = None

        try:
            self._verified_database_backup(
                source,
                target,
            )

            audit_conn = get_connection()

            denetim_kaydi_ekle(
                audit_conn,
                modul="SISTEM",
                islem="YEDEKLEME",
                kullanici=self.app.current_user,
                kayit_turu="database_backup",
                aciklama=(
                    "Doğrulanmış manuel veritabanı "
                    "yedeği oluşturuldu."
                ),
                yeni_deger={
                    "dosya_adi": target.name,
                    "butunluk": "OK",
                },
                oturum_id=self.app.current_user.get(
                    "oturum_id"
                ),
            )

            audit_conn.commit()

        except Exception as exc:
            if audit_conn is not None:
                audit_conn.rollback()

            target.unlink(missing_ok=True)
            messagebox.showerror(
                "Veritabanı Yedeği",
                (
                    "Yedek oluşturulamadı.\n\n"
                    f"{exc}"
                ),
            )
            return

        finally:
            if audit_conn is not None:
                audit_conn.close()

        messagebox.showinfo(
            "Veritabanı Yedeği",
            (
                "Doğrulanmış veritabanı yedeği "
                "başarıyla oluşturuldu.\n\n"
                f"Dosya: {target.name}\n"
                "Bütünlük: OK"
            ),
        )

        self.create()

    def restore_database(self):
        from tkinter import filedialog

        selected = filedialog.askopenfilename(
            title="REDBOX OS Yedek Dosyası Seç",
            initialdir="backups",
            filetypes=[
                ("SQLite Database", "*.db"),
                ("Tüm Dosyalar", "*.*"),
            ],
        )

        if not selected:
            return

        selected_path = Path(selected)
        live_path = Path("database/redbox_os.db")

        try:
            selected_integrity = (
                self._database_integrity(
                    selected_path
                )
            )

            if selected_integrity != "ok":
                raise RuntimeError(
                    "Seçilen yedek geçerli değil. "
                    f"Bütünlük sonucu: {selected_integrity}"
                )

            confirmation = messagebox.askyesno(
                "Güvenli Geri Yükleme",
                (
                    "Seçilen doğrulanmış yedek canlı "
                    "veritabanının yerine yüklenecek.\n\n"
                    f"Dosya: {selected_path.name}\n"
                    "Bütünlük: OK\n\n"
                    "İşlem öncesinde canlı veritabanının "
                    "otomatik güvenlik yedeği alınacaktır.\n\n"
                    "Devam edilsin mi?"
                ),
            )

            if not confirmation:
                return

            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            safety_backup = Path("backups") / (
                "redbox_os_before_restore_"
                f"{timestamp}.db"
            )

            self._verified_database_backup(
                live_path,
                safety_backup,
            )

            temporary = live_path.with_name(
                "redbox_os_restore_pending.db"
            )
            temporary.unlink(missing_ok=True)

            source_conn = sqlite3.connect(
                f"file:{selected_path.resolve()}?mode=ro",
                uri=True,
            )
            target_conn = sqlite3.connect(
                str(temporary)
            )

            try:
                source_conn.backup(target_conn)
                target_conn.commit()
            finally:
                target_conn.close()
                source_conn.close()

            temporary_integrity = (
                self._database_integrity(
                    temporary
                )
            )

            if temporary_integrity != "ok":
                temporary.unlink(missing_ok=True)
                raise RuntimeError(
                    "Geri yükleme kopyası doğrulanamadı. "
                    f"Sonuç: {temporary_integrity}"
                )

            os.replace(
                temporary,
                live_path,
            )

            run_migrations(live_path)

            final_integrity = (
                self._database_integrity(
                    live_path
                )
            )

            if final_integrity != "ok":
                raise RuntimeError(
                    "Canlı veritabanının son doğrulaması "
                    f"başarısız: {final_integrity}"
                )

            audit_conn = get_connection()

            try:
                denetim_kaydi_ekle(
                    audit_conn,
                    modul="SISTEM",
                    islem="GERI_YUKLEME",
                    kullanici=self.app.current_user,
                    kayit_turu="database_restore",
                    aciklama=(
                        "Doğrulanmış veritabanı yedeği "
                        "canlı sisteme geri yüklendi."
                    ),
                    yeni_deger={
                        "kaynak_dosya": (
                            selected_path.name
                        ),
                        "guvenlik_yedegi": (
                            safety_backup.name
                        ),
                        "butunluk": "OK",
                    },
                    oturum_id=self.app.current_user.get(
                        "oturum_id"
                    ),
                )

                audit_conn.commit()

            except Exception:
                audit_conn.rollback()
                raise

            finally:
                audit_conn.close()

        except Exception as exc:
            messagebox.showerror(
                "Geri Yükleme Hatası",
                str(exc),
            )
            return

        messagebox.showinfo(
            "Güvenli Geri Yükleme",
            (
                "Veritabanı başarıyla geri yüklendi "
                "ve doğrulandı.\n\n"
                f"Ön yedek: {safety_backup.name}\n"
                "Bütünlük: OK\n\n"
                "Uygulamayı şimdi kapatıp yeniden açın."
            ),
        )


    def company_info(self):
        window = ctk.CTkToplevel(self.app)
        window.title("REDBOX OS — Firma Bilgileri")
        window.geometry("720x610")
        window.minsize(650, 540)
        window.transient(self.app)
        window.grab_set()

        body = ctk.CTkScrollableFrame(
            window,
            corner_radius=14,
        )
        body.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20,
        )

        ctk.CTkLabel(
            body,
            text="FİRMA BİLGİLERİ",
            font=("Arial", 24, "bold"),
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 5),
        )

        ctk.CTkLabel(
            body,
            text=(
                "REDBOX OS operasyon kimliği ve "
                "üretim sistemi özeti"
            ),
            font=("Arial", 13),
            text_color="#A3A3A3",
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 20),
        )

        bilgiler = (
            ("FİRMA / İŞLETME", "REDBOX GIDA"),
            ("ÜRÜN / MARKA", "LONG POTATO"),
            ("YÖNETİM SİSTEMİ", "REDBOX OS"),
            ("ÜRETİM MODELİ", "Parti ve lot bazlı üretim"),
            (
                "İZLENEBİLİRLİK",
                "Hammadde → üretim → paketleme → sevkiyat",
            ),
            (
                "AKTİF AMBALAJLAR",
                "500 g ve 2.5 kg",
            ),
            (
                "VERİ KAYNAĞI",
                "SQLite — database/redbox_os.db",
            ),
        )

        table = ctk.CTkFrame(body)
        table.pack(
            fill="x",
            padx=20,
            pady=(0, 15),
        )
        table.grid_columnconfigure(1, weight=1)

        for row_index, (label, value) in enumerate(
            bilgiler
        ):
            color = (
                "#292929"
                if row_index % 2 == 0
                else "#303030"
            )

            ctk.CTkLabel(
                table,
                text=label,
                width=190,
                height=44,
                anchor="w",
                font=("Arial", 12, "bold"),
                fg_color=color,
            ).grid(
                row=row_index,
                column=0,
                sticky="nsew",
                padx=(1, 0),
                pady=1,
            )

            ctk.CTkLabel(
                table,
                text=value,
                height=44,
                anchor="w",
                justify="left",
                wraplength=410,
                fg_color=color,
            ).grid(
                row=row_index,
                column=1,
                sticky="nsew",
                padx=(0, 1),
                pady=1,
            )

        ctk.CTkLabel(
            body,
            text=(
                "Firma adresi, iletişim bilgileri ve resmi "
                "kayıt bilgileri sisteme tanımlandığında "
                "bu bölümden merkezi olarak yönetilecektir."
            ),
            font=("Arial", 12),
            text_color="#A3A3A3",
            justify="left",
            wraplength=620,
        ).pack(
            anchor="w",
            padx=20,
            pady=(5, 20),
        )

        ctk.CTkButton(
            body,
            text="KAPAT",
            height=42,
            command=window.destroy,
        ).pack(
            fill="x",
            padx=20,
            pady=(0, 20),
        )

        window.after(
            150,
            window.focus_force,
        )

    def settings(self):
        conn = get_connection()

        try:
            rows = conn.execute(
                """
                SELECT
                    anahtar,
                    deger,
                    aciklama
                FROM sistem_ayarlari
                ORDER BY anahtar
                """
            ).fetchall()
        finally:
            conn.close()

        window = ctk.CTkToplevel(self.app)
        window.title("REDBOX OS — Operasyon Ayarları")
        window.geometry("900x680")
        window.minsize(780, 560)
        window.transient(self.app)
        window.grab_set()

        body = ctk.CTkScrollableFrame(
            window,
            corner_radius=14,
        )
        body.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20,
        )

        ctk.CTkLabel(
            body,
            text="OPERASYON AYARLARI",
            font=("Arial", 24, "bold"),
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 5),
        )

        ctk.CTkLabel(
            body,
            text=(
                "Üretim, ambalaj, depolama ve raf ömrü "
                "için kullanılan merkezi sistem parametreleri"
            ),
            font=("Arial", 13),
            text_color="#A3A3A3",
        ).pack(
            anchor="w",
            padx=20,
            pady=(0, 20),
        )

        table = ctk.CTkFrame(body)
        table.pack(
            fill="x",
            padx=20,
            pady=(0, 15),
        )
        table.grid_columnconfigure(0, weight=2)
        table.grid_columnconfigure(1, weight=1)
        table.grid_columnconfigure(2, weight=3)

        headers = (
            ("AYAR KODU", 0),
            ("DEĞER", 1),
            ("AÇIKLAMA", 2),
        )

        for title, column in headers:
            ctk.CTkLabel(
                table,
                text=title,
                height=42,
                font=("Arial", 12, "bold"),
                fg_color="#1E293B",
            ).grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=1,
                pady=1,
            )

        for row_index, row in enumerate(
            rows,
            start=1,
        ):
            color = (
                "#292929"
                if row_index % 2 == 1
                else "#303030"
            )

            values = (
                row["anahtar"],
                row["deger"],
                row["aciklama"] or "-",
            )

            for column, value in enumerate(values):
                ctk.CTkLabel(
                    table,
                    text=str(value),
                    height=46,
                    anchor=(
                        "center"
                        if column == 1
                        else "w"
                    ),
                    justify="left",
                    wraplength=360,
                    fg_color=color,
                    font=(
                        ("Arial", 12, "bold")
                        if column == 1
                        else ("Arial", 12)
                    ),
                ).grid(
                    row=row_index,
                    column=column,
                    sticky="nsew",
                    padx=1,
                    pady=1,
                )

        warning = ctk.CTkFrame(
            body,
            fg_color="#422006",
            corner_radius=10,
        )
        warning.pack(
            fill="x",
            padx=20,
            pady=(5, 15),
        )

        ctk.CTkLabel(
            warning,
            text=(
                "Bu parametreler üretim hesaplarını ve stok "
                "hareketlerini doğrudan etkiler. Güvenlik "
                "nedeniyle bu ekranda salt okunur gösterilir."
            ),
            font=("Arial", 12, "bold"),
            text_color="#FBBF24",
            justify="left",
            wraplength=760,
        ).pack(
            anchor="w",
            padx=18,
            pady=15,
        )

        ctk.CTkButton(
            body,
            text="KAPAT",
            height=42,
            command=window.destroy,
        ).pack(
            fill="x",
            padx=20,
            pady=(0, 20),
        )

        window.after(
            150,
            window.focus_force,
        )
