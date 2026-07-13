import customtkinter as ctk
from pathlib import Path
from datetime import datetime
import shutil
from tkinter import messagebox


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
