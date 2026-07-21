import json
import sqlite3
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from database.db import get_connection
from database.licensing_engine import (
    cihaz_parmak_izi_olustur,
    lisans_acik_anahtarlarini_yukle,
    lisans_erisim_karari,
    lisans_talep_bilgilerini_getir,
    lisansi_aktive_et,
)


class LicenseCenterWindow(ctk.CTkToplevel):
    STATUS_TEXTS = {
        "AKTIF": "AKTİF",
        "GRACE": "EK SÜRE",
        "GECIS_SURESI": "30 GÜNLÜK GEÇİŞ",
        "GECIS_SURESI_DOLDU": "GEÇİŞ SÜRESİ DOLDU",
        "DEMO_AKTIF": "30 GÜNLÜK DEMO AKTİF",
        "DEMO_SURESI_DOLDU": "DEMO SÜRESİ DOLDU",
        "DEMO_GECERSIZ": "DEMO GEÇERSİZ",
        "DEMO_YOK": "DEMO BAŞLATILMADI",
        "LISANS_GEREKLI": "LİSANS GEREKLİ",
        "LISANS_YOK": "LİSANS YOK",
        "GECERSIZ": "GEÇERSİZ",
        "SURESI_DOLDU": "SÜRESİ DOLDU",
        "ASKIDA": "ASKIDA",
        "IPTAL": "İPTAL",
        "ILK_KURULUM": "İLK KURULUM",
    }

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
        self.device = None
        self.public_keys = None
        self.request_data = None
        self.access_decision = None
        self.confirmed = ctk.BooleanVar(value=False)

        self.title("REDBOX OS — Lisans Merkezi")
        self.geometry("900x780")
        self.minsize(760, 640)
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

        self._header()
        self._status_card()
        self._request_card()
        self._activation_card()
        self._footer_buttons()
        self._load_state()

    def _header(self):
        ctk.CTkLabel(
            self.body,
            text="LİSANS MERKEZİ",
            font=("Arial", 27, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=25,
            pady=(25, 5),
        )

        ctk.CTkLabel(
            self.body,
            text=(
                "REDBOX OS lisans durumunu görüntüleyin, bu cihaz "
                "için lisans talebi oluşturun veya imzalı çevrimdışı "
                "lisansı güvenli şekilde aktive edin."
            ),
            font=("Arial", 13),
            text_color="#A3A3A3",
            justify="left",
            wraplength=790,
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=25,
            pady=(0, 18),
        )

    def _status_card(self):
        card = ctk.CTkFrame(self.body)
        card.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=25,
            pady=(0, 14),
        )
        card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            card,
            text="LİSANS DURUMU",
            font=("Arial", 15, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            padx=18,
            pady=(16, 10),
        )

        self.status_value = ctk.CTkLabel(
            card,
            text="KONTROL EDİLİYOR",
            font=("Arial", 21, "bold"),
            text_color="#60A5FA",
        )
        self.status_value.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
            padx=18,
            pady=(0, 8),
        )

        self.status_detail = ctk.CTkLabel(
            card,
            text="",
            justify="left",
            anchor="w",
            wraplength=650,
            text_color="#D4D4D4",
        )
        self.status_detail.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=18,
            pady=(0, 16),
        )

    def _request_card(self):
        card = ctk.CTkFrame(self.body)
        card.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=25,
            pady=(0, 14),
        )
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="LİSANS TALEBİ",
            font=("Arial", 15, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=18,
            pady=(16, 5),
        )

        ctk.CTkLabel(
            card,
            text=(
                "Talep dosyası firma ve cihazın yalnız SHA-256 "
                "parmak izlerini içerir. Ham cihaz kimliği dışa "
                "aktarılmaz."
            ),
            justify="left",
            wraplength=780,
            text_color="#A3A3A3",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=18,
            pady=(0, 10),
        )

        self.device_label = ctk.CTkLabel(
            card,
            text="CİHAZ PARMAK İZİ: hazırlanıyor",
            font=("Arial", 12, "bold"),
            anchor="w",
        )
        self.device_label.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 10),
        )

        self.export_button = ctk.CTkButton(
            card,
            text="LİSANS TALEBİNİ DIŞA AKTAR",
            height=42,
            command=self._export_request,
        )
        self.export_button.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 16),
        )

    def _activation_card(self):
        card = ctk.CTkFrame(self.body)
        card.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=25,
            pady=(0, 20),
        )
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="ÇEVRİMDIŞI LİSANS AKTİVASYONU",
            font=("Arial", 15, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=18,
            pady=(16, 5),
        )

        ctk.CTkLabel(
            card,
            text=(
                "Yetkili REDBOX lisans otoritesinden alınan RBX1 "
                "lisans anahtarını aşağıdaki alana yapıştırın."
            ),
            justify="left",
            wraplength=780,
            text_color="#A3A3A3",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=18,
            pady=(0, 10),
        )

        self.license_input = ctk.CTkTextbox(
            card,
            height=110,
            wrap="word",
        )
        self.license_input.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 12),
        )

        ctk.CTkCheckBox(
            card,
            text=(
                "Firma ve cihaz bilgilerimi kontrol ettim; imzalı "
                "lisansın bu kurulum için aktive edilmesini onaylıyorum."
            ),
            variable=self.confirmed,
            onvalue=True,
            offvalue=False,
            font=("Arial", 12, "bold"),
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=18,
            pady=(0, 12),
        )

        self.activation_button = ctk.CTkButton(
            card,
            text="İMZALI LİSANSI AKTİVE ET",
            height=44,
            fg_color="#15803D",
            hover_color="#166534",
            command=self._activate,
        )
        self.activation_button.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=18,
            pady=(0, 16),
        )

    def _footer_buttons(self):
        ctk.CTkButton(
            self.footer,
            text="DURUMU YENİLE",
            height=44,
            command=self._load_state,
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(15, 6),
            pady=15,
        )

        ctk.CTkButton(
            self.footer,
            text="KAPAT",
            height=44,
            fg_color="#525252",
            command=self.destroy,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(6, 15),
            pady=15,
        )

    def _set_unavailable(self, title, detail):
        self.status_value.configure(
            text=title,
            text_color="#F59E0B",
        )
        self.status_detail.configure(text=detail)
        self.export_button.configure(state="disabled")
        self.activation_button.configure(state="disabled")

    def _load_state(self):
        self.request_data = None
        self.access_decision = None
        self.export_button.configure(state="normal")
        self.activation_button.configure(state="normal")

        try:
            self.device = cihaz_parmak_izi_olustur()
            self.public_keys = lisans_acik_anahtarlarini_yukle()
        except Exception as exc:
            self._set_unavailable(
                "LİSANS ALTYAPISI HAZIR DEĞİL",
                str(exc),
            )
            return

        device_hash = self.device["cihaz_parmak_izi_sha256"]
        self.device_label.configure(
            text=(
                "CİHAZ PARMAK İZİ: "
                + device_hash[:16].upper()
                + "…"
            )
        )

        conn = get_connection()
        try:
            self.request_data = lisans_talep_bilgilerini_getir(
                conn,
                cihaz_bilgisi=self.device,
            )
            self.access_decision = lisans_erisim_karari(
                conn,
                self.public_keys,
                device_hash,
            )
        except sqlite3.OperationalError:
            self._set_unavailable(
                "MIGRATION 12 BEKLİYOR",
                (
                    "Lisans tabloları henüz bu veritabanında hazır "
                    "değil. Kontrollü Migration 12 tamamlanmadan "
                    "aktivasyon yapılmaz."
                ),
            )
            return
        except Exception as exc:
            self._set_unavailable(
                "LİSANS DURUMU OKUNAMADI",
                str(exc),
            )
            return
        finally:
            conn.close()

        if not self.request_data.get("hazir"):
            reason = self.request_data.get("neden_kodu")
            if reason == "FIRMA_PROFILI_GEREKLI":
                self._set_unavailable(
                    "FİRMA PROFİLİ GEREKLİ",
                    (
                        "Lisans talebi ve aktivasyonundan önce gerçek "
                        "firma profilini Sistem Yönetim Merkezi "
                        "üzerinden tamamlayın."
                    ),
                )
            else:
                self._set_unavailable(
                    "FİRMA PROFİLİ HAZIR DEĞİL",
                    reason or "Firma profili doğrulanamadı.",
                )
            return

        status = self.access_decision.get("durum", "GECERSIZ")
        status_text = self.STATUS_TEXTS.get(status, status)
        allowed = self.access_decision.get("erisim_izni", False)
        color = "#22C55E" if allowed else "#EF4444"

        details = [
            "Firma: " + self.request_data["ticari_unvan"],
            (
                "Akış: "
                + self.access_decision.get("akis", "-")
            ),
            (
                "Neden kodu: "
                + self.access_decision.get("neden_kodu", "-")
            ),
        ]

        if "kalan_gun" in self.access_decision:
            remaining_label = (
                "Demo süresinde kalan gün: "
                if status == "DEMO_AKTIF"
                else "Geçiş süresinde kalan gün: "
            )
            details.append(
                remaining_label
                + str(self.access_decision["kalan_gun"])
            )

        if self.access_decision.get("bitis_zamani"):
            end_label = (
                "Demo bitiş zamanı: "
                if status.startswith("DEMO_")
                else "Geçiş bitiş zamanı: "
            )
            details.append(
                end_label
                + str(self.access_decision["bitis_zamani"])
            )

        if status == "DEMO_AKTIF":
            details.append(
                "Demo için aktivasyon kodu gerekmez. "
                "Ticari kullanıma geçerken imzalı RBX1 "
                "lisansı etkinleştirin."
            )

        payload = self.access_decision.get("payload") or {}
        if payload.get("lisans_turu"):
            details.append(
                "Lisans türü: " + payload["lisans_turu"]
            )
        if payload.get("bitis_tarihi"):
            details.append(
                "Lisans bitiş tarihi: "
                + payload["bitis_tarihi"]
            )

        self.status_value.configure(
            text=status_text,
            text_color=color,
        )
        self.status_detail.configure(
            text="\n".join(details)
        )

        if status in {"AKTIF", "GRACE"}:
            self.activation_button.configure(state="disabled")

    def _export_request(self):
        if not self.request_data or not self.request_data.get("hazir"):
            messagebox.showwarning(
                "Firma Profili Gerekli",
                (
                    "FIRMA_PROFILI_GEREKLI: Önce gerçek firma "
                    "profilini tamamlayın."
                ),
                parent=self,
            )
            return

        target = filedialog.asksaveasfilename(
            parent=self,
            title="Lisans Talep Dosyasını Kaydet",
            defaultextension=".json",
            initialfile=(
                "redbox_lisans_talebi_"
                + self.request_data["talep_uuid"]
                + ".json"
            ),
            filetypes=(("JSON dosyası", "*.json"),),
        )

        if not target:
            return

        try:
            Path(target).write_text(
                json.dumps(
                    self.request_data,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            messagebox.showerror(
                "Talep Dosyası Kaydedilemedi",
                str(exc),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Lisans Talebi Hazır",
            (
                "Lisans talep dosyası oluşturuldu. Dosyayı yalnız "
                "yetkili REDBOX lisans otoritesine iletin."
            ),
            parent=self,
        )

    def _activate(self):
        if not self.request_data or not self.request_data.get("hazir"):
            messagebox.showwarning(
                "Firma Profili Gerekli",
                (
                    "FIRMA_PROFILI_GEREKLI: Aktivasyondan önce "
                    "gerçek firma profilini tamamlayın."
                ),
                parent=self,
            )
            return

        if not self.confirmed.get():
            messagebox.showwarning(
                "Açık Onay Gerekli",
                (
                    "İmzalı lisansı aktive etmek için firma ve cihaz "
                    "bağlantısını açıkça onaylayın."
                ),
                parent=self,
            )
            return

        license_key = self.license_input.get(
            "1.0",
            "end",
        ).strip()

        if not license_key:
            messagebox.showwarning(
                "Lisans Anahtarı Gerekli",
                "İmzalı RBX1 lisans anahtarını girin.",
                parent=self,
            )
            return

        if not messagebox.askyesno(
            "Lisansı Aktive Et",
            (
                "İmzalı lisans bu firma ve cihaz için atomik olarak "
                "aktive edilsin mi?"
            ),
            parent=self,
        ):
            return

        conn = get_connection()
        try:
            result = lisansi_aktive_et(
                conn,
                license_key,
                self.public_keys,
                self.request_data["firma_id"],
                self.device["cihaz_parmak_izi_sha256"],
                kullanici=self.kullanici,
                oturum_id=self.oturum_id,
            )
        except Exception as exc:
            messagebox.showerror(
                "Lisans Aktivasyonu Başarısız",
                str(exc),
                parent=self,
            )
            return
        finally:
            conn.close()

        self.license_input.delete("1.0", "end")
        self.confirmed.set(False)

        messagebox.showinfo(
            "Lisans Aktive Edildi",
            (
                "Lisans güvenli şekilde aktive edildi. Durum: "
                + result["durum"]
            ),
            parent=self,
        )

        self._load_state()

        if self.on_complete is not None:
            self.on_complete()
