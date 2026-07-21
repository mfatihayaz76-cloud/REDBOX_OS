import json
import subprocess
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from cryptography.hazmat.primitives import serialization

from database.licensing_engine import PRODUCT_CODE
from tools.license_issuer import lisans_anahtari_uret


DEFAULT_KEY_ID = "REDBOX-PROD-2813E117AB41"
DEFAULT_AUTHORITY = (
    Path.home() / "REDBOX_OS_LICENSE_AUTHORITY"
)


def _is_sha256(value):
    if not isinstance(value, str) or len(value) != 64:
        return False

    try:
        int(value, 16)
    except ValueError:
        return False

    return value == value.lower()


def load_license_request(path):
    request_path = Path(path).expanduser().resolve()

    if not request_path.is_file():
        raise FileNotFoundError(
            "Lisans talep dosyası bulunamadı."
        )

    try:
        value = json.loads(
            request_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Lisans talep dosyası bozuk veya geçersiz."
        ) from exc

    if not isinstance(value, dict):
        raise ValueError(
            "Lisans talebi JSON nesnesi olmalıdır."
        )

    if value.get("talep_surumu") != 1:
        raise ValueError(
            "Lisans talep sürümü desteklenmiyor."
        )

    if value.get("urun_kodu") != PRODUCT_CODE:
        raise ValueError(
            "Talep farklı veya geçersiz bir ürüne ait."
        )

    company_hash = value.get(
        "firma_parmak_izi_sha256"
    )
    device_hash = value.get(
        "cihaz_parmak_izi_sha256"
    )

    if not _is_sha256(company_hash):
        raise ValueError(
            "Firma parmak izi geçersiz."
        )

    if not _is_sha256(device_hash):
        raise ValueError(
            "Cihaz parmak izi geçersiz."
        )

    return value


def _encrypted_key_path(authority_path, key_id):
    authority = Path(
        authority_path
    ).expanduser().resolve()

    path = (
        authority
        / "private"
        / f"{key_id}_ed25519_private_encrypted.pem"
    )

    if not path.is_file():
        raise FileNotFoundError(
            "Şifreli lisans imzalama anahtarı bulunamadı."
        )

    return path


def issue_license_file(
    request_path,
    output_path,
    authority_path,
    key_id,
    license_type,
    start_date,
    end_date,
    grace_days,
    password,
):
    request = load_license_request(request_path)
    output = Path(output_path).expanduser().resolve()

    if output.exists():
        raise FileExistsError(
            "Çıktı dosyası zaten mevcut; üzerine yazılmadı."
        )

    if not output.name.lower().endswith(".rbx1"):
        raise ValueError(
            "Çıktı dosyasının uzantısı .rbx1 olmalıdır."
        )

    if not password:
        raise ValueError(
            "İmzalama anahtarı parolası boş olamaz."
        )

    key_path = _encrypted_key_path(
        authority_path,
        key_id,
    )

    try:
        signing_key = (
            serialization.load_pem_private_key(
                key_path.read_bytes(),
                password=str(password).encode("utf-8"),
            )
        )
    except Exception as exc:
        raise ValueError(
            "İmzalama anahtarı açılamadı. "
            "Parolayı kontrol edin."
        ) from exc

    token, payload = lisans_anahtari_uret(
        request,
        signing_key,
        key_id,
        license_type,
        start_date,
        bitis_tarihi=end_date,
        grace_period_gun=grace_days,
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output.write_text(
        token + "\n",
        encoding="utf-8",
    )

    return payload


class LicenseManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("REDBOX — Lisans Yöneticisi")
        self.geometry("1040x760")
        self.minsize(900, 680)

        self.request_path = None
        self.request_data = None
        self.last_output = None

        self.license_type = ctk.StringVar(
            value="SURESIZ"
        )
        self.start_date = ctk.StringVar(
            value=date.today().isoformat()
        )
        self.end_date = ctk.StringVar(value="")
        self.grace_days = ctk.StringVar(value="7")
        self.password = ctk.StringVar(value="")

        self._build_ui()
        self._update_type_state()

    def _build_ui(self):
        header = ctk.CTkFrame(
            self,
            corner_radius=0,
            height=105,
            fg_color="#132238",
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="REDBOX LİSANS YÖNETİCİSİ",
            font=ctk.CTkFont(
                size=27,
                weight="bold",
            ),
        ).pack(
            anchor="w",
            padx=34,
            pady=(22, 4),
        )

        ctk.CTkLabel(
            header,
            text=(
                "Müşteri talebinden güvenli ve imzalı "
                "RBX1 lisansı oluşturun"
            ),
            text_color="#b9d7ea",
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w", padx=34)

        body = ctk.CTkScrollableFrame(
            self,
            corner_radius=0,
        )
        body.pack(
            fill="both",
            expand=True,
            padx=22,
            pady=18,
        )

        self._request_card(body)
        self._license_card(body)
        self._security_card(body)

        footer = ctk.CTkFrame(
            self,
            corner_radius=0,
            height=78,
        )
        footer.pack(fill="x")
        footer.pack_propagate(False)

        self.show_button = ctk.CTkButton(
            footer,
            text="DOSYAYI FINDER’DA GÖSTER",
            state="disabled",
            command=self._show_output,
            height=42,
        )
        self.show_button.pack(
            side="left",
            padx=(25, 10),
            pady=18,
        )

        ctk.CTkButton(
            footer,
            text="KAPAT",
            fg_color="#555555",
            hover_color="#444444",
            command=self.destroy,
            height=42,
            width=180,
        ).pack(
            side="right",
            padx=25,
            pady=18,
        )

    def _request_card(self, parent):
        card = ctk.CTkFrame(
            parent,
            corner_radius=12,
        )
        card.pack(
            fill="x",
            padx=8,
            pady=(8, 12),
        )

        ctk.CTkLabel(
            card,
            text="1. MÜŞTERİ LİSANS TALEBİ",
            font=ctk.CTkFont(
                size=18,
                weight="bold",
            ),
        ).pack(
            anchor="w",
            padx=22,
            pady=(18, 6),
        )

        ctk.CTkLabel(
            card,
            text=(
                "Müşterinin e-postayla gönderdiği "
                "redbox_lisans_talebi_*.json dosyasını seçin."
            ),
            text_color="#b7c5d1",
        ).pack(
            anchor="w",
            padx=22,
            pady=(0, 12),
        )

        ctk.CTkButton(
            card,
            text="LİSANS TALEBİ SEÇ",
            command=self._select_request,
            height=42,
        ).pack(
            fill="x",
            padx=22,
            pady=(0, 12),
        )

        self.request_label = ctk.CTkLabel(
            card,
            text="Henüz talep seçilmedi.",
            justify="left",
            anchor="w",
            wraplength=880,
        )
        self.request_label.pack(
            fill="x",
            padx=22,
            pady=(0, 18),
        )

    def _license_card(self, parent):
        card = ctk.CTkFrame(
            parent,
            corner_radius=12,
        )
        card.pack(
            fill="x",
            padx=8,
            pady=12,
        )

        ctk.CTkLabel(
            card,
            text="2. LİSANS AYARLARI",
            font=ctk.CTkFont(
                size=18,
                weight="bold",
            ),
        ).pack(
            anchor="w",
            padx=22,
            pady=(18, 12),
        )

        form = ctk.CTkFrame(
            card,
            fg_color="transparent",
        )
        form.pack(
            fill="x",
            padx=22,
            pady=(0, 10),
        )
        form.grid_columnconfigure(
            (0, 1, 2),
            weight=1,
        )

        ctk.CTkLabel(
            form,
            text="Lisans türü",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 5),
        )

        self.type_selector = ctk.CTkSegmentedButton(
            form,
            values=["SÜRESİZ", "SÜRELİ"],
            command=self._type_changed,
        )
        self.type_selector.grid(
            row=1,
            column=0,
            sticky="ew",
            padx=(0, 12),
        )
        self.type_selector.set("SÜRESİZ")

        ctk.CTkLabel(
            form,
            text="Başlangıç tarihi (YYYY-AA-GG)",
        ).grid(
            row=0,
            column=1,
            sticky="w",
            pady=(0, 5),
        )

        self.start_entry = ctk.CTkEntry(
            form,
            textvariable=self.start_date,
            height=38,
        )
        self.start_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=6,
        )

        ctk.CTkLabel(
            form,
            text="Bitiş tarihi (YYYY-AA-GG)",
        ).grid(
            row=0,
            column=2,
            sticky="w",
            pady=(0, 5),
        )

        self.end_entry = ctk.CTkEntry(
            form,
            textvariable=self.end_date,
            height=38,
        )
        self.end_entry.grid(
            row=1,
            column=2,
            sticky="ew",
            padx=(12, 0),
        )

        second = ctk.CTkFrame(
            card,
            fg_color="transparent",
        )
        second.pack(
            fill="x",
            padx=22,
            pady=10,
        )
        second.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            second,
            text="Ek erişim günü",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 12),
        )

        ctk.CTkOptionMenu(
            second,
            values=[
                str(value)
                for value in range(0, 31)
            ],
            variable=self.grace_days,
            width=120,
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 12),
        )

        ctk.CTkLabel(
            second,
            text="İmzalama anahtarı parolası",
        ).grid(
            row=0,
            column=1,
            sticky="w",
        )

        self.password_entry = ctk.CTkEntry(
            second,
            textvariable=self.password,
            show="●",
            placeholder_text=(
                "Parola ekranda gösterilmez ve kaydedilmez"
            ),
            height=38,
        )
        self.password_entry.grid(
            row=1,
            column=1,
            sticky="ew",
        )

        self.issue_button = ctk.CTkButton(
            card,
            text="İMZALI LİSANS OLUŞTUR",
            command=self._issue,
            height=48,
            font=ctk.CTkFont(
                size=15,
                weight="bold",
            ),
            fg_color="#1f9d55",
            hover_color="#187a43",
        )
        self.issue_button.pack(
            fill="x",
            padx=22,
            pady=(10, 20),
        )

    def _security_card(self, parent):
        card = ctk.CTkFrame(
            parent,
            corner_radius=12,
            fg_color="#2f251b",
        )
        card.pack(
            fill="x",
            padx=8,
            pady=12,
        )

        ctk.CTkLabel(
            card,
            text="GÜVENLİK KURALI",
            text_color="#f5b041",
            font=ctk.CTkFont(
                size=15,
                weight="bold",
            ),
        ).pack(
            anchor="w",
            padx=22,
            pady=(16, 5),
        )

        ctk.CTkLabel(
            card,
            text=(
                "Müşteriye yalnızca oluşan .rbx1 dosyasını "
                "gönderin. Lisans otoritesi klasörünü, "
                "şifreli imzalama anahtarını veya parolanızı "
                "hiçbir zaman paylaşmayın."
            ),
            justify="left",
            wraplength=880,
            text_color="#f4e6d4",
        ).pack(
            anchor="w",
            padx=22,
            pady=(0, 16),
        )

    def _select_request(self):
        selected = filedialog.askopenfilename(
            title="Müşteri lisans talebini seçin",
            filetypes=[
                ("REDBOX lisans talebi", "*.json"),
                ("JSON dosyaları", "*.json"),
            ],
        )

        if not selected:
            return

        try:
            request = load_license_request(selected)
        except Exception as exc:
            messagebox.showerror(
                "Geçersiz Lisans Talebi",
                str(exc),
                parent=self,
            )
            return

        self.request_path = Path(selected)
        self.request_data = request

        company_hash = request[
            "firma_parmak_izi_sha256"
        ]
        device_hash = request[
            "cihaz_parmak_izi_sha256"
        ]

        self.request_label.configure(
            text=(
                f"DOSYA: {self.request_path.name}\n"
                f"ÜRÜN: {request['urun_kodu']}\n"
                f"FİRMA PARMAK İZİ: "
                f"{company_hash[:16]}…{company_hash[-8:]}\n"
                f"CİHAZ PARMAK İZİ: "
                f"{device_hash[:16]}…{device_hash[-8:]}\n"
                "DURUM: Talep doğrulandı"
            ),
            text_color="#6ee7a8",
        )

    def _type_changed(self, value):
        self.license_type.set(
            "SURESIZ"
            if value == "SÜRESİZ"
            else "SURELI"
        )
        self._update_type_state()

    def _update_type_state(self):
        if self.license_type.get() == "SURELI":
            self.end_entry.configure(state="normal")
        else:
            self.end_date.set("")
            self.end_entry.configure(state="disabled")

    def _validate_dates(self):
        try:
            start = date.fromisoformat(
                self.start_date.get().strip()
            )
        except ValueError as exc:
            raise ValueError(
                "Başlangıç tarihi YYYY-AA-GG olmalıdır."
            ) from exc

        if self.license_type.get() == "SURELI":
            try:
                end = date.fromisoformat(
                    self.end_date.get().strip()
                )
            except ValueError as exc:
                raise ValueError(
                    "Bitiş tarihi YYYY-AA-GG olmalıdır."
                ) from exc

            if end < start:
                raise ValueError(
                    "Bitiş tarihi başlangıçtan önce olamaz."
                )

            return start.isoformat(), end.isoformat()

        return start.isoformat(), None

    def _suggested_name(self):
        request_id = (
            self.request_path.stem[-12:]
            if self.request_path
            else "MUSTERI"
        )
        type_label = self.license_type.get()
        today = date.today().strftime("%Y%m%d")

        return (
            f"REDBOX_OS_{request_id}_"
            f"{type_label}_{today}.rbx1"
        )

    def _issue(self):
        if self.request_path is None:
            messagebox.showwarning(
                "Talep Seçilmedi",
                "Önce müşteri lisans talep dosyasını seçin.",
                parent=self,
            )
            return

        try:
            start_value, end_value = (
                self._validate_dates()
            )

            if not self.password.get():
                raise ValueError(
                    "İmzalama anahtarı parolasını girin."
                )
        except ValueError as exc:
            messagebox.showerror(
                "Eksik veya Geçersiz Bilgi",
                str(exc),
                parent=self,
            )
            return

        output = filedialog.asksaveasfilename(
            title="İmzalı lisansı kaydedin",
            initialdir=str(Path.home() / "Desktop"),
            initialfile=self._suggested_name(),
            defaultextension=".rbx1",
            filetypes=[
                ("REDBOX imzalı lisans", "*.rbx1"),
            ],
        )

        if not output:
            return

        confirmed = messagebox.askyesno(
            "Lisansı Oluştur",
            (
                f"Lisans türü: "
                f"{self.license_type.get()}\n"
                f"Başlangıç: {start_value}\n"
                f"Bitiş: {end_value or 'YOK'}\n\n"
                "Bu müşteri ve cihaz için imzalı "
                "lisans oluşturulsun mu?"
            ),
            parent=self,
        )

        if not confirmed:
            return

        self.issue_button.configure(state="disabled")

        try:
            payload = issue_license_file(
                request_path=self.request_path,
                output_path=output,
                authority_path=DEFAULT_AUTHORITY,
                key_id=DEFAULT_KEY_ID,
                license_type=self.license_type.get(),
                start_date=start_value,
                end_date=end_value,
                grace_days=int(
                    self.grace_days.get()
                ),
                password=self.password.get(),
            )
        except Exception as exc:
            messagebox.showerror(
                "Lisans Oluşturulamadı",
                str(exc),
                parent=self,
            )
            return
        finally:
            self.password.set("")
            self.issue_button.configure(state="normal")

        self.last_output = Path(output).resolve()
        self.show_button.configure(state="normal")

        messagebox.showinfo(
            "Lisans Oluşturuldu",
            (
                "İmzalı RBX1 lisansı başarıyla oluşturuldu.\n\n"
                f"Lisans UUID: {payload['lisans_uuid']}\n"
                f"Tür: {payload['lisans_turu']}\n"
                f"Dosya: {self.last_output.name}\n\n"
                "Müşteriye yalnızca bu .rbx1 "
                "dosyasını gönderin."
            ),
            parent=self,
        )

    def _show_output(self):
        if (
            self.last_output is None
            or not self.last_output.is_file()
        ):
            messagebox.showwarning(
                "Dosya Bulunamadı",
                "Oluşturulan lisans dosyası bulunamadı.",
                parent=self,
            )
            return

        subprocess.run(
            ["open", "-R", str(self.last_output)],
            check=False,
        )


def main():
    app = LicenseManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
