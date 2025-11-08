import tkinter as tk
from tkinter import messagebox, simpledialog
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF
import json, os, datetime

DATA_FILE = "data.json"

# ---------- Data Structure and Persistence ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"spins": [], "balance": 0.0, "custom_buttons": [], "manual_wins": None, "manual_losses": None}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

data = load_data()

# ---------- Main App ----------
class RouletteApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Casino Roulette Tracker")
        self.dark_mode = False

        self.set_theme_colors()

        self.balance = data.get("balance", 0.0)
        self.spins = data.get("spins", [])
        self.custom_buttons = data.get("custom_buttons", [])
        self.manual_wins = data.get("manual_wins")
        self.manual_losses = data.get("manual_losses")

        self.selected_numbers = set()
        self.number_buttons = {}

        self.create_ui()
        self.update_graph()
        self.update_stats()

    # ---------- Theme Handling ----------
    def set_theme_colors(self):
        if self.dark_mode:
            self.bg_color = "#111111"
            self.text_color = "#FFFFFF"
            self.button_color = "#333333"
            self.highlight_color = "#777777"
        else:
            self.bg_color = "#014421"  # Casino green
            self.text_color = "white"
            self.button_color = "#228B22"
            self.highlight_color = "#DAA520"

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.set_theme_colors()
        self.root.configure(bg=self.bg_color)
        for widget in self.root.winfo_children():
            widget.destroy()
        self.create_ui()
        self.update_graph()
        self.update_stats()

    # ---------- UI Layout ----------
    def create_ui(self):
        self.root.configure(bg=self.bg_color)
        self.root.geometry("900x600")

        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill="both", expand=True)

        left_frame = tk.Frame(main_frame, bg=self.bg_color)
        left_frame.pack(side="left", fill="y", padx=10, pady=10)

        right_frame = tk.Frame(main_frame, bg=self.bg_color)
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Number Buttons (3 per row)
        number_frame = tk.Frame(left_frame, bg=self.bg_color)
        number_frame.pack(pady=(0, 10))
        for n in range(37):
            color = "#D40000" if n in self.red_numbers() else "#000000"
            btn = tk.Button(
                number_frame, text=str(n), width=6,
                bg=color, fg="white"
            )
            btn.grid(row=n // 3, column=n % 3, padx=2, pady=2)
            btn.bind("<Button-1>", lambda e, x=n: self.number_click(e, x))
            self.number_buttons[n] = btn

        # --- Custom Bets Section ---
        tk.Label(left_frame, text="Custom Bets", bg=self.bg_color, fg=self.text_color).pack(pady=(10, 0))
        self.bet_frame = tk.Frame(left_frame, bg=self.bg_color)
        self.bet_frame.pack(pady=(0, 5))
        self.refresh_custom_buttons()

        add_button = tk.Button(left_frame, text="Add Custom", bg=self.button_color, fg="white",
                               command=self.add_custom_button)
        add_button.pack(pady=3, fill="x")

        reset_button = tk.Button(left_frame, text="Reset Session", bg=self.highlight_color, fg="white",
                                 command=self.reset_session)
        reset_button.pack(pady=3, fill="x")

        # --- Edit Wins/Losses Button ---
        edit_button = tk.Button(left_frame, text="Edit Wins/Losses", bg=self.highlight_color, fg="white",
                                command=self.edit_wins_losses)
        edit_button.pack(pady=3, fill="x")

        # --- PDF and Dark Mode Buttons ---
        pdf_button = tk.Button(left_frame, text="Export PDF", bg=self.highlight_color, fg="white",
                               command=self.generate_pdf)
        pdf_button.pack(pady=3, fill="x")

        dark_button = tk.Button(left_frame, text="Toggle Dark Mode", bg="#555555", fg="white",
                                command=self.toggle_dark_mode)
        dark_button.pack(pady=(8, 3), fill="x")

        # --- Stats Display ---
        self.stats_label = tk.Label(right_frame, text="", bg=self.bg_color, fg=self.text_color, justify="left",
                                    font=("Helvetica", 12))
        self.stats_label.pack(anchor="w", pady=(5, 10))

        # --- Graph Canvas ---
        self.graph_canvas = tk.Canvas(right_frame, bg="#013220" if not self.dark_mode else "#222222", height=300)
        self.graph_canvas.pack(fill="both", expand=True, pady=10)

    # ---------- Logic ----------
    def number_click(self, event, n):
        if (event.state & 0x0001):  # Shift key held
            self.selected_numbers.add(n)
            self.number_buttons[n].config(relief="sunken")
        else:
            if self.selected_numbers:
                self.selected_numbers.add(n)
                self.record_spin(list(self.selected_numbers))
                for idx in self.selected_numbers:
                    self.number_buttons[idx].config(relief="raised")
                self.selected_numbers.clear()
            else:
                self.record_spin([n])
        self.update_graph()
        self.update_stats()

    def record_spin(self, nums):
        self.spins.append(nums)
        save_data({
            "spins": self.spins,
            "balance": self.balance,
            "custom_buttons": self.custom_buttons,
            "manual_wins": self.manual_wins,
            "manual_losses": self.manual_losses
        })

    def add_custom_button(self):
        value = simpledialog.askstring("New Bet Button", "Enter amount (e.g. +10 or -20):")
        if value:
            self.custom_buttons.append(value)
            save_data({
                "spins": self.spins,
                "balance": self.balance,
                "custom_buttons": self.custom_buttons,
                "manual_wins": self.manual_wins,
                "manual_losses": self.manual_losses
            })
            self.refresh_custom_buttons()

    def refresh_custom_buttons(self):
        for widget in self.bet_frame.winfo_children():
            widget.destroy()

        for label in self.custom_buttons:
            btn = tk.Button(self.bet_frame, text=label, bg=self.button_color, fg="white",
                            command=lambda val=label: self.apply_bet(val))
            btn.pack(pady=1, fill="x")

        if self.custom_buttons:
            del_btn = tk.Button(self.bet_frame, text="Remove Custom", bg="#8B0000", fg="white",
                                command=self.remove_custom_button)
            del_btn.pack(pady=4, fill="x")

    def remove_custom_button(self):
        if not self.custom_buttons:
            return
        to_remove = simpledialog.askstring("Delete Custom", "Enter exact label to remove:")
        if to_remove in self.custom_buttons:
            self.custom_buttons.remove(to_remove)
            save_data({
                "spins": self.spins,
                "balance": self.balance,
                "custom_buttons": self.custom_buttons,
                "manual_wins": self.manual_wins,
                "manual_losses": self.manual_losses
            })
            self.refresh_custom_buttons()

    def apply_bet(self, val):
        try:
            self.balance += float(val)
        except ValueError:
            messagebox.showerror("Error", "Invalid bet value.")
            return
        save_data({
            "spins": self.spins,
            "balance": self.balance,
            "custom_buttons": self.custom_buttons,
            "manual_wins": self.manual_wins,
            "manual_losses": self.manual_losses
        })
        self.update_stats()

    # ---------- Win/Loss Tracking ----------
    def get_wins(self):
        if self.manual_wins is not None:
            return self.manual_wins
        return len([s for s in self.spins if 0 in s])

    def get_losses(self):
        if self.manual_losses is not None:
            return self.manual_losses
        total_spins = len(self.spins)
        return total_spins - len([s for s in self.spins if 0 in s])

    def edit_wins_losses(self):
        current_wins = self.get_wins()
        current_losses = self.get_losses()

        new_wins = simpledialog.askinteger("Edit Wins", f"Current Wins: {current_wins}\nEnter new number of wins:")
        if new_wins is None:
            return
        new_losses = simpledialog.askinteger("Edit Losses", f"Current Losses: {current_losses}\nEnter new number of losses:")
        if new_losses is None:
            return

        self.manual_wins = new_wins
        self.manual_losses = new_losses

        save_data({
            "spins": self.spins,
            "balance": self.balance,
            "custom_buttons": self.custom_buttons,
            "manual_wins": self.manual_wins,
            "manual_losses": self.manual_losses
        })

        self.update_stats()

    # ---------- Stats ----------
    def update_stats(self):
        total_spins = len(self.spins)
        win_count = self.get_wins()
        loss_count = self.get_losses()
        text = f"Total Spins: {total_spins}\nWins: {win_count}\nLosses: {loss_count}\nBalance: ${self.balance:.2f}"
        self.stats_label.config(text=text)

    def get_frequencies(self):
        freq = {i: 0 for i in range(37)}
        for s in self.spins:
            for n in s:
                freq[n] += 1
        return freq

    def update_graph(self):
        self.graph_canvas.delete("all")
        freq = self.get_frequencies()
        max_val = max(freq.values()) if any(freq.values()) else 1
        width = 600
        height = 250
        bar_width = width / 37
        for i in range(37):
            bar_height = (freq[i] / max_val) * height
            x0 = i * bar_width + 10
            y0 = height - bar_height
            x1 = x0 + bar_width - 2
            y1 = height
            color = "#D40000" if i in self.red_numbers() else "#000000"
            self.graph_canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="#013220")
            self.graph_canvas.create_text(x0 + bar_width / 2, height + 15, text=str(i), fill="white")

    def red_numbers(self):
        return {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}

    def reset_session(self):
        if messagebox.askyesno("Reset", "Clear all data?"):
            self.spins.clear()
            self.balance = 0
            self.manual_wins = None
            self.manual_losses = None
            save_data({"spins": self.spins, "balance": self.balance, "custom_buttons": self.custom_buttons,
                       "manual_wins": self.manual_wins, "manual_losses": self.manual_losses})
            self.update_graph()
            self.update_stats()

    # ---------- PDF Generation ----------
    def generate_pdf(self):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"roulette_report_{timestamp}.pdf"

        c = canvas.Canvas(filename, pagesize=A4)
        width, height = A4

        # Header
        c.setFillColorRGB(0.0, 0.27, 0.13)
        c.rect(0, height - 100, width, 100, fill=1, stroke=0)
        c.setFillColorRGB(1, 0.84, 0)
        c.setFont("Helvetica-Bold", 26)
        c.drawCentredString(width / 2, height - 60, "🎰 Roulette Session Report")

        # Info box
        now = datetime.datetime.now().strftime("%B %d, %Y — %I:%M %p")
        c.setFont("Helvetica", 12)
        c.setFillColor("white")
        c.drawCentredString(width / 2, height - 85, f"Generated on {now}")

        y = height - 140
        c.setFillColorRGB(0.93, 0.93, 0.93)
        c.rect(40, y - 100, width - 80, 90, fill=1, stroke=0)

        freq = self.get_frequencies()
        total = len(self.spins)
        wins = self.get_wins()
        losses = self.get_losses()

        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y - 30, "Session Summary:")
        c.setFont("Helvetica", 12)
        c.drawString(70, y - 50, f"Total Spins: {total}")
        c.drawString(70, y - 65, f"Wins: {wins}")
        c.drawString(70, y - 80, f"Losses: {losses}")
        c.drawString(70, y - 95, f"Balance: ${self.balance:.2f}")

        # Divider
        c.setStrokeColorRGB(1, 0.84, 0)
        c.setLineWidth(2)
        c.line(40, y - 110, width - 40, y - 110)

        # Graph
        c.setFont("Helvetica-Bold", 16)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(50, y - 140, "Number Frequency Heatmap:")

        drawing = Drawing(480, 200)
        max_val = max(freq.values()) if any(freq.values()) else 1
        bar_w = 480 / 37
        for i in range(37):
            h = (freq[i] / max_val) * 150
            color = "#D40000" if i in self.red_numbers() else "#000000"
            drawing.add(Rect(i * bar_w, 0, bar_w - 1, h, fillColor=color))
            drawing.add(String(i * bar_w + bar_w / 2, -12, str(i), textAnchor="middle", fontSize=7, fillColor="black"))

        renderPDF.draw(drawing, c, 60, y - 370)
        c.setFont("Helvetica-Oblique", 9)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        c.drawCentredString(width / 2, 30, "Roulette Analysis — Generated by GAS")

        c.save()
        messagebox.showinfo("PDF Export", f"Report saved as:\n{filename}")

# ---------- Run ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = RouletteApp(root)
    root.mainloop()
