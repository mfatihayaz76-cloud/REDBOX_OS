import hashlib
import hmac
import multiprocessing
import os
import sqlite3
from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from database.db import get_connection


PBKDF2_ITERATIONS = 600_000


def _parola_hash(parola, tuz, iterasyon=PBKDF2_ITERATIONS):
    return hashlib.pbkdf2_hmac(
        "sha256",
        parola.encode("utf-8"),
        bytes.fromhex(tuz),
        iterasyon,
    ).hex()


class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.authenticated_user = None
        self.title("REDBOX OS — Giriş")
        self.geometry("520x650")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._kapat)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.card = ctk.CTkFrame(
            self,
            width=420,
            corner_radius=18,
        )
        self.card.grid(
            row=0,
            column=0,
            padx=50,
            pady=45,
            sticky="nsew",
        )
        self.card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.card,
            text="REDBOX OS",
            font=("Arial", 34, "bold"),
        ).grid(
            row=0,
            column=0,
            padx=30,
            pady=(45, 4),
        )

        ctk.CTkLabel(
            self.card,
            text="REDBOX GIDA",
            font=("Arial", 14),
            text_color="#9CA3AF",
        ).grid(
            row=1,
            column=0,
            padx=30,
            pady=(0, 30),
        )

        self.form = ctk.CTkFrame(
            self.card,
            fg_color="transparent",
        )
        self.form.grid(
            row=2,
            column=0,
            padx=35,
            pady=(0, 25),
            sticky="ew",
        )
        self.form.grid_columnconfigure(0, weight=1)

        if self._hesap_var_mi():
            self._giris_formu()
        else:
            self._ilk_kurulum_formu()

        self.after(150, self._ortala)

    def _ortala(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{max(y - 30, 0)}")

    def _hesap_var_mi(self):
        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT COUNT(*)
                FROM kullanici_hesaplari
                WHERE aktif = 1
            """).fetchone()
            return int(row[0]) > 0
        finally:
            conn.close()

    def _formu_temizle(self):
        for widget in self.form.winfo_children():
            widget.destroy()

    def _baslik(self, text, detail):
        ctk.CTkLabel(
            self.form,
            text=text,
            font=("Arial", 20, "bold"),
        ).grid(
            row=0,
            column=0,
            pady=(0, 6),
        )

        ctk.CTkLabel(
            self.form,
            text=detail,
            font=("Arial", 12),
            text_color="#9CA3AF",
            wraplength=330,
        ).grid(
            row=1,
            column=0,
            pady=(0, 22),
        )

    def _ilk_kurulum_formu(self):
        self._formu_temizle()
        self._baslik(
            "İLK YÖNETİCİ HESABI",
            "Bu işlem yalnızca ilk kullanımda yapılır.",
        )

        personeller = self._aktif_personeller()
        if not personeller:
            messagebox.showerror(
                "Kurulum Hatası",
                "Aktif personel kaydı bulunamadı.",
            )
            self.destroy()
            return

        varsayilan = (
            "Fatih Ayaz"
            if "Fatih Ayaz" in personeller
            else personeller[0]
        )

        self.personel_secim = ctk.CTkOptionMenu(
            self.form,
            values=personeller,
            height=42,
        )
        self.personel_secim.set(varsayilan)
        self.personel_secim.grid(
            row=2,
            column=0,
            pady=7,
            sticky="ew",
        )

        self.kullanici_entry = ctk.CTkEntry(
            self.form,
            placeholder_text="Kullanıcı adı",
            height=42,
        )
        self.kullanici_entry.insert(0, "fatih")
        self.kullanici_entry.grid(
            row=3,
            column=0,
            pady=7,
            sticky="ew",
        )

        self.parola_entry = ctk.CTkEntry(
            self.form,
            placeholder_text="Parola — en az 8 karakter",
            show="●",
            height=42,
        )
        self.parola_entry.grid(
            row=4,
            column=0,
            pady=7,
            sticky="ew",
        )

        self.parola_tekrar_entry = ctk.CTkEntry(
            self.form,
            placeholder_text="Parola tekrar",
            show="●",
            height=42,
        )
        self.parola_tekrar_entry.grid(
            row=5,
            column=0,
            pady=7,
            sticky="ew",
        )

        ctk.CTkButton(
            self.form,
            text="YÖNETİCİ HESABINI OLUŞTUR",
            height=46,
            font=("Arial", 13, "bold"),
            command=self._ilk_hesabi_olustur,
        ).grid(
            row=6,
            column=0,
            pady=(18, 5),
            sticky="ew",
        )

        self.parola_tekrar_entry.bind(
            "<Return>",
            lambda _event: self._ilk_hesabi_olustur(),
        )
        self.parola_entry.focus_set()

    def _aktif_personeller(self):
        conn = get_connection()
        try:
            rows = conn.execute("""
                SELECT p.ad_soyad
                FROM personeller p
                LEFT JOIN kullanici_hesaplari kh
                  ON kh.personel_id = p.id
                WHERE p.aktif = 1
                  AND kh.id IS NULL
                ORDER BY
                    CASE
                        WHEN p.ad_soyad = 'Fatih Ayaz' THEN 0
                        ELSE 1
                    END,
                    p.ad_soyad
            """).fetchall()
            return [row["ad_soyad"] for row in rows]
        finally:
            conn.close()

    def _ilk_hesabi_olustur(self):
        personel = self.personel_secim.get().strip()
        kullanici = self.kullanici_entry.get().strip()
        parola = self.parola_entry.get()
        parola_tekrar = self.parola_tekrar_entry.get()

        if len(kullanici) < 3:
            messagebox.showwarning(
                "Eksik Bilgi",
                "Kullanıcı adı en az 3 karakter olmalıdır.",
            )
            return

        if len(parola) < 8:
            messagebox.showwarning(
                "Zayıf Parola",
                "Parola en az 8 karakter olmalıdır.",
            )
            return

        if parola != parola_tekrar:
            messagebox.showwarning(
                "Parola Hatası",
                "Parolalar birbiriyle aynı değil.",
            )
            return

        tuz = os.urandom(16).hex()
        parola_ozeti = _parola_hash(parola, tuz)
        now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        conn = get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")

            hesap_sayisi = conn.execute("""
                SELECT COUNT(*)
                FROM kullanici_hesaplari
            """).fetchone()[0]

            if hesap_sayisi:
                raise RuntimeError(
                    "İlk yönetici hesabı daha önce oluşturulmuş."
                )

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
                VALUES (?, ?, ?, ?, ?, 1, 1, ?)
            """, (
                personel_row["id"],
                kullanici,
                parola_ozeti,
                tuz,
                PBKDF2_ITERATIONS,
                now,
            ))

            conn.commit()

        except (sqlite3.Error, RuntimeError) as exc:
            conn.rollback()
            messagebox.showerror(
                "Hesap Oluşturma Hatası",
                str(exc),
            )
            return
        finally:
            conn.close()

        messagebox.showinfo(
            "Hesap Hazır",
            "Yönetici hesabı güvenli şekilde oluşturuldu.",
        )
        self._giris_formu()

    def _giris_formu(self):
        self._formu_temizle()
        self._baslik(
            "GÜVENLİ GİRİŞ",
            "REDBOX OS yönetim paneline giriş yapın.",
        )

        self.kullanici_entry = ctk.CTkEntry(
            self.form,
            placeholder_text="Kullanıcı adı",
            height=44,
        )
        self.kullanici_entry.grid(
            row=2,
            column=0,
            pady=8,
            sticky="ew",
        )

        self.parola_entry = ctk.CTkEntry(
            self.form,
            placeholder_text="Parola",
            show="●",
            height=44,
        )
        self.parola_entry.grid(
            row=3,
            column=0,
            pady=8,
            sticky="ew",
        )

        ctk.CTkButton(
            self.form,
            text="GİRİŞ YAP",
            height=46,
            font=("Arial", 14, "bold"),
            command=self._giris_yap,
        ).grid(
            row=4,
            column=0,
            pady=(20, 8),
            sticky="ew",
        )

        ctk.CTkLabel(
            self.form,
            text="Yetkisiz erişim yasaktır.",
            font=("Arial", 11),
            text_color="#6B7280",
        ).grid(
            row=5,
            column=0,
            pady=(12, 0),
        )

        self.parola_entry.bind(
            "<Return>",
            lambda _event: self._giris_yap(),
        )
        self.kullanici_entry.focus_set()

    def _giris_yap(self):
        kullanici = self.kullanici_entry.get().strip()
        parola = self.parola_entry.get()

        if not kullanici or not parola:
            messagebox.showwarning(
                "Eksik Bilgi",
                "Kullanıcı adı ve parola zorunludur.",
            )
            return

        conn = get_connection()
        try:
            row = conn.execute("""
                SELECT
                    kh.id,
                    kh.personel_id,
                    kh.kullanici_adi,
                    kh.parola_hash,
                    kh.parola_tuzu,
                    kh.iterasyon,
                    kh.yonetici,
                    p.ad_soyad
                FROM kullanici_hesaplari kh
                JOIN personeller p
                  ON p.id = kh.personel_id
                WHERE kh.kullanici_adi = ?
                  AND kh.aktif = 1
                  AND p.aktif = 1
                LIMIT 1
            """, (kullanici,)).fetchone()

            dogru = False
            if row is not None:
                aday = _parola_hash(
                    parola,
                    row["parola_tuzu"],
                    int(row["iterasyon"]),
                )
                dogru = hmac.compare_digest(
                    aday,
                    row["parola_hash"],
                )

            if not dogru:
                messagebox.showerror(
                    "Giriş Başarısız",
                    "Kullanıcı adı veya parola hatalı.",
                )
                self.parola_entry.delete(0, "end")
                self.parola_entry.focus_set()
                return

            yetki_rows = conn.execute("""
                SELECT yetki_kodu
                FROM personel_yetkileri
                WHERE personel_id = ?
                  AND aktif = 1
                ORDER BY yetki_kodu
            """, (row["personel_id"],)).fetchall()

            conn.execute("""
                UPDATE kullanici_hesaplari
                SET son_giris_zamani = ?
                WHERE id = ?
            """, (
                datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                row["id"],
            ))
            conn.commit()

            self.authenticated_user = {
                "hesap_id": row["id"],
                "personel_id": row["personel_id"],
                "kullanici_adi": row["kullanici_adi"],
                "ad_soyad": row["ad_soyad"],
                "yonetici": bool(row["yonetici"]),
                "yetkiler": [
                    item["yetki_kodu"]
                    for item in yetki_rows
                ],
            }

        finally:
            conn.close()

        self.withdraw()
        self.quit()

    def _kapat(self):
        self.authenticated_user = None
        self.withdraw()
        self.quit()


def _login_process(send_connection):
    window = LoginWindow()
    window.mainloop()

    try:
        send_connection.send(window.authenticated_user)
    finally:
        send_connection.close()
        window.destroy()


def authenticate_user():
    context = multiprocessing.get_context("spawn")
    receive_connection, send_connection = context.Pipe(
        duplex=False
    )

    process = context.Process(
        target=_login_process,
        args=(send_connection,),
    )
    process.start()
    send_connection.close()

    try:
        current_user = receive_connection.recv()
    except EOFError:
        current_user = None
    finally:
        receive_connection.close()
        process.join()

    if process.exitcode != 0:
        raise RuntimeError(
            "Giriş ekranı güvenli şekilde başlatılamadı."
        )

    return current_user
