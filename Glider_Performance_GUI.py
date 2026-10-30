"""
DAEDALUS · DAE28 Glider Performance Studio - Project 1.1 (ASW 28-based design)
=============================================================
GUI version of Glider_Performance_Calc.py

Run:
    pip install customtkinter matplotlib numpy
    python Glider_Performance_GUI.py

What's inside
  * Your original functions (lift, stall speed, drag polar, glide ratio/angle/range, Reynolds)
  * NEW: ISA atmosphere (density + viscosity change with altitude)
  * NEW: Analytical best-glide / min-sink points (no scanning needed)
  * NEW: Speed polar (sink rate vs airspeed), drag breakdown, glide range with wind
  * NEW: MacCready speed-to-fly + cross-country average speed
  * NEW: Presets (ASW 28 15 m / 18 m), water-ballast via mass slider, CSV export
"""

import csv
import math
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
import matplotlib
import numpy as np

matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# =====================================================================
# 1. CALCULATION CORE  (your original functions + a few new ones)
# =====================================================================
RHO_SL = 1.2250        # air density [kg/m^3]
G = 9.80665            # gravitational acceleration [m/s^2]
VNE = 280 / 3.6        # never-exceed speed used for the plots [m/s]
MU_SL = 1.7894e-5      # dynamic viscosity [kg/(m*s)]


def lift(rho, V, S, CL):
    return 0.5 * rho * V**2 * S * CL


def required_wing_area(L, rho, V, CL):
    return 2 * L / (CL * rho * V**2)


def stall_speed(W, rho, S, CL_max):
    return math.sqrt(2 * W / (rho * S * CL_max))


def horizontal_flight_speed(W, rho, S, CL):
    return math.sqrt(2 * W / (rho * S * CL))


def drag_coefficient(CL, CD0, AR, e):
    return CD0 + (CL**2) / (math.pi * AR * e)


def drag(rho, V, S, CD):
    return 0.5 * rho * V**2 * S * CD


def glide_ratio(CL, CD):
    return CL / CD


def glide_angle_deg(CL, CD):
    return math.degrees(math.atan(CD / CL))


def glide_range(h, CL, CD):
    return h * glide_ratio(CL, CD)


def reynolds_number(rho, V, c, mu):
    return rho * V * c / mu


# ---- NEW: International Standard Atmosphere (0 - 20 km) -------------
def isa(h):
    """Return (rho [kg/m^3], mu [kg/(m s)], T [K], p [Pa]) at altitude h [m]."""
    R, g0 = 287.058, 9.80665
    if h <= 11000:
        T = 288.15 - 0.0065 * h
        p = 101325.0 * (T / 288.15) ** 5.25588
    else:
        T = 216.65
        p = 22632.1 * math.exp(-g0 * (h - 11000) / (R * T))
    rho = p / (R * T)
    mu = 1.458e-6 * T**1.5 / (T + 110.4)  # Sutherland's law
    return rho, mu, T, p


# ---- NEW: full performance analysis for one set of parameters -------
def analyse(P):
    rho, mu, T, _ = isa(P["alt"])
    W = P["mass"] * G
    b = math.sqrt(P["S"] * P["AR"])
    c = P["S"] / b
    k = 1.0 / (math.pi * P["AR"] * P["e"])

    def point(CL):
        CD = drag_coefficient(CL, P["CD0"], P["AR"], P["e"])
        V = horizontal_flight_speed(W, rho, P["S"], CL)
        return dict(CL=CL, CD=CD, V=V, LD=glide_ratio(CL, CD),
                    sink=V * CD / CL, gamma=glide_angle_deg(CL, CD),
                    Re=reynolds_number(rho, V, c, mu))

    CL_bg = min(math.sqrt(P["CD0"] / k), P["CLmax"])          # best L/D
    CL_ms = min(math.sqrt(3 * P["CD0"] / k), P["CLmax"])      # min sink

    V = np.linspace(stall_speed(W, rho, P["S"], P["CLmax"]), VNE, 500)
    CL = 2 * W / (rho * P["S"] * V**2)
    CD = P["CD0"] + k * CL**2
    q = 0.5 * rho * V**2
    arr = dict(CL=CL, CD=CD, V=V, LD=CL / CD, sink=V * CD / CL,
               D=q * P["S"] * CD, D_par=q * P["S"] * P["CD0"],
               D_ind=q * P["S"] * k * CL**2)

    # ground-speed range with wind (headwind positive)
    w = P["wind"]
    Vg = arr["V"] - w
    ratio = np.where(Vg > 0, Vg / arr["sink"], 0.0)
    i_w = int(np.argmax(ratio))
    best_wind = dict(V=arr["V"][i_w], range=P["h"] * ratio[i_w])

    # MacCready: average cross-country speed for climb rate Mc
    def mc_opt(Mc):
        if Mc <= 0:
            return arr["V"][i_w], 0.0
        avg = np.where(Vg > 0, Vg * Mc / (Mc + arr["sink"]), 0.0)
        j = int(np.argmax(avg))
        return arr["V"][j], avg[j]

    Mcs = np.linspace(0, 5, 51)
    mc_curve = [mc_opt(m) for m in Mcs]
    mc = dict(Mc=Mcs, Vopt=np.array([a for a, _ in mc_curve]),
              Vavg=np.array([b_ for _, b_ in mc_curve]))
    v_stf, v_avg = mc_opt(P["Mc"])

    return dict(
        rho=rho, mu=mu, T=T, W=W, b=b, c=c, k=k,
        wing_loading=W / P["S"] / G,
        stall=dict(V=stall_speed(W, rho, P["S"], P["CLmax"])),
        best=point(CL_bg), minsink=point(CL_ms), cruise=point(P["CLc"]),
        arr=arr, wind=best_wind, mc=mc, stf=v_stf, xc_avg=v_avg,
        range_best=glide_range(P["h"], CL_bg, point(CL_bg)["CD"]),
        range_cruise=glide_range(P["h"], P["CLc"], point(P["CLc"])["CD"]),
    )


# =====================================================================
# 2. GUI
# =====================================================================
BG, PANEL, CARD = "#0d1117", "#151b26", "#1c2433"
TXT, MUTED = "#e6edf3", "#8b98a9"
C_BLUE, C_PINK, C_LIME, C_AMBER, C_VIOLET = "#4cc9f0", "#f72585", "#b8f35c", "#ffb703", "#9d4edd"

PRESETS = {
    "DAE28 (15 m)": dict(S=10.5, AR=21.43, mass=525, CLmax=1.4, CD0=0.012, e=0.90),
    "DAE28 (18 m)": dict(S=10.5, AR=30.86, mass=600, CLmax=1.4, CD0=0.011, e=0.92),
    "DAE28 empty (15 m)": dict(S=10.5, AR=21.43, mass=240, CLmax=1.4, CD0=0.012, e=0.90),
}

# key, label, min, max, default, step, number format, unit
SLIDERS = [
    ("S",     "Wing area",          6,      20,    10.5,   0.1,    "{:.1f}",  "m²"),
    ("AR",    "Aspect ratio",       10,     40,    21.43,  0.01,   "{:.2f}",  ""),
    ("mass",  "Mass (ballast)",     200,    700,   525,    1,      "{:.0f}",  "kg"),
    ("CLmax", "CL max",             1.0,    2.0,   1.4,    0.01,   "{:.2f}",  ""),
    ("CD0",   "CD0 (parasite)",     0.006,  0.030, 0.012,  0.0005, "{:.4f}",  ""),
    ("e",     "Oswald e",           0.60,   1.00,  0.90,   0.01,   "{:.2f}",  ""),
    ("CLc",   "Cruise CL",          0.10,   1.40,  0.60,   0.01,   "{:.2f}",  ""),
    ("alt",   "Altitude",           0,      6000,  0,      50,     "{:.0f}",  "m"),
    ("h",     "Release height",     100,    5000,  1000,   50,     "{:.0f}",  "m"),
    ("wind",  "Headwind (+) / tail (−)", -20, 20,  0,      0.5,    "{:+.1f}", "m/s"),
    ("Mc",    "MacCready setting",  0,      5,     1.5,    0.1,    "{:.1f}",  "m/s"),
]


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("DAEDALUS · DAE28 Glider Performance Studio")
        self.geometry("1500x900")
        self.minsize(1250, 760)
        self.configure(fg_color=BG)

        self.vars, self.labels, self.sliders = {}, {}, {}
        self._job = None
        self.result = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()
        self.apply_preset("DAE28 (15 m)")

    # ------------------------------------------------------------ sidebar
    def _build_sidebar(self):
        side = ctk.CTkScrollableFrame(self, width=300, fg_color=PANEL, corner_radius=0)
        side.grid(row=0, column=0, sticky="nsw")

        ctk.CTkLabel(side, text="✈  DAE28 STUDIO", font=("Segoe UI", 22, "bold"),
                     text_color=C_BLUE).pack(anchor="w", padx=14, pady=(14, 0))
        ctk.CTkLabel(side, text="Team DAEDALUS · Project 1.1",
                     font=("Segoe UI", 12), text_color=MUTED).pack(anchor="w", padx=14, pady=(0, 12))

        self.preset_menu = ctk.CTkOptionMenu(
            side, values=list(PRESETS), command=self.apply_preset,
            fg_color=CARD, button_color=C_BLUE, button_hover_color="#38a8cc",
            text_color=TXT, dropdown_fg_color=CARD)
        self.preset_menu.pack(fill="x", padx=14, pady=(0, 10))

        for key, label, lo, hi, default, step, fmt, unit in SLIDERS:
            row = ctk.CTkFrame(side, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=(4, 0))
            ctk.CTkLabel(row, text=label, font=("Segoe UI", 12), text_color=MUTED).pack(side="left")
            lab = ctk.CTkLabel(row, text="", font=("Consolas", 13, "bold"), text_color=TXT)
            lab.pack(side="right")
            var = tk.DoubleVar(value=default)
            sl = ctk.CTkSlider(
                side, from_=lo, to=hi, variable=var,
                number_of_steps=int(round((hi - lo) / step)),
                progress_color=C_BLUE, button_color=C_BLUE, button_hover_color=C_LIME,
                command=lambda _v, k=key: self._on_change(k))
            sl.pack(fill="x", padx=14, pady=(0, 2))
            self.vars[key], self.labels[key], self.sliders[key] = var, (lab, fmt, unit), sl

        btns = ctk.CTkFrame(side, fg_color="transparent")
        btns.pack(fill="x", padx=14, pady=16)
        ctk.CTkButton(btns, text="Export CSV", fg_color=C_BLUE, text_color="#04141a",
                      hover_color="#38a8cc", command=self.export_csv).pack(fill="x", pady=3)
        ctk.CTkButton(btns, text="Save plots (PNG)", fg_color=CARD, hover_color="#26324a",
                      command=self.save_png).pack(fill="x", pady=3)
        ctk.CTkButton(btns, text="Reset to DAE28 (15 m)", fg_color=CARD, hover_color="#26324a",
                      command=lambda: self.apply_preset("DAE28 (15 m)", reset_all=True)).pack(fill="x", pady=3)

    # --------------------------------------------------------------- main
    def _build_main(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=14, pady=14)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        # KPI cards
        cards = ctk.CTkFrame(main, fg_color="transparent")
        cards.grid(row=0, column=0, sticky="ew")
        self.cards = {}
        spec = [
            ("stall",  "STALL SPEED",       C_PINK),
            ("bestv",  "BEST-GLIDE SPEED",  C_BLUE),
            ("bestld", "BEST L/D",          C_LIME),
            ("minsink", "MIN SINK",         C_VIOLET),
            ("cruise", "CRUISE SPEED",      C_AMBER),
            ("cld",    "CRUISE L/D",        C_AMBER),
            ("angle",  "GLIDE ANGLE (cruise)", C_BLUE),
            ("range",  "RANGE (best, no wind)", C_LIME),
            ("rangew", "RANGE (best, with wind)", C_LIME),
            ("stf",    "SPEED-TO-FLY (MC)", C_VIOLET),
            ("xc",     "XC AVERAGE SPEED",  C_VIOLET),
            ("re",     "REYNOLDS @ CRUISE", C_PINK),
        ]
        for i, (k, title, col) in enumerate(spec):
            card = ctk.CTkFrame(cards, fg_color=CARD, corner_radius=12)
            card.grid(row=i // 6, column=i % 6, sticky="nsew", padx=4, pady=4)
            cards.grid_columnconfigure(i % 6, weight=1, uniform="c")
            ctk.CTkLabel(card, text=title, font=("Segoe UI", 9, "bold"),
                         text_color=MUTED).pack(anchor="w", padx=10, pady=(8, 0))
            v = ctk.CTkLabel(card, text="–", font=("Segoe UI", 19, "bold"), text_color=col)
            v.pack(anchor="w", padx=10)
            s = ctk.CTkLabel(card, text="", font=("Segoe UI", 10), text_color=MUTED)
            s.pack(anchor="w", padx=10, pady=(0, 8))
            self.cards[k] = (v, s)

        # Plot tabs
        self.tabs = ctk.CTkTabview(main, fg_color=PANEL, segmented_button_selected_color=C_BLUE,
                                   segmented_button_selected_hover_color="#38a8cc",
                                   segmented_button_unselected_color=CARD,
                                   text_color="#e6edf3")
        self.tabs.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        self.figs = {}
        for name in ["Speed Polar", "Drag Polar", "L/D & Drag", "Glide Range", "Cross-Country", "Summary"]:
            tab = self.tabs.add(name)
            if name == "Summary":
                self.summary = ctk.CTkTextbox(tab, fg_color=BG, text_color=TXT,
                                              font=("Consolas", 13), corner_radius=10)
                self.summary.pack(fill="both", expand=True, padx=6, pady=6)
                continue
            fig = Figure(facecolor=PANEL)
            canvas = FigureCanvasTkAgg(fig, master=tab)
            canvas.get_tk_widget().configure(bg=PANEL, highlightthickness=0)
            canvas.get_tk_widget().pack(fill="both", expand=True)
            self.figs[name] = (fig, canvas)

    # ------------------------------------------------------------ events
    def apply_preset(self, name, reset_all=False):
        if reset_all:
            for key, _l, _lo, _hi, default, *_ in SLIDERS:
                self.vars[key].set(default)
            self.preset_menu.set(name)
        for k, v in PRESETS[name].items():
            self.vars[k].set(v)
        for k in self.vars:
            self._update_label(k)
        self.refresh()

    def _update_label(self, key):
        lab, fmt, unit = self.labels[key]
        lab.configure(text=f"{fmt.format(self.vars[key].get())} {unit}".strip())

    def _on_change(self, key):
        self._update_label(key)
        if key in PRESETS["DAE28 (15 m)"]:
            self.preset_menu.set("Custom")
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(40, self.refresh)  # debounce while dragging

    def params(self):
        return {k: float(v.get()) for k, v in self.vars.items()}

    # ----------------------------------------------------------- refresh
    def refresh(self):
        self._job = None
        P = self.params()
        r = self.result = analyse(P)
        kmh = lambda v: v * 3.6

        def card(k, val, sub=""):
            self.cards[k][0].configure(text=val)
            self.cards[k][1].configure(text=sub)

        b, ms, cr = r["best"], r["minsink"], r["cruise"]
        card("stall", f"{kmh(r['stall']['V']):.0f} km/h", f"{r['stall']['V']:.1f} m/s  ·  CLmax {P['CLmax']:.2f}")
        card("bestv", f"{kmh(b['V']):.0f} km/h", f"{b['V']:.1f} m/s  ·  CL {b['CL']:.2f}")
        card("bestld", f"{b['LD']:.1f} : 1", f"glide angle {b['gamma']:.2f}°")
        card("minsink", f"{ms['sink']:.2f} m/s", f"at {kmh(ms['V']):.0f} km/h")
        card("cruise", f"{kmh(cr['V']):.0f} km/h", f"{cr['V']:.1f} m/s  ·  CL {P['CLc']:.2f}")
        card("cld", f"{cr['LD']:.1f} : 1", f"CD {cr['CD']:.4f}  ·  sink {cr['sink']:.2f} m/s")
        card("angle", f"{cr['gamma']:.2f}°", f"from {P['h']:.0f} m: {r['range_cruise']/1000:.1f} km")
        card("range", f"{r['range_best']/1000:.1f} km", f"from {P['h']:.0f} m")
        card("rangew", f"{r['wind']['range']/1000:.1f} km",
             f"fly {kmh(r['wind']['V']):.0f} km/h · wind {P['wind']:+.1f} m/s")
        card("stf", f"{kmh(r['stf']):.0f} km/h", f"MacCready {P['Mc']:.1f} m/s")
        card("xc", f"{kmh(r['xc_avg']):.0f} km/h", "cross-country average")
        card("re", f"{cr['Re']/1e6:.2f} ×10⁶", f"chord {r['c']:.2f} m · span {r['b']:.1f} m")

        self._plot_speed_polar(P, r)
        self._plot_drag_polar(P, r)
        self._plot_ld_drag(P, r)
        self._plot_range(P, r)
        self._plot_xc(P, r)
        self._fill_summary(P, r)

    # -------------------------------------------------------------- plots
    @staticmethod
    def _style(ax, xlabel, ylabel, title):
        ax.set_facecolor(BG)
        ax.set_title(title, color=TXT, fontsize=12, fontweight="bold", loc="left")
        ax.set_xlabel(xlabel, color=MUTED)
        ax.set_ylabel(ylabel, color=MUTED)
        ax.tick_params(colors=MUTED)
        for s in ax.spines.values():
            s.set_color("#2a3448")
        ax.grid(True, color="#222c3e", lw=0.7)

    @staticmethod
    def _finish(fig, canvas):
        fig.tight_layout(rect=(0, 0.03, 1, 1))
        fig.text(0.995, 0.008, "DAEDALUS · DAE28", color=MUTED, fontsize=8, ha="right", va="bottom")
        canvas.draw_idle()

    @staticmethod
    def _legend(ax, **kw):
        leg = ax.legend(facecolor=CARD, edgecolor="#2a3448", labelcolor=TXT, fontsize=9, **kw)
        return leg

    def _plot_speed_polar(self, P, r):
        fig, canvas = self.figs["Speed Polar"]
        fig.clear()
        ax = fig.add_subplot(111)
        a = r["arr"]
        self._style(ax, "Airspeed [km/h]", "Sink rate [m/s]", "Speed polar")
        ax.plot(a["V"] * 3.6, -a["sink"], color=C_BLUE, lw=2.5, label="Speed polar")
        b, ms, cr = r["best"], r["minsink"], r["cruise"]
        # tangent from (headwind, 0) -> best glide over the ground
        w = P["wind"] * 3.6
        Vw = r["wind"]["V"] * 3.6
        sw = np.interp(Vw, a["V"] * 3.6, a["sink"])
        xs = np.array([w, Vw * 1.6 - w * 0.6])
        slope = -sw / (Vw - w) if Vw != w else 0
        ax.plot(xs, slope * (xs - w), color=C_LIME, lw=1.2, ls="--", label="Best glide over ground")
        ax.scatter([r["stall"]["V"] * 3.6], [-np.interp(r["stall"]["V"], a["V"], a["sink"])],
                   color=C_PINK, s=70, zorder=5, label=f"Stall {r['stall']['V']*3.6:.0f} km/h")
        ax.scatter([ms["V"] * 3.6], [-ms["sink"]], color=C_VIOLET, s=70, zorder=5,
                   label=f"Min sink {ms['sink']:.2f} m/s")
        ax.scatter([b["V"] * 3.6], [-b["sink"]], color=C_LIME, s=70, zorder=5,
                   label=f"Best L/D {b['LD']:.1f}")
        ax.scatter([cr["V"] * 3.6], [-cr["sink"]], color=C_AMBER, s=70, zorder=5, label="Cruise point")
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.axhline(-P["Mc"], color=C_VIOLET, lw=0.8, ls=":", alpha=0.7)
        cap = max(4.0, P["Mc"] + 2.5)
        ax.set_xlim(0, a["V"][a["sink"] <= cap].max() * 3.6)
        ax.set_ylim(-cap, 0.3)
        self._legend(ax, loc="lower left")
        self._finish(fig, canvas)

    def _plot_drag_polar(self, P, r):
        fig, canvas = self.figs["Drag Polar"]
        fig.clear()
        a = r["arr"]
        ax1, ax2 = fig.add_subplot(121), fig.add_subplot(122)
        self._style(ax1, "CD", "CL", "Drag polar  (CL vs CD)")
        ax1.plot(a["CD"], a["CL"], color=C_BLUE, lw=2.5)
        ax1.axvline(P["CD0"], color=MUTED, lw=0.8, ls=":")
        ax1.text(P["CD0"], a["CL"].max() * 0.05, " CD0", color=MUTED)
        b, cr = r["best"], r["cruise"]
        ax1.plot([0, b["CD"] * 1.8], [0, b["CL"] * 1.8], color=C_LIME, ls="--", lw=1.2, label="Tangent: max L/D")
        ax1.scatter([b["CD"]], [b["CL"]], color=C_LIME, s=70, zorder=5, label=f"Best L/D CL={b['CL']:.2f}")
        ax1.scatter([cr["CD"]], [cr["CL"]], color=C_AMBER, s=70, zorder=5, label=f"Cruise CL={cr['CL']:.2f}")
        ax1.set_ylim(0, P["CLmax"] * 1.05)
        self._legend(ax1, loc="lower right")

        self._style(ax2, "CL", "CL / CD", "Lift-to-drag vs CL")
        ax2.plot(a["CL"], a["LD"], color=C_LIME, lw=2.5)
        ax2.scatter([b["CL"]], [b["LD"]], color=C_LIME, s=70, zorder=5)
        ax2.scatter([cr["CL"]], [cr["LD"]], color=C_AMBER, s=70, zorder=5)
        ax2.annotate(f"max {b['LD']:.1f}", (b["CL"], b["LD"]), color=TXT, xytext=(10, -18),
                     textcoords="offset points")
        self._finish(fig, canvas)

    def _plot_ld_drag(self, P, r):
        fig, canvas = self.figs["L/D & Drag"]
        fig.clear()
        a = r["arr"]
        ax1, ax2 = fig.add_subplot(121), fig.add_subplot(122)
        v = a["V"] * 3.6
        self._style(ax1, "Airspeed [km/h]", "L/D", "Glide ratio vs airspeed")
        ax1.plot(v, a["LD"], color=C_LIME, lw=2.5)
        ax1.scatter([r["best"]["V"] * 3.6], [r["best"]["LD"]], color=C_LIME, s=70, zorder=5)
        ax1.scatter([r["cruise"]["V"] * 3.6], [r["cruise"]["LD"]], color=C_AMBER, s=70, zorder=5)

        self._style(ax2, "Airspeed [km/h]", "Drag [N]", "Drag breakdown")
        ax2.plot(v, a["D"], color=TXT, lw=2.5, label="Total")
        ax2.plot(v, a["D_par"], color=C_BLUE, lw=1.8, label="Parasite")
        ax2.plot(v, a["D_ind"], color=C_PINK, lw=1.8, label="Induced")
        ax2.axvline(r["best"]["V"] * 3.6, color=C_LIME, ls="--", lw=1)
        ax2.text(r["best"]["V"] * 3.6, a["D"].max() * 0.9, "  min drag\n  (parasite = induced)",
                 color=C_LIME, fontsize=9)
        self._legend(ax2, loc="upper center")
        self._finish(fig, canvas)

    def _plot_range(self, P, r):
        fig, canvas = self.figs["Glide Range"]
        fig.clear()
        ax = fig.add_subplot(111)
        self._style(ax, "Distance [km]", "Height [m]", f"Glide from {P['h']:.0f} m")
        h = P["h"]
        lines = [
            (r["range_best"], C_LIME, f"Best L/D, no wind: {r['range_best']/1000:.1f} km"),
            (r["range_cruise"], C_AMBER, f"Cruise CL, no wind: {r['range_cruise']/1000:.1f} km"),
            (r["wind"]["range"], C_PINK, f"Best with wind {P['wind']:+.1f} m/s: {r['wind']['range']/1000:.1f} km"),
        ]
        for R, col, lab in lines:
            ax.plot([0, R / 1000], [h, 0], color=col, lw=2.5, label=lab)
            ax.fill_between([0, R / 1000], [h, 0], color=col, alpha=0.06)
            ax.scatter([R / 1000], [0], color=col, s=60, zorder=5)
        ax.set_xlim(0, max(R for R, *_ in lines) / 1000 * 1.1 + 0.1)
        ax.set_ylim(0, h * 1.08)
        self._legend(ax, loc="upper right")
        self._finish(fig, canvas)

    def _plot_xc(self, P, r):
        fig, canvas = self.figs["Cross-Country"]
        fig.clear()
        m = r["mc"]
        ax1, ax2 = fig.add_subplot(121), fig.add_subplot(122)
        self._style(ax1, "MacCready setting [m/s]", "Speed-to-fly [km/h]", "MacCready speed-to-fly")
        ax1.plot(m["Mc"], m["Vopt"] * 3.6, color=C_VIOLET, lw=2.5)
        ax1.scatter([P["Mc"]], [r["stf"] * 3.6], color=C_AMBER, s=80, zorder=5,
                    label=f"{r['stf']*3.6:.0f} km/h @ MC {P['Mc']:.1f}")
        self._legend(ax1, loc="lower right")

        self._style(ax2, "Average climb rate [m/s]", "Cross-country speed [km/h]", "Achievable XC speed")
        ax2.plot(m["Mc"], m["Vavg"] * 3.6, color=C_BLUE, lw=2.5)
        ax2.scatter([P["Mc"]], [r["xc_avg"] * 3.6], color=C_AMBER, s=80, zorder=5,
                    label=f"{r['xc_avg']*3.6:.0f} km/h @ {P['Mc']:.1f} m/s")
        self._legend(ax2, loc="lower right")
        self._finish(fig, canvas)

    # ----------------------------------------------------------- summary
    def _summary_text(self, P, r):
        b, ms, cr = r["best"], r["minsink"], r["cruise"]
        k = lambda v: v * 3.6
        return f"""DAE28 PERFORMANCE SUMMARY  ·  TEAM DAEDALUS
{'=' * 58}
 Geometry
   Wing area S            {P['S']:8.2f} m²
   Aspect ratio           {P['AR']:8.2f}
   Span / mean chord      {r['b']:8.2f} m / {r['c']:.2f} m
   Mass / weight          {P['mass']:8.0f} kg / {r['W']:.0f} N
   Wing loading           {r['wing_loading']:8.1f} kg/m²

 Atmosphere (ISA @ {P['alt']:.0f} m)
   Density                {r['rho']:8.4f} kg/m³   (sea level {RHO_SL})
   Viscosity              {r['mu']:.3e} kg/(m·s)
   Temperature            {r['T']-273.15:8.1f} °C

 Speeds
   Stall                  {r['stall']['V']:8.2f} m/s  {k(r['stall']['V']):7.1f} km/h
   Min sink               {ms['V']:8.2f} m/s  {k(ms['V']):7.1f} km/h   sink {ms['sink']:.2f} m/s
   Best glide             {b['V']:8.2f} m/s  {k(b['V']):7.1f} km/h   L/D {b['LD']:.1f}
   Cruise (CL {P['CLc']:.2f})       {cr['V']:8.2f} m/s  {k(cr['V']):7.1f} km/h   L/D {cr['LD']:.1f}

 Aerodynamics
   CL best-glide          {b['CL']:8.3f}   (= sqrt(CD0·π·AR·e))
   CL min-sink            {ms['CL']:8.3f}   (= sqrt(3·CD0·π·AR·e))
   CD at best glide       {b['CD']:8.4f}   (parasite = induced)
   Glide angle (best)     {b['gamma']:8.2f} °
   Glide angle (cruise)   {cr['gamma']:8.2f} °
   Reynolds @ cruise      {cr['Re']:.3e}

 Range from {P['h']:.0f} m
   Best L/D, no wind      {r['range_best']/1000:8.2f} km
   Cruise CL, no wind     {r['range_cruise']/1000:8.2f} km
   Best, wind {P['wind']:+.1f} m/s     {r['wind']['range']/1000:8.2f} km  (fly {k(r['wind']['V']):.0f} km/h)

 Cross-country (MacCready {P['Mc']:.1f} m/s)
   Speed-to-fly           {k(r['stf']):8.1f} km/h
   Average XC speed       {k(r['xc_avg']):8.1f} km/h
"""

    def _fill_summary(self, P, r):
        self.summary.configure(state="normal")
        self.summary.delete("1.0", "end")
        self.summary.insert("1.0", self._summary_text(P, r))
        self.summary.configure(state="disabled")

    # ------------------------------------------------------------ export
    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="glider_polar.csv",
                                            filetypes=[("CSV", "*.csv")])
        if not path:
            return
        a = self.result["arr"]
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["CL", "CD", "V_m/s", "V_km/h", "L/D", "sink_m/s", "drag_N", "parasite_N", "induced_N"])
            for i in range(len(a["CL"])):
                w.writerow([f"{a['CL'][i]:.4f}", f"{a['CD'][i]:.5f}", f"{a['V'][i]:.3f}",
                            f"{a['V'][i]*3.6:.2f}", f"{a['LD'][i]:.3f}", f"{a['sink'][i]:.4f}",
                            f"{a['D'][i]:.3f}", f"{a['D_par'][i]:.3f}", f"{a['D_ind'][i]:.3f}"])
        messagebox.showinfo("Export", f"Saved {path}")

    def save_png(self):
        folder = filedialog.askdirectory(title="Choose a folder for the plots")
        if not folder:
            return
        for name, (fig, _c) in self.figs.items():
            fig.savefig(f"{folder}/{name.replace(' ', '_').replace('/', '-')}.png",
                        dpi=160, facecolor=fig.get_facecolor())
        messagebox.showinfo("Export", f"Saved {len(self.figs)} PNGs to {folder}")


if __name__ == "__main__":
    App().mainloop()
