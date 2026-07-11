import customtkinter as ctk
from tkinter import messagebox
from datetime import datetime

from database.db import init_database, get_connection
from database.stock_engine import uretim_stok_isle

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

init_database()


class RedboxOS(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("REDBOX OS")
        self.geometry("1380x820")
        self.minsize(1180, 700)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=245, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)

        ctk.CTkLabel(
            self.sidebar,
            text="REDBOX OS",
            font=("Arial", 28, "bold")
        ).grid(row=0, column=0, padx=25, pady=(35, 5))

        ctk.CTkLabel(
            self.sidebar,
            text="REDBOX GIDA",
            font=("Arial", 13)
        ).grid(row=1, column=0, padx=25, pady=(0, 30))

        menu = [
            ("ANA SAYFA", self.ana_sayfa),
            ("DEPO KABUL", self.depo_kabul),
            ("ÜRETİM", self.uretim),
            ("PAKETLEME", self.paketleme),
            ("SEVKİYAT", self.sevkiyat),
            ("İZLENEBİLİRLİK", self.izlenebilirlik),
            ("TEMİZLİK", self.temizlik),
        ]

        for index, (text, command) in enumerate(menu, start=2):
            ctk.CTkButton(
                self.sidebar,
                text=text,
                command=command,
                height=44,
                width=205,
                anchor="w",
                font=("Arial", 14, "bold")
            ).grid(row=index, column=0, padx=20, pady=5)

        ctk.CTkLabel(
            self.sidebar,
            text="REDBOX OS • ÇEKİRDEK v0.2",
            font=("Arial", 11)
        ).grid(row=11, column=0, padx=20, pady=20)

        self.content = ctk.CTkFrame(self, corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")

        self.ana_sayfa()

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def show_page(self, title, subtitle):
        self.clear_content()

        ctk.CTkLabel(
            self.content,
            text=title,
            font=("Arial", 34, "bold")
        ).pack(anchor="w", padx=45, pady=(35, 5))

        ctk.CTkLabel(
            self.content,
            text=subtitle,
            font=("Arial", 16)
        ).pack(anchor="w", padx=45, pady=(0, 20))

    def ana_sayfa(self):
        self.show_page(
            "ANA SAYFA",
            "REDBOX Gıda operasyon kontrol merkezi"
        )

        conn = get_connection()
        kabul_sayisi = conn.execute(
            "SELECT COUNT(*) AS toplam FROM depo_kabul"
        ).fetchone()["toplam"]
        uretim_sayisi = conn.execute(
            "SELECT COUNT(*) AS toplam FROM uretim"
        ).fetchone()["toplam"]
        paket_sayisi = conn.execute(
            "SELECT COUNT(*) AS toplam FROM paketleme"
        ).fetchone()["toplam"]
        sevk_sayisi = conn.execute(
            "SELECT COUNT(*) AS toplam FROM sevkiyat"
        ).fetchone()["toplam"]
        conn.close()

        cards = ctk.CTkFrame(self.content, fg_color="transparent")
        cards.pack(fill="x", padx=40, pady=20)

        card_data = [
            ("DEPO KABUL", str(kabul_sayisi)),
            ("ÜRETİM KAYDI", str(uretim_sayisi)),
            ("PAKETLEME KAYDI", str(paket_sayisi)),
            ("SEVKİYAT KAYDI", str(sevk_sayisi)),
        ]

        for title, value in card_data:
            card = ctk.CTkFrame(cards, width=210, height=130)
            card.pack(side="left", expand=True, fill="both", padx=7)
            card.pack_propagate(False)

            ctk.CTkLabel(
                card,
                text=title,
                font=("Arial", 13, "bold")
            ).pack(pady=(25, 10))

            ctk.CTkLabel(
                card,
                text=value,
                font=("Arial", 28, "bold")
            ).pack()

    def depo_kabul(self):
        self.show_page(
            "DEPO KABUL",
            "Hammadde kabul ve tedarikçi lot kayıtları"
        )

        ana_frame = ctk.CTkFrame(self.content)
        ana_frame.pack(fill="both", expand=True, padx=40, pady=(0, 30))

        form = ctk.CTkFrame(ana_frame, width=410)
        form.pack(side="left", fill="y", padx=(10, 5), pady=10)
        form.pack_propagate(False)

        liste = ctk.CTkFrame(ana_frame)
        liste.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        ctk.CTkLabel(
            form,
            text="YENİ HAMMADDE KABULÜ",
            font=("Arial", 18, "bold")
        ).pack(pady=(20, 15))

        conn = get_connection()
        hammaddeler = conn.execute(
            "SELECT id, ad FROM hammaddeler WHERE aktif = 1 ORDER BY id"
        ).fetchall()
        conn.close()

        self.hammadde_map = {row["ad"]: row["id"] for row in hammaddeler}

        self.kabul_tarihi = self.form_entry(
            form, "Kabul Tarihi", datetime.now().strftime("%d.%m.%Y")
        )

        ctk.CTkLabel(form, text="Hammadde").pack(
            anchor="w", padx=25, pady=(5, 2)
        )
        self.hammadde_secim = ctk.CTkOptionMenu(
            form,
            values=list(self.hammadde_map.keys()),
            width=350
        )
        self.hammadde_secim.pack(padx=25, pady=(0, 8))

        self.tedarikci = self.form_entry(form, "Tedarikçi")
        self.lot_no = self.form_entry(form, "Tedarikçi Lot No")
        self.urt = self.form_entry(form, "Üretim Tarihi")
        self.skt = self.form_entry(form, "SKT / TETT")
        self.miktar = self.form_entry(form, "Miktar (kg)")
        self.aciklama = self.form_entry(form, "Açıklama")

        ctk.CTkButton(
            form,
            text="KABUL KAYDINI KAYDET",
            command=self.depo_kabul_kaydet,
            height=45,
            width=350,
            font=("Arial", 14, "bold")
        ).pack(padx=25, pady=(15, 8))

        ctk.CTkButton(
            form,
            text="FORMU TEMİZLE",
            command=self.depo_form_temizle,
            height=38,
            width=350,
            fg_color="gray35"
        ).pack(padx=25, pady=(0, 15))

        ctk.CTkLabel(
            liste,
            text="SON DEPO KABUL KAYITLARI",
            font=("Arial", 18, "bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        self.kabul_liste_frame = ctk.CTkScrollableFrame(liste)
        self.kabul_liste_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15)
        )

        self.depo_kabul_listele()

    def form_entry(self, parent, label, default=""):
        ctk.CTkLabel(parent, text=label).pack(
            anchor="w", padx=25, pady=(5, 2)
        )

        entry = ctk.CTkEntry(parent, width=350)
        entry.pack(padx=25, pady=(0, 5))

        if default:
            entry.insert(0, default)

        return entry

    def depo_kabul_kaydet(self):
        try:
            tarih = self.kabul_tarihi.get().strip()
            hammadde_adi = self.hammadde_secim.get().strip()
            tedarikci = self.tedarikci.get().strip()
            lot_no = self.lot_no.get().strip()
            urt = self.urt.get().strip()
            skt = self.skt.get().strip()
            miktar_text = self.miktar.get().strip().replace(",", ".")
            aciklama = self.aciklama.get().strip()

            if not tarih:
                raise ValueError("Kabul tarihi boş bırakılamaz.")

            if not hammadde_adi:
                raise ValueError("Hammadde seçilmelidir.")

            if not lot_no:
                raise ValueError("Tedarikçi lot numarası zorunludur.")

            if not miktar_text:
                raise ValueError("Miktar girilmelidir.")

            miktar_kg = float(miktar_text)

            if miktar_kg <= 0:
                raise ValueError("Miktar 0'dan büyük olmalıdır.")

            hammadde_id = self.hammadde_map[hammadde_adi]

            conn = get_connection()
            conn.execute("""
                INSERT INTO depo_kabul (
                    kabul_tarihi,
                    hammadde_id,
                    tedarikci,
                    tedarikci_lot_no,
                    uretim_tarihi,
                    skt_tett,
                    miktar_kg,
                    kabul_durumu,
                    aciklama,
                    kayit_zamani
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'KABUL', ?, ?)
            """, (
                tarih,
                hammadde_id,
                tedarikci,
                lot_no,
                urt,
                skt,
                miktar_kg,
                aciklama,
                datetime.now().isoformat(timespec="seconds")
            ))
            conn.commit()
            conn.close()

            messagebox.showinfo(
                "REDBOX OS",
                "Hammadde kabul kaydı başarıyla kaydedildi."
            )

            self.depo_form_temizle()
            self.depo_kabul_listele()

        except ValueError as hata:
            messagebox.showerror("Kayıt Hatası", str(hata))

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                f"Kayıt yapılamadı:\n{hata}"
            )

    def depo_form_temizle(self):
        alanlar = [
            self.tedarikci,
            self.lot_no,
            self.urt,
            self.skt,
            self.miktar,
            self.aciklama
        ]

        for alan in alanlar:
            alan.delete(0, "end")

    def depo_kabul_listele(self):
        for widget in self.kabul_liste_frame.winfo_children():
            widget.destroy()

        conn = get_connection()
        kayitlar = conn.execute("""
            SELECT
                dk.id,
                dk.kabul_tarihi,
                h.ad AS hammadde,
                dk.tedarikci,
                dk.tedarikci_lot_no,
                dk.miktar_kg
            FROM depo_kabul dk
            JOIN hammaddeler h ON h.id = dk.hammadde_id
            ORDER BY dk.id DESC
            LIMIT 100
        """).fetchall()
        conn.close()

        if not kayitlar:
            ctk.CTkLabel(
                self.kabul_liste_frame,
                text="Henüz depo kabul kaydı bulunmuyor."
            ).pack(pady=30)
            return

        for kayit in kayitlar:
            satir = ctk.CTkFrame(self.kabul_liste_frame)
            satir.pack(fill="x", padx=5, pady=4)

            bilgi = (
                f'{kayit["kabul_tarihi"]}  •  '
                f'{kayit["hammadde"]}\n'
                f'Lot: {kayit["tedarikci_lot_no"]}  •  '
                f'{kayit["miktar_kg"]:.3f} kg'
            )

            if kayit["tedarikci"]:
                bilgi += f'  •  {kayit["tedarikci"]}'

            ctk.CTkLabel(
                satir,
                text=bilgi,
                justify="left",
                anchor="w"
            ).pack(
                side="left",
                fill="x",
                expand=True,
                padx=12,
                pady=10
            )

            ctk.CTkButton(
                satir,
                text="SİL",
                width=65,
                fg_color="gray35",
                command=lambda kayit_id=kayit["id"]:
                    self.depo_kabul_sil(kayit_id)
            ).pack(side="right", padx=10)

    def depo_kabul_sil(self, kayit_id):
        cevap = messagebox.askyesno(
            "Kayıt Silme",
            "Bu depo kabul kaydı silinsin mi?\n\n"
            "Bağlı üretim kaydı varsa sistem silmeye izin vermeyecektir."
        )

        if not cevap:
            return

        try:
            conn = get_connection()
            conn.execute(
                "DELETE FROM depo_kabul WHERE id = ?",
                (kayit_id,)
            )
            conn.commit()
            conn.close()

            self.depo_kabul_listele()

        except Exception as hata:
            messagebox.showerror(
                "Silme Hatası",
                f"Kayıt silinemedi:\n{hata}"
            )

    def uretim(self):
        self.show_page(
            "ÜRETİM",
            "Parti hesabı, üretim firesi ve ürün lot kayıtları"
        )

        ana_frame = ctk.CTkFrame(self.content)
        ana_frame.pack(fill="both", expand=True, padx=40, pady=(0, 30))

        form = ctk.CTkScrollableFrame(
            ana_frame,
            width=410,
            label_text=""
        )
        form.pack(
            side="left",
            fill="y",
            padx=(10, 5),
            pady=10
        )

        liste = ctk.CTkFrame(ana_frame)
        liste.pack(
            side="right",
            fill="both",
            expand=True,
            padx=(5, 10),
            pady=10
        )

        ctk.CTkLabel(
            form,
            text="YENİ ÜRETİM KAYDI",
            font=("Arial", 18, "bold")
        ).pack(pady=(20, 15))

        self.uretim_tarihi = self.form_entry(
            form,
            "Üretim Tarihi",
            datetime.now().strftime("%d.%m.%Y")
        )

        self.urun_lot_no = self.form_entry(
            form,
            "Ürün Lot No"
        )

        self.parti_sayisi = self.form_entry(
            form,
            "Parti Sayısı"
        )

        self.parti_sayisi.bind(
            "<KeyRelease>",
            self.uretim_hesapla
        )

        self.uretim_firesi = self.form_entry(
            form,
            "Üretim Firesi (kg)",
            "0"
        )

        self.uretim_firesi.bind(
            "<KeyRelease>",
            self.uretim_hesapla
        )

        ctk.CTkLabel(
            form,
            text="TEORİK ÜRETİM",
            font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=25, pady=(15, 2))

        self.teorik_label = ctk.CTkLabel(
            form,
            text="0.000 kg",
            font=("Arial", 24, "bold")
        )
        self.teorik_label.pack(
            anchor="w",
            padx=25,
            pady=(0, 10)
        )

        ctk.CTkLabel(
            form,
            text="NET ÜRETİM",
            font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=25, pady=(5, 2))

        self.net_label = ctk.CTkLabel(
            form,
            text="0.000 kg",
            font=("Arial", 24, "bold")
        )
        self.net_label.pack(
            anchor="w",
            padx=25,
            pady=(0, 10)
        )

        self.uretim_aciklama = self.form_entry(
            form,
            "Açıklama"
        )

        ctk.CTkButton(
            form,
            text="ÜRETİM KAYDINI KAYDET",
            command=self.uretim_kaydet,
            height=45,
            width=350,
            font=("Arial", 14, "bold")
        ).pack(padx=25, pady=(15, 15))

        ctk.CTkLabel(
            liste,
            text="SON ÜRETİM KAYITLARI",
            font=("Arial", 18, "bold")
        ).pack(anchor="w", padx=20, pady=(20, 10))

        self.uretim_liste_frame = ctk.CTkScrollableFrame(liste)
        self.uretim_liste_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15)
        )

        self.uretim_listele()

    def uretim_hesapla(self, event=None):
        try:
            parti_text = self.parti_sayisi.get().strip()
            fire_text = self.uretim_firesi.get().strip().replace(",", ".")

            parti = int(parti_text) if parti_text else 0
            fire = float(fire_text) if fire_text else 0.0

            conn_recete = get_connection()

            recete = conn_recete.execute("""
                SELECT parti_teorik_kg
                FROM receteler
                WHERE aktif = 1
                ORDER BY id DESC
                LIMIT 1
            """).fetchone()

            conn_recete.close()

            if recete is None:
                raise ValueError("Aktif üretim reçetesi bulunamadı.")

            parti_teorik_kg = float(recete["parti_teorik_kg"])
            teorik = parti * parti_teorik_kg
            net = teorik - fire

            self.teorik_label.configure(
                text=f"{teorik:.3f} kg"
            )

            self.net_label.configure(
                text=f"{net:.3f} kg"
            )

        except ValueError:
            self.teorik_label.configure(text="HATALI DEĞER")
            self.net_label.configure(text="HATALI DEĞER")

    def uretim_kaydet(self):
        try:
            tarih = self.uretim_tarihi.get().strip()
            lot_no = self.urun_lot_no.get().strip()
            parti_text = self.parti_sayisi.get().strip()
            fire_text = self.uretim_firesi.get().strip().replace(",", ".")
            aciklama = self.uretim_aciklama.get().strip()

            if not tarih:
                raise ValueError("Üretim tarihi boş bırakılamaz.")

            if not lot_no:
                raise ValueError("Ürün lot numarası zorunludur.")

            if not parti_text:
                raise ValueError("Parti sayısı girilmelidir.")

            parti = int(parti_text)
            fire = float(fire_text) if fire_text else 0.0

            if parti <= 0:
                raise ValueError("Parti sayısı 0'dan büyük olmalıdır.")

            if fire < 0:
                raise ValueError("Üretim firesi negatif olamaz.")

            conn_recete = get_connection()

            try:
                recete = conn_recete.execute("""
                    SELECT parti_teorik_kg
                    FROM receteler
                    WHERE aktif = 1
                    ORDER BY id DESC
                    LIMIT 1
                """).fetchone()
            finally:
                conn_recete.close()

            if recete is None:
                raise ValueError("Aktif üretim reçetesi bulunamadı.")

            parti_teorik_kg = float(recete["parti_teorik_kg"])
            teorik = parti * parti_teorik_kg
            net = teorik - fire

            if net < 0:
                raise ValueError(
                    "Üretim firesi teorik üretimden büyük olamaz."
                )

            conn = get_connection()

            try:
                conn.execute("BEGIN")

                cursor = conn.execute("""
                    INSERT INTO uretim (
                        uretim_tarihi,
                        urun_lot_no,
                        parti_sayisi,
                        teorik_uretim_kg,
                        uretim_firesi_kg,
                        net_uretim_kg,
                        personel_1,
                        personel_2,
                        aciklama,
                        kayit_zamani
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tarih,
                    lot_no,
                    parti,
                    teorik,
                    fire,
                    net,
                    "Fatih Ayaz",
                    "Eda Ayaz",
                    aciklama,
                    datetime.now().isoformat(timespec="seconds")
                ))

                uretim_id = cursor.lastrowid

                uretim_stok_isle(
                    conn,
                    uretim_id,
                    parti
                )

                conn.commit()

            except Exception:
                conn.rollback()
                raise

            finally:
                conn.close()

            messagebox.showinfo(
                "REDBOX OS",
                "Üretim kaydı, reçete ve hammadde lot tüketimleri başarıyla kaydedildi."
            )

            self.uretim()

        except ValueError as hata:
            messagebox.showerror(
                "Kayıt Hatası",
                str(hata)
            )

        except Exception as hata:
            messagebox.showerror(
                "Sistem Hatası",
                f"Üretim kaydı yapılamadı:\n{hata}"
            )

    def uretim_listele(self):
        for widget in self.uretim_liste_frame.winfo_children():
            widget.destroy()

        conn = get_connection()

        kayitlar = conn.execute("""
            SELECT
                id,
                uretim_tarihi,
                urun_lot_no,
                parti_sayisi,
                teorik_uretim_kg,
                uretim_firesi_kg,
                net_uretim_kg
            FROM uretim
            ORDER BY id DESC
            LIMIT 100
        """).fetchall()

        conn.close()

        if not kayitlar:
            ctk.CTkLabel(
                self.uretim_liste_frame,
                text="Henüz üretim kaydı bulunmuyor."
            ).pack(pady=30)
            return

        for kayit in kayitlar:
            satir = ctk.CTkFrame(
                self.uretim_liste_frame
            )
            satir.pack(
                fill="x",
                padx=5,
                pady=4
            )

            bilgi = (
                f'{kayit["uretim_tarihi"]}  •  '
                f'LOT {kayit["urun_lot_no"]}\n'
                f'{kayit["parti_sayisi"]} parti  •  '
                f'Teorik: {kayit["teorik_uretim_kg"]:.3f} kg  •  '
                f'Fire: {kayit["uretim_firesi_kg"]:.3f} kg  •  '
                f'Net: {kayit["net_uretim_kg"]:.3f} kg'
            )

            ctk.CTkLabel(
                satir,
                text=bilgi,
                justify="left",
                anchor="w"
            ).pack(
                side="left",
                fill="x",
                expand=True,
                padx=12,
                pady=10
            )

            ctk.CTkButton(
                satir,
                text="SİL",
                width=65,
                fg_color="gray35",
                command=lambda kayit_id=kayit["id"]:
                    self.uretim_sil(kayit_id)
            ).pack(
                side="right",
                padx=10
            )

    def uretim_sil(self, kayit_id):
        cevap = messagebox.askyesno(
            "Üretim Kaydı Silme",
            "Bu üretim kaydı silinsin mi?\n\n"
            "Bağlı paketleme veya lot kaydı varsa "
            "sistem silmeye izin vermeyebilir."
        )

        if not cevap:
            return

        try:
            conn = get_connection()

            conn.execute(
                "DELETE FROM uretim WHERE id = ?",
                (kayit_id,)
            )

            conn.commit()
            conn.close()

            self.uretim_listele()

        except Exception as hata:
            messagebox.showerror(
                "Silme Hatası",
                f"Üretim kaydı silinemedi:\n{hata}"
            )

    def paketleme(self):
        self.show_page(
            "PAKETLEME",
            "500 g ve 2.5 kg paketleme kayıtları"
        )

    def sevkiyat(self):
        self.show_page(
            "SEVKİYAT",
            "Müşteri, soğuk zincir ve sevkiyat kayıtları"
        )

    def izlenebilirlik(self):
        self.show_page(
            "İZLENEBİLİRLİK",
            "Ürün lotundan hammaddeye ve müşteriye tam lot zinciri"
        )

    def temizlik(self):
        self.show_page(
            "TEMİZLİK",
            "Alan ve ekipman temizlik kayıtları"
        )


if __name__ == "__main__":
    app = RedboxOS()
    app.mainloop()
