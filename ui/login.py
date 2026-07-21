import hashlib
import hmac
import multiprocessing
from datetime import datetime
from tkinter import messagebox

import customtkinter as ctk

from database.db import get_connection
from database.audit_engine import (
    denetim_kaydi_ekle,
    yeni_oturum_id,
)
from database.first_setup_engine import (
    ilk_kurulum_gerekli_mi,
    uygulama_kimligini_getir,
)
from ui.first_setup_wizard import FirstSetupWizard
from ui.company_profile_window import CompanyProfileWindow
from ui.license_center_window import LicenseCenterWindow
from database.licensing_engine import (
    cihaz_parmak_izi_olustur,
    lisans_acik_anahtarlarini_yukle,
    lisans_erisim_karari,
    lisans_talep_bilgilerini_getir,
)


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
        self.oturum_id = yeni_oturum_id()
        self.application_context = self._uygulama_kimligi()
        self.license_device = None
        self.license_public_keys = None
        self.license_decision = self._lisans_erisim_karari()
        self.title(
            "REDBOX OS — "
            f"{self.application_context['firma_kisa_ad']} — Giriş"
        )
        self._window_width = 520
        self._window_height = 650
        self.geometry(
            f"{self._window_width}x{self._window_height}"
        )
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
        self.card.grid_rowconfigure(3, weight=1)

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

        self.company_label = ctk.CTkLabel(
            self.card,
            text=self.application_context["firma_kisa_ad"],
            font=("Arial", 14, "bold"),
            text_color="#D1D5DB",
        )
        self.company_label.grid(
            row=1,
            column=0,
            padx=30,
            pady=(0, 5),
        )

        self.mode_label = ctk.CTkLabel(
            self.card,
            text=self.application_context["kullanim_modu"],
            font=("Arial", 11, "bold"),
            text_color=self._mod_rengi(),
        )
        self.mode_label.grid(
            row=2,
            column=0,
            padx=30,
            pady=(0, 22),
        )

        self.form = ctk.CTkFrame(
            self.card,
            fg_color="transparent",
        )
        self.form.grid(
            row=3,
            column=0,
            padx=35,
            pady=(0, 25),
            sticky="nsew",
        )
        self.form.grid_columnconfigure(0, weight=1)

        if self._ilk_kurulum_gerekli_mi():
            self._window_width = 900
            self._window_height = 820
            self.minsize(760, 680)
            self.resizable(True, True)
            self.geometry(
                f"{self._window_width}x{self._window_height}"
            )
            self._ilk_kurulum_formu()
        else:
            self._giris_formu()

        self.after(150, self._ortala)

    def _ortala(self):
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = min(self._window_width, screen_width - 40)
        height = min(self._window_height, screen_height - 90)
        x = max((screen_width - width) // 2, 0)
        y = max((screen_height - height) // 2 - 20, 0)
        self.geometry(
            f"{width}x{height}+{x}+{y}"
        )

    def _uygulama_kimligi(self):
        conn = get_connection()
        try:
            return uygulama_kimligini_getir(conn)
        finally:
            conn.close()

    def _mod_rengi(self):
        return {
            "GERCEK": "#22C55E",
            "DEMO": "#F59E0B",
            "KURULUM": "#60A5FA",
        }.get(
            self.application_context["kullanim_modu"],
            "#9CA3AF",
        )

    def _kimlik_etiketlerini_guncelle(self):
        self.company_label.configure(
            text=self.application_context["firma_kisa_ad"],
        )
        self.mode_label.configure(
            text=self.application_context["kullanim_modu"],
            text_color=self._mod_rengi(),
        )
        self.title(
            "REDBOX OS — "
            f"{self.application_context['firma_kisa_ad']} — Giriş"
        )

    def _ilk_kurulum_gerekli_mi(self):
        conn = get_connection()
        try:
            return ilk_kurulum_gerekli_mi(conn)
        finally:
            conn.close()


    def _lisans_erisim_karari(self):
        try:
            self.license_device = cihaz_parmak_izi_olustur()
            self.license_public_keys = (
                lisans_acik_anahtarlarini_yukle()
            )
            conn = get_connection()
            try:
                return lisans_erisim_karari(
                    conn,
                    self.license_public_keys,
                    self.license_device[
                        "cihaz_parmak_izi_sha256"
                    ],
                )
            finally:
                conn.close()
        except Exception as exc:
            return {
                "erisim_izni": False,
                "gecerli": False,
                "durum": "LISANS_KONTROL_HATASI",
                "neden_kodu": type(exc).__name__,
                "akis": "LISANS_AKTIVASYONU",
                "aciklama": str(exc),
            }

    def _lisans_kararini_yenile(self):
        self.license_decision = self._lisans_erisim_karari()
        return self.license_decision

    def _lisans_tamamlama_akisi(self, authenticated_user):
        conn = get_connection()
        try:
            request = lisans_talep_bilgilerini_getir(
                conn,
                cihaz_bilgisi=self.license_device,
            )
        finally:
            conn.close()

        if not request.get("hazir"):
            company_window = CompanyProfileWindow(
                self,
                kullanici=authenticated_user,
                oturum_id=self.oturum_id,
            )
            self.wait_window(company_window)

        decision = self._lisans_kararini_yenile()

        if decision.get("erisim_izni"):
            return True

        license_window = LicenseCenterWindow(
            self,
            kullanici=authenticated_user,
            oturum_id=self.oturum_id,
        )
        self.wait_window(license_window)

        decision = self._lisans_kararini_yenile()
        return bool(decision.get("erisim_izni"))

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
        self.form.grid_rowconfigure(0, weight=1)
        self.wizard = FirstSetupWizard(
            self.form,
            on_complete=self._kurulum_tamamlandi,
            oturum_id=self.oturum_id,
        )
        self.wizard.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

    def _kurulum_tamamlandi(self, _result):
        self.application_context = self._uygulama_kimligi()
        self._lisans_kararini_yenile()
        self._kimlik_etiketlerini_guncelle()
        self._window_width = 520
        self._window_height = 650
        self.minsize(520, 650)
        self.resizable(False, False)
        self.geometry(
            f"{self._window_width}x{self._window_height}"
        )
        self._giris_formu()
        self.after(50, self._ortala)

    def _giris_formu(self):
        self._formu_temizle()
        self._baslik(
            "GÜVENLİ GİRİŞ",
            "REDBOX OS yönetim paneline giriş yapın.",
        )

        if self.license_decision.get("durum") == "GECIS_SURESI":
            ctk.CTkLabel(
                self.form,
                text=(
                    "LİSANS GEÇİŞ SÜRESİ: "
                    + str(self.license_decision.get("kalan_gun", 0))
                    + " gün kaldı"
                ),
                font=("Arial", 11, "bold"),
                text_color="#F59E0B",
            ).grid(
                row=6,
                column=0,
                pady=(8, 0),
            )
        elif self.license_decision.get("durum") == "DEMO_AKTIF":
            ctk.CTkLabel(
                self.form,
                text=(
                    "30 GÜNLÜK DEMO: "
                    + str(self.license_decision.get("kalan_gun", 0))
                    + " gün kaldı — aktivasyon kodu gerekmez"
                ),
                font=("Arial", 11, "bold"),
                text_color="#F59E0B",
            ).grid(
                row=6,
                column=0,
                pady=(8, 0),
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
                denetim_kaydi_ekle(
                    conn,
                    modul="GUVENLIK",
                    islem="GIRIS_BASARISIZ",
                    kullanici={
                        "kullanici_adi": kullanici,
                    },
                    aciklama=(
                        "Geçersiz kullanıcı adı veya parola "
                        "ile giriş denemesi."
                    ),
                    oturum_id=self.oturum_id,
                )
                conn.commit()

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

            authenticated_user = {
                "hesap_id": row["id"],
                "personel_id": row["personel_id"],
                "kullanici_adi": row["kullanici_adi"],
                "ad_soyad": row["ad_soyad"],
                "yonetici": bool(row["yonetici"]),
                "yetkiler": [
                    item["yetki_kodu"]
                    for item in yetki_rows
                ],
                "oturum_id": self.oturum_id,
            }
            authenticated_user.update(
                self.application_context
            )

            current_license = self._lisans_kararini_yenile()

            if not current_license.get("erisim_izni"):
                if not self._lisans_tamamlama_akisi(
                    authenticated_user
                ):
                    messagebox.showerror(
                        "Lisans Aktivasyonu Gerekli",
                        (
                            "REDBOX OS erişimi için firma profilini "
                            "tamamlayın ve geçerli imzalı lisansı "
                            "aktive edin.\n\nNeden kodu: "
                            + self.license_decision.get(
                                "neden_kodu",
                                "LISANS_GEREKLI",
                            )
                        ),
                        parent=self,
                    )
                    self.parola_entry.delete(0, "end")
                    self.parola_entry.focus_set()
                    return

            authenticated_user["lisans_durumu"] = dict(
                self.license_decision
            )

            conn.execute("""
                UPDATE kullanici_hesaplari
                SET son_giris_zamani = ?
                WHERE id = ?
            """, (
                datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                row["id"],
            ))

            denetim_kaydi_ekle(
                conn,
                modul="GUVENLIK",
                islem="GIRIS_BASARILI",
                kullanici=authenticated_user,
                kayit_turu="kullanici_hesaplari",
                kayit_id=row["id"],
                aciklama="Kullanıcı oturumu başarıyla açıldı.",
                oturum_id=self.oturum_id,
            )

            conn.commit()
            self.authenticated_user = authenticated_user

            if (
                self.license_decision.get("durum")
                == "GECIS_SURESI"
            ):
                messagebox.showwarning(
                    "Lisans Geçiş Süresi",
                    (
                        "Mevcut kurulum güvenli geçiş süresindedir. "
                        "Normal kullanım devam eder. Kalan süre: "
                        + str(
                            self.license_decision.get(
                                "kalan_gun",
                                0,
                            )
                        )
                        + " gün. Süre dolmadan gerçek firma "
                        "profilini tamamlayıp lisansı aktive edin."
                    ),
                    parent=self,
                )

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
    window = LoginWindow()

    try:
        window.mainloop()
        return window.authenticated_user
    finally:
        try:
            window.destroy()
        except Exception:
            pass

