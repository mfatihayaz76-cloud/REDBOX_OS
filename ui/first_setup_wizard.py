from tkinter import messagebox

import customtkinter as ctk

from database.db import get_connection
from database.first_setup_engine import ilk_kurulumu_tamamla


STEP_TITLES = (
    "Kullanım Modu",
    "Firma Bilgileri",
    "Ana Tesis",
    "İlk Yönetici",
    "Son Kontrol",
)


class FirstSetupWizard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_complete,
        oturum_id=None,
    ):
        super().__init__(
            master,
            fg_color="transparent",
        )
        self.on_complete = on_complete
        self.oturum_id = oturum_id
        self.current_step = 0
        self.field_values = {}
        self.kullanim_modu = ctk.StringVar(value="GERCEK")
        self.tesis_turu = ctk.StringVar(value="URETIM")
        self.acik_onay = ctk.BooleanVar(value=False)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self.content = None
        self._create_content()

        self.navigation = ctk.CTkFrame(
            self,
            fg_color="transparent",
        )
        self.navigation.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(4, 0),
        )
        self.navigation.grid_columnconfigure(1, weight=1)

        self.confirmation_checkbox = ctk.CTkCheckBox(
            self.navigation,
            text=(
                "Bilgileri kontrol ettim ve kurulum "
                "işlemini açıkça onaylıyorum."
            ),
            variable=self.acik_onay,
            onvalue=True,
            offvalue=False,
        )
        self.confirmation_checkbox.grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="w",
            padx=8,
            pady=(0, 12),
        )
        self.confirmation_checkbox.grid_remove()

        self.back_button = ctk.CTkButton(
            self.navigation,
            text="GERİ",
            width=110,
            command=self._previous_step,
        )
        self.back_button.grid(row=1, column=0, padx=(0, 8))

        self.next_button = ctk.CTkButton(
            self.navigation,
            text="DEVAM ET",
            height=42,
            font=("Arial", 13, "bold"),
            command=self._next_step,
        )
        self.next_button.grid(
            row=1,
            column=2,
            sticky="e",
        )

        self._show_step()

    def _build_header(self):
        self.step_label = ctk.CTkLabel(
            self,
            text="",
            font=("Arial", 12, "bold"),
            text_color="#60A5FA",
        )
        self.step_label.grid(
            row=0,
            column=0,
            pady=(0, 3),
        )

        self.title_label = ctk.CTkLabel(
            self,
            text="",
            font=("Arial", 22, "bold"),
        )
        self.title_label.grid(
            row=1,
            column=0,
            pady=(0, 4),
        )

    def _create_content(self):
        if self.content is not None:
            self.content.destroy()

        content_class = (
            ctk.CTkScrollableFrame
            if self.current_step == 1
            else ctk.CTkFrame
        )
        self.content = content_class(
            self,
            fg_color="transparent",
            corner_radius=10,
        )
        self.content.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=8,
            pady=(6, 8),
        )
        self.content.grid_columnconfigure(0, weight=1)

    def _configure_confirmation(self):
        if self.current_step == len(STEP_TITLES) - 1:
            self.confirmation_checkbox.grid()
        else:
            self.confirmation_checkbox.grid_remove()

    def _show_step(self):
        self._create_content()
        self._configure_confirmation()
        self.step_label.configure(
            text=(
                f"ADIM {self.current_step + 1} / "
                f"{len(STEP_TITLES)}"
            )
        )
        self.title_label.configure(
            text=STEP_TITLES[self.current_step]
        )
        self.back_button.configure(
            state=(
                "disabled"
                if self.current_step == 0
                else "normal"
            )
        )
        self.next_button.configure(
            text=(
                "KURULUMU TAMAMLA"
                if self.current_step == len(STEP_TITLES) - 1
                else "DEVAM ET"
            )
        )

        builders = (
            self._build_mode_step,
            self._build_company_step,
            self._build_facility_step,
            self._build_admin_step,
            self._build_review_step,
        )
        builders[self.current_step]()

    def _description(self, text):
        ctk.CTkLabel(
            self.content,
            text=text,
            wraplength=560,
            justify="left",
            text_color="#9CA3AF",
            font=("Arial", 12),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(4, 18),
        )

    def _entry(
        self,
        key,
        label,
        row,
        placeholder="",
        show=None,
        default="",
    ):
        ctk.CTkLabel(
            self.content,
            text=label,
            anchor="w",
            font=("Arial", 12, "bold"),
        ).grid(
            row=row,
            column=0,
            sticky="ew",
            pady=(3, 2),
        )

        if key not in self.field_values:
            self.field_values[key] = ctk.StringVar(
                value=default,
            )

        entry = ctk.CTkEntry(
            self.content,
            placeholder_text=placeholder,
            height=38,
            show=show,
            textvariable=self.field_values[key],
        )
        entry.grid(
            row=row + 1,
            column=0,
            sticky="ew",
            pady=(0, 3),
        )
        return row + 2

    def _build_mode_step(self):
        self._description(
            "Kurulum türünü seçin. GERÇEK kullanım canlı "
            "işletme kayıtları içindir. DEMO kullanım yalnız "
            "tanıtım ve eğitim ortamları içindir."
        )

        ctk.CTkSegmentedButton(
            self.content,
            values=("GERCEK", "DEMO"),
            variable=self.kullanim_modu,
            height=44,
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            pady=8,
        )

        ctk.CTkLabel(
            self.content,
            text=(
                "Seçilen kullanım modu kurulum kaydına "
                "kalıcı olarak işlenir."
            ),
            wraplength=560,
            justify="left",
            text_color="#F59E0B",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            pady=(12, 0),
        )

    def _build_company_step(self):
        self._description(
            "Yasal firma kimliğini ve kurumsal iletişim "
            "bilgilerini girin."
        )
        row = 1
        fields = (
            ("firma_ticari_unvan", "Ticari Unvan *", ""),
            ("firma_kisa_ad", "Firma Kısa Adı *", ""),
            ("firma_vergi_dairesi", "Vergi Dairesi", ""),
            ("firma_vergi_no", "Vergi Numarası", ""),
            ("firma_ulke", "Ülke", "Türkiye"),
            ("firma_il", "İl", ""),
            ("firma_ilce", "İlçe", ""),
            ("firma_adres", "Açık Adres", ""),
            ("firma_telefon", "Telefon", ""),
            ("firma_eposta", "E-posta", ""),
        )
        for key, label, default in fields:
            row = self._entry(
                key,
                label,
                row,
                default=default,
            )

    def _build_facility_step(self):
        self._description(
            "Ana tesis kimliğini girin. İlk kurulumda tesis "
            "adres ve iletişim bilgileri firma profilinden "
            "otomatik alınacaktır."
        )
        row = 1
        row = self._entry(
            "tesis_kodu",
            "Tesis Kodu *",
            row,
            placeholder="Örnek: IST-01",
        )
        row = self._entry(
            "tesis_adi",
            "Tesis Adı *",
            row,
        )

        ctk.CTkLabel(
            self.content,
            text="Tesis Türü *",
            anchor="w",
            font=("Arial", 12, "bold"),
        ).grid(row=row, column=0, sticky="ew", pady=(5, 3))
        ctk.CTkOptionMenu(
            self.content,
            values=("URETIM", "DEPO", "MERKEZ", "DIGER"),
            variable=self.tesis_turu,
            height=40,
        ).grid(
            row=row + 1,
            column=0,
            sticky="ew",
            pady=(0, 3),
        )
        row += 2

        ctk.CTkLabel(
            self.content,
            text=(
                "Adres ve iletişim: Firma profiliyle aynı"
            ),
            anchor="w",
            text_color="#60A5FA",
            font=("Arial", 12, "bold"),
        ).grid(
            row=row,
            column=0,
            sticky="ew",
            pady=(16, 4),
        )

    def _build_admin_step(self):
        self._description(
            "İlk yönetici tüm temel üretim, HACCP, kalite "
            "ve sistem yetkileriyle oluşturulacaktır."
        )
        row = 1
        row = self._entry(
            "yonetici_ad_soyad",
            "Ad Soyad *",
            row,
        )
        row = self._entry(
            "yonetici_gorev",
            "Görev",
            row,
            default="Sistem Yöneticisi",
        )
        row = self._entry(
            "yonetici_kullanici_adi",
            "Kullanıcı Adı *",
            row,
        )
        row = self._entry(
            "yonetici_parola",
            "Parola *",
            row,
            placeholder="En az 8 karakter",
            show="●",
        )
        self._entry(
            "yonetici_parola_tekrar",
            "Parola Tekrar *",
            row,
            show="●",
        )

    def _build_review_step(self):
        self._description(
            "Bilgileri kontrol edin. Açık onay verilmeden "
            "firma, tesis veya yönetici kaydı oluşturulmaz."
        )

        values = self._collect_data()
        summary = (
            f"Kullanım modu: {values['kullanim_modu']}\n\n"
            f"Firma: {values['firma']['ticari_unvan']}\n"
            f"Kısa ad: {values['firma']['kisa_ad']}\n\n"
            f"Ana tesis: {values['tesis']['tesis_adi']}\n"
            f"Tesis kodu: {values['tesis']['tesis_kodu']}\n"
            f"Tesis türü: {values['tesis']['tesis_turu']}\n\n"
            f"İlk yönetici: {values['yonetici']['ad_soyad']}\n"
            f"Kullanıcı adı: "
            f"{values['yonetici']['kullanici_adi']}"
        )

        ctk.CTkLabel(
            self.content,
            text=summary,
            justify="left",
            anchor="w",
            wraplength=780,
            font=("Arial", 14),
        ).grid(
            row=1,
            column=0,
            sticky="ew",
            padx=12,
            pady=12,
        )


    def _value(self, key):
        variable = self.field_values.get(key)
        return variable.get().strip() if variable else ""

    def _collect_data(self):
        return {
            "kullanim_modu": self.kullanim_modu.get(),
            "firma": {
                "ticari_unvan": self._value(
                    "firma_ticari_unvan"
                ),
                "kisa_ad": self._value("firma_kisa_ad"),
                "vergi_dairesi": self._value(
                    "firma_vergi_dairesi"
                ),
                "vergi_no": self._value("firma_vergi_no"),
                "ulke": self._value("firma_ulke"),
                "il": self._value("firma_il"),
                "ilce": self._value("firma_ilce"),
                "adres": self._value("firma_adres"),
                "telefon": self._value("firma_telefon"),
                "eposta": self._value("firma_eposta"),
            },
            "tesis": {
                "tesis_kodu": self._value("tesis_kodu"),
                "tesis_adi": self._value("tesis_adi"),
                "tesis_turu": self.tesis_turu.get(),
                "ulke": self._value("firma_ulke"),
                "il": self._value("firma_il"),
                "ilce": self._value("firma_ilce"),
                "adres": self._value("firma_adres"),
                "telefon": self._value("firma_telefon"),
                "eposta": self._value("firma_eposta"),
            },
            "yonetici": {
                "ad_soyad": self._value(
                    "yonetici_ad_soyad"
                ),
                "gorev": self._value("yonetici_gorev"),
                "kullanici_adi": self._value(
                    "yonetici_kullanici_adi"
                ),
                "parola": self._value("yonetici_parola"),
            },
        }

    def _validate_step(self):
        required_by_step = {
            1: (
                ("firma_ticari_unvan", "Ticari unvan"),
                ("firma_kisa_ad", "Firma kısa adı"),
            ),
            2: (
                ("tesis_kodu", "Tesis kodu"),
                ("tesis_adi", "Tesis adı"),
            ),
            3: (
                ("yonetici_ad_soyad", "Yönetici adı soyadı"),
                (
                    "yonetici_kullanici_adi",
                    "Kullanıcı adı",
                ),
                ("yonetici_parola", "Parola"),
                (
                    "yonetici_parola_tekrar",
                    "Parola tekrarı",
                ),
            ),
        }

        for key, label in required_by_step.get(
            self.current_step,
            (),
        ):
            if not self._value(key):
                messagebox.showwarning(
                    "Eksik Bilgi",
                    f"{label} zorunludur.",
                )
                return False

        if self.current_step == 3:
            parola = self._value("yonetici_parola")
            tekrar = self._value(
                "yonetici_parola_tekrar"
            )
            if parola != tekrar:
                messagebox.showwarning(
                    "Parola Hatası",
                    "Parolalar birbiriyle aynı değil.",
                )
                return False

        return True

    def _next_step(self):
        if not self._validate_step():
            return

        if self.current_step < len(STEP_TITLES) - 1:
            self.current_step += 1
            self._show_step()
            return

        self._complete_setup()

    def _previous_step(self):
        if self.current_step == 0:
            return
        self.current_step -= 1
        self._show_step()

    def _complete_setup(self):
        if not self.acik_onay.get():
            messagebox.showwarning(
                "Açık Onay Gerekli",
                "Kurulumu tamamlamak için açık onay verin.",
            )
            return

        if not messagebox.askyesno(
            "Kurulumu Tamamla",
            "Firma, ana tesis ve ilk yönetici hesabı "
            "oluşturulsun mu?",
        ):
            return

        data = self._collect_data()
        conn = get_connection()

        try:
            result = ilk_kurulumu_tamamla(
                conn,
                data["firma"],
                data["tesis"],
                data["yonetici"],
                kullanim_modu=data["kullanim_modu"],
                oturum_id=self.oturum_id,
            )
        except Exception as exc:
            messagebox.showerror(
                "Kurulum Tamamlanamadı",
                str(exc),
            )
            return
        finally:
            conn.close()

        messagebox.showinfo(
            "Kurulum Tamamlandı",
            "Firma, ana tesis ve ilk yönetici hesabı "
            "güvenli şekilde oluşturuldu.",
        )
        self.on_complete(result)
