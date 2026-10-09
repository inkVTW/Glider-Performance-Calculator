"""
Glider Performance GUI - Project 1.1
Needs glider_performance.py in the same folder.
Install once:  pip install matplotlib
Run:           python glider_gui.py
"""

import tkinter as tk
from tkinter import ttk

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import glider_performance as gp

# label, key, default value
INPUTS = [
    ("Wing area S [m²]", "S", 10.5),
    ("Aspect ratio AR", "AR", 21.43),
    ("Mass [kg]", "m", 525),
    ("CL max", "CL_max", 1.4),
    ("CD0", "CD0", 0.012),
    ("Oswald e", "e", 0.9),
    ("Cruise CL", "CL", 0.6),
    ("Start height [m]", "h", 1000),
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DAEDALUS Glider Performance Calculator")
        self.configure(padx=12, pady=12)

        # ---- left: inputs ----
        left = ttk.LabelFrame(self, text="Inputs", padding=10)
        left.grid(row=0, column=0, sticky="n")
        self.vars = {}
        for i, (label, key, default) in enumerate(INPUTS):
            ttk.Label(left, text=label).grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=str(default))
            entry = ttk.Entry(left, textvariable=var, width=10)
            entry.grid(row=i, column=1, padx=6)
            entry.bind("<Return>", lambda _e: self.calculate())
            self.vars[key] = var
        ttk.Button(left, text="Calculate", command=self.calculate).grid(
            row=len(INPUTS), column=0, columnspan=2, pady=10, sticky="ew")

        # ---- left-bottom: results ----
        res = ttk.LabelFrame(self, text="Results", padding=10)
        res.grid(row=1, column=0, sticky="n", pady=8)
        self.out = tk.StringVar()
        ttk.Label(res, textvariable=self.out, font=("Consolas", 11),
                  justify="left").pack()

        # ---- right: plot ----
        self.fig = Figure(figsize=(6, 4.5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().grid(row=0, column=1, rowspan=2, padx=12)

        self.calculate()

    def get(self, key):
        return float(self.vars[key].get())

    def calculate(self):
        try:
            S, AR, m = self.get("S"), self.get("AR"), self.get("m")
            CL_max, CD0, e = self.get("CL_max"), self.get("CD0"), self.get("e")
            CL, h = self.get("CL"), self.get("h")
        except ValueError:
            self.out.set("Please enter numbers only.")
            return

        W = m * gp.G
        CD = gp.drag_coefficient(CL, CD0, AR, e)
        V_stall = gp.stall_speed(W, gp.RHO_SL, S, CL_max)
        V = gp.horizontal_flight_speed(W, gp.RHO_SL, S, CL)

        # best L/D by sweeping CL
        cls = [i / 100 for i in range(10, int(CL_max * 100) + 1)]
        lds = [gp.glide_ratio(c, gp.drag_coefficient(c, CD0, AR, e)) for c in cls]
        best_ld = max(lds)
        best_cl = cls[lds.index(best_ld)]

        self.out.set(
            f"Stall speed : {V_stall*3.6:6.1f} km/h\n"
            f"Speed @ CL  : {V*3.6:6.1f} km/h\n"
            f"CD          : {CD:6.4f}\n"
            f"L/D         : {gp.glide_ratio(CL, CD):6.1f}\n"
            f"Glide angle : {gp.glide_angle_deg(CL, CD):6.2f} °\n"
            f"Range       : {gp.glide_range(h, CL, CD)/1000:6.1f} km\n"
            f"Best L/D    : {best_ld:6.1f} @ CL {best_cl:.2f}"
        )

        self.ax.clear()
        self.ax.plot(cls, lds, label="L/D")
        self.ax.axvline(CL, color="orange", ls="--", label=f"Cruise CL = {CL}")
        self.ax.plot(best_cl, best_ld, "ro", label="Best L/D")
        self.ax.set_xlabel("CL")
        self.ax.set_ylabel("L/D")
        self.ax.set_title("Glide ratio vs lift coefficient")
        self.ax.grid(True)
        self.ax.legend()
        self.canvas.draw()


if __name__ == "__main__":
    App().mainloop()
