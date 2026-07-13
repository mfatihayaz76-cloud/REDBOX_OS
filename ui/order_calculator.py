import subprocess
import customtkinter as ctk
from tkinter import messagebox, ttk

from ui.services.order_calculator_service import OrderCalculatorService
from database.report_engine import siparis_hesaplama_pdf_olustur


class OrderCalculatorWindow(ctk.CTkToplevel):

    def __init__(self, master):
        super().__init__(master)

        self.title("Sipariş Hesaplama")
        self.geometry("980x820")
        self.minsize(900, 700)
        self.transient(master)
        self.grab_set()

        self.service = OrderCalculatorService()
        self.plan = None
        self.entries = {}

        self.body = ctk.CTkScrollableFrame(
            self,
            corner_radius=12,
        )
        self.body.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=20,
        )

        ctk.CTkLabel(
            self.body,
            text="SİPARİŞ ÜRETİM PLANLAMA",
            font=("Arial", 24, "bold"),
        ).pack(
            anchor="w",
            padx=15,
            pady=(15, 4),
        )

        ctk.CTkLabel(
            self.body,
            text=(
                "Bu ekran yalnızca hesaplama yapar; "
                "üretim veya sevkiyat kaydı oluşturmaz."
            ),
            font=("Arial", 13),
            text_color="#a9b4c2",
        ).pack(
            anchor="w",
            padx=15,
            pady=(0, 15),
        )

        form = ctk.CTkFrame(self.body)
        form.pack(
            fill="x",
            padx=15,
            pady=(0, 12),
        )

        fields = (
            ("500 g Paket Adedi", "packages_500"),
            ("2.5 kg Paket Adedi", "packages_2500"),
        )

        for column, (label, key) in enumerate(fields):
            form.grid_columnconfigure(column, weight=1)

            ctk.CTkLabel(
                form,
                text=label,
                font=("Arial", 12, "bold"),
            ).grid(
                row=0,
                column=column,
                sticky="w",
                padx=10,
                pady=(12, 4),
            )

            entry = ctk.CTkEntry(
                form,
                height=38,
                placeholder_text="0",
            )
            entry.grid(
                row=1,
                column=column,
                sticky="ew",
                padx=10,
                pady=(0, 12),
            )
            self.entries[key] = entry

        buttons = ctk.CTkFrame(
            self.body,
            fg_color="transparent",
        )
        buttons.pack(
            fill="x",
            padx=15,
            pady=(0, 12),
        )

        ctk.CTkButton(
            buttons,
            text="HESAPLA",
            command=self.calculate,
            height=42,
            font=("Arial", 13, "bold"),
        ).pack(side="left")

        self.pdf_button = ctk.CTkButton(
            buttons,
            text="SİPARİŞ HESAPLAMA PDF",
            command=self.create_pdf,
            height=42,
            state="disabled",
            font=("Arial", 13, "bold"),
        )
        self.pdf_button.pack(
            side="left",
            padx=10,
        )

        self.result = ctk.CTkFrame(self.body)
        self.result.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15),
        )

        ctk.CTkLabel(
            self.result,
            text="Sipariş miktarlarını girip HESAPLA düğmesine basın.",
            font=("Arial", 14),
        ).pack(padx=20, pady=30)

    def calculate(self):
        try:
            self.plan = self.service.calculate(
                packages_500=self.entries["packages_500"].get(),
                packages_2500=self.entries["packages_2500"].get(),
            )
        except Exception as error:
            self.plan = None
            self.pdf_button.configure(state="disabled")
            messagebox.showerror(
                "Sipariş Hesaplama Hatası",
                str(error),
                parent=self,
            )
            return

        self.render_result()
        self.pdf_button.configure(state="normal")

    def render_result(self):
        for widget in self.result.winfo_children():
            widget.destroy()

        status_color = (
            "#2fa572"
            if self.plan["status"] != "HAMMADDE EKSİK"
            else "#d9534f"
        )

        ctk.CTkLabel(
            self.result,
            text=self.plan["status"],
            font=("Arial", 22, "bold"),
            text_color=status_color,
        ).pack(
            anchor="w",
            padx=15,
            pady=(15, 10),
        )

        summary = ctk.CTkFrame(self.result)
        summary.pack(
            fill="x",
            padx=15,
            pady=(0, 12),
        )

        values = (
            ("Sipariş Toplamı", self.plan["total_order_kg"], "kg"),
            ("Mamul Stoktan", self.plan["total_allocated_kg"], "kg"),
            ("Üretilecek", self.plan["production_required_kg"], "kg"),
            ("Gerekli Parti", self.plan["batch_count"], ""),
            ("Teorik Üretim", self.plan["theoretical_production_kg"], "kg"),
            ("Tahmini Fazla", self.plan["estimated_surplus_kg"], "kg"),
            ("Proses Suyu", self.plan["process_water_required_kg"], "kg"),
        )

        for index, (label, value, unit) in enumerate(values):
            row = index // 4
            column = index % 4
            summary.grid_columnconfigure(column, weight=1)

            card = ctk.CTkFrame(summary)
            card.grid(
                row=row,
                column=column,
                sticky="nsew",
                padx=5,
                pady=5,
            )

            ctk.CTkLabel(
                card,
                text=label,
                font=("Arial", 11, "bold"),
            ).pack(pady=(10, 2))

            display = (
                str(value)
                if label == "Gerekli Parti"
                else f"{float(value):.3f} {unit}"
            )

            ctk.CTkLabel(
                card,
                text=display,
                font=("Arial", 16, "bold"),
            ).pack(pady=(0, 10))

        ctk.CTkLabel(
            self.result,
            text="HAMMADDE GEREKSİNİMİ",
            font=("Arial", 16, "bold"),
        ).pack(
            anchor="w",
            padx=15,
            pady=(6, 6),
        )

        table_frame = ctk.CTkFrame(self.result)
        table_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15),
        )

        tree = ttk.Treeview(
            table_frame,
            columns=("name", "required", "stock", "shortage"),
            show="headings",
            height=8,
        )
        tree.heading("name", text="Hammadde")
        tree.heading("required", text="Gereken kg")
        tree.heading("stock", text="Mevcut kg")
        tree.heading("shortage", text="Eksik kg")

        tree.column("name", width=330, anchor="w")
        tree.column("required", width=130, anchor="e")
        tree.column("stock", width=130, anchor="e")
        tree.column("shortage", width=130, anchor="e")

        for row in self.plan["raw_materials"]:
            tree.insert(
                "",
                "end",
                values=(
                    row["name"],
                    f'{row["required_kg"]:.3f}',
                    f'{row["available_kg"]:.3f}',
                    f'{row["shortage_kg"]:.3f}',
                ),
            )

        tree.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=8,
        )

    def create_pdf(self):
        if self.plan is None:
            return

        try:
            pdf = siparis_hesaplama_pdf_olustur(self.plan)

            subprocess.run(
                ["open", "-R", str(pdf.resolve())],
                check=False,
            )

            messagebox.showinfo(
                "REDBOX OS",
                (
                    "Sipariş hesaplama PDF raporu oluşturuldu.\n\n"
                    f"Dosya:\n{pdf}"
                ),
                parent=self,
            )
        except Exception as error:
            messagebox.showerror(
                "Sipariş Hesaplama PDF Hatası",
                str(error),
                parent=self,
            )
