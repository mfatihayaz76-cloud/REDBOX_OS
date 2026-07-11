import customtkinter as ctk

ctk.set_appearance_mode("dark")

app = ctk.CTk()
app.title("REDBOX OS - Sistem Testi")
app.geometry("700x400")

baslik = ctk.CTkLabel(
    app,
    text="REDBOX OS",
    font=("Arial", 36, "bold")
)
baslik.pack(pady=(100, 15))

durum = ctk.CTkLabel(
    app,
    text="Sistem başarıyla çalışıyor.",
    font=("Arial", 18)
)
durum.pack(pady=10)

app.mainloop()
