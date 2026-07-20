from tkinter import messagebox

import customtkinter as ctk

from database.company_profile_engine import (
    firma_profilini_getir,
    legacy_firma_profilini_olustur,
)
from database.db import get_connection


class CompanyProfileWindow(ctk.CTkToplevel):

    FIELD_CONTRACT = (
        ("ticari_unvan", "Ticari Unvan *"),
        ("kisa_ad", "Firma Kısa Adı *"),
        ("vergi_dairesi", "Vergi Dairesi"),
        ("vergi_no", "Vergi Numarası"),
        ("ulke", "Ülke *"),
        ("il", "İl"),
        ("ilce", "İlçe"),
        ("adres", "Açık Adres"),
        ("telefon", "Telefon"),
        ("eposta", "E-posta"),
    )

    def __init__(
        self,
        master,
        kullanici=None,
        oturum_id=None,
        on_complete=None,
    ):
        super().__init__(master)

        self.kullanici = kullanici or {}
        self.oturum_id = oturum_id
        self.on_complete = on_complete
        self.values = {
            key: ctk.StringVar(
                value=(
                    "Türkiye"
                    if key == "ulke"
                    else ""
                )
            )
            for key, _label in self.FIELD_CONTRACT
        }
        self.confirmed = ctk.BooleanVar(value=False)

        self.title("REDBOX OS — Firma Profili")
        self.geometry("820x780")
        self.minsize(720, 620)
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.body = ctk.CTkScrollableFrame(
            self,
            corner_radius=14,
        )
        self.body.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=20,
            pady=(20, 10),
        )
        self.body.grid_columnconfigure(0, weight=1)

        self.footer = ctk.CTkFrame(
            self,
            corner_radius=12,
        )
        self.footer.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=20,
            pady=(0, 20),
        )
        self.footer.grid_columnconfigure(0, weight=1)
        self.footer.grid_columnconfigure(1, weight=1)

        profile = self._load_profile()

        if profile is None:
            self._render_form()
        else:
            self._render_profile(profile)

        self.after(150, self.focus_force)

    def _load_profile(self):
        conn = get_connection()
        try:
            return firma_profilini_getir(conn)
        finally:
            conn.close()

    def _header(self, subtitle):
        ctk.CTkLabel(
            self.body,
            text="FİRMA PROFİLİ",
            font=("Arial", 26, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=25,
            pady=(25, 5),
        )

        ctk.CTkLabel(
            self.body,
            text=subtitle,
            font=("Arial", 13),
            text_color="#A3A3A3",
            justify="left",
            wraplength=700,
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=25,
            pady=(0, 20),
        )

    def _render_profile(self, profile):
        self._header(
            "Lisans ve kurumsal uygulama kimliğinde "
            "kullanılan doğrulanmış firma bilgileri."
        )

        fields = (
            ("TİCARİ UNVAN", profile["ticari_unvan"]),
            ("KISA AD", profile["kisa_ad"]),
            (
                "VERGİ DAİRESİ",
                profile["vergi_dairesi"] or "-",
            ),
            (
                "VERGİ NUMARASI",
                profile["vergi_no"] or "-",
            ),
            ("ÜLKE", profile["ulke"]),
            ("İL", profile["il"] or "-"),
            ("İLÇE", profile["ilce"] or "-"),
            ("AÇIK ADRES", profile["adres"] or "-"),
            ("TELEFON", profile["telefon"] or "-"),
            ("E-POSTA", profile["eposta"] or "-"),
            (
                "DURUM",
                (
                    "AKTİF"
                    if int(profile["aktif"]) == 1
                    else "PASİF"
                ),
            ),
        )

        table = ctk.CTkFrame(self.body)
        table.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=25,
            pady=(0, 20),
        )
        table.grid_columnconfigure(1, weight=1)

        for row_index, (label, value) in enumerate(fields):
            color = (
                "#292929"
                if row_index % 2 == 0
                else "#303030"
            )

            ctk.CTkLabel(
                table,
                text=label,
                width=190,
                height=46,
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
                text=str(value),
                height=46,
                anchor="w",
                justify="left",
                wraplength=480,
                fg_color=color,
            ).grid(
                row=row_index,
                column=1,
                sticky="nsew",
                padx=(0, 1),
                pady=1,
            )

        ctk.CTkLabel(
            self.body,
            text=(
                "Firma kimliğini değiştirmek aktif lisans "
                "bağlantısını etkileyebilir. Kimlik değişiklikleri "
                "kontrollü lisans yenileme sürecinde yapılacaktır."
            ),
            font=("Arial", 12, "bold"),
            text_color="#FBBF24",
            justify="left",
            wraplength=700,
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=25,
            pady=(0, 25),
        )

        ctk.CTkButton(
            self.footer,
            text="KAPAT",
            height=44,
            command=self.destroy,
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=15,
            pady=15,
        )

    def _render_form(self):
        self._header(
            "Mevcut kurulumun gerçek ticari firma bilgilerini "
            "girin. Bu bilgiler lisansın firma bağlantısını "
            "oluşturacaktır."
        )

        form = ctk.CTkFrame(
            self.body,
            fg_color="transparent",
        )
        form.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=25,
            pady=(0, 20),
        )
        form.grid_columnconfigure(0, weight=1)

        for row_index, (key, label) in enumerate(
            self.FIELD_CONTRACT
        ):
            ctk.CTkLabel(
                form,
                text=label,
                font=("Arial", 12, "bold"),
                anchor="w",
            ).grid(
                row=row_index * 2,
                column=0,
                sticky="ew",
                pady=(8, 4),
            )

            ctk.CTkEntry(
                form,
                textvariable=self.values[key],
                height=42,
            ).grid(
                row=row_index * 2 + 1,
                column=0,
                sticky="ew",
            )

        warning = ctk.CTkFrame(
            self.body,
            fg_color="#422006",
            corner_radius=10,
        )
        warning.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=25,
            pady=(0, 20),
        )

        ctk.CTkLabel(
            warning,
            text=(
                "Gerçek ve yetkili firma bilgilerini girin. "
                "Kaydetme işlemi audit kaydı oluşturur ve firma "
                "kimliği daha sonra lisansa bağlanır."
            ),
            text_color="#FBBF24",
            font=("Arial", 12, "bold"),
            justify="left",
            wraplength=680,
        ).pack(
            anchor="w",
            padx=16,
            pady=14,
        )

        ctk.CTkCheckBox(
            self.footer,
            text=(
                "Bilgileri kontrol ettim ve gerçek firma "
                "profilinin oluşturulmasını onaylıyorum."
            ),
            variable=self.confirmed,
            onvalue=True,
            offvalue=False,
            font=("Arial", 12, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=15,
            pady=(15, 8),
        )

        ctk.CTkButton(
            self.footer,
            text="VAZGEÇ",
            height=44,
            fg_color="#525252",
            command=self.destroy,
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(15, 6),
            pady=(5, 15),
        )

        ctk.CTkButton(
            self.footer,
            text="FİRMA PROFİLİNİ OLUŞTUR",
            height=44,
            command=self._save,
        ).grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(6, 15),
            pady=(5, 15),
        )

    def _save(self):
        if not self.confirmed.get():
            messagebox.showwarning(
                "Açık Onay Gerekli",
                (
                    "Firma profilini oluşturmak için bilgileri "
                    "kontrol ettiğinizi açıkça onaylayın."
                ),
                parent=self,
            )
            return

        company = {
            key: variable.get()
            for key, variable in self.values.items()
        }

        if not messagebox.askyesno(
            "Firma Profilini Oluştur",
            (
                "Gerçek firma profili oluşturulsun ve "
                "lisans bağlantısında kullanılsın mı?"
            ),
            parent=self,
        ):
            return

        conn = get_connection()

        try:
            profile = legacy_firma_profilini_olustur(
                conn,
                company,
                kullanici=self.kullanici,
                oturum_id=self.oturum_id,
            )
        except Exception as exc:
            messagebox.showerror(
                "Firma Profili Oluşturulamadı",
                str(exc),
                parent=self,
            )
            return
        finally:
            conn.close()

        messagebox.showinfo(
            "Firma Profili Hazır",
            (
                profile["kisa_ad"]
                + " firma profili güvenli şekilde oluşturuldu."
            ),
            parent=self,
        )

        self.destroy()

        if self.on_complete is not None:
            self.on_complete()
