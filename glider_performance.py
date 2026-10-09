"""
DAEDALUS Glider Performance Calculator - Project 1.1 (ASW 28-based design)
====================================================================
Straightforward functions for the performance calculations covered in
weeks 3 & 4 of the Performance lectures:

  - Air properties (standard sea level)
  - Lift equation
  - Stall speed
  - Drag polar (parasite + induced drag)
  - Glide ratio (L/D) and glide angle
  - Glide range
  - Reynolds number
"""

import math

# ---------------------------------------------------------------
# Standard sea level air properties 
# ---------------------------------------------------------------
RHO_SL = 1.2250        # air density [kg/m^3]
G = 9.80665            # gravitational acceleration [m/s^2]
MU_SL = 1.7894e-5      # dynamic viscosity [kg/(m*s)]


# ---------------------------------------------------------------
# 1. Lift
# ---------------------------------------------------------------
def lift(rho, V, S, CL):
    """Lift force [N].  L = 1/2 * rho * V^2 * S * CL"""
    return 0.5 * rho * V**2 * S * CL


def required_wing_area(L, rho, V, CL):
    """Wing area [m^2] needed to produce a given lift at speed V."""
    return 2 * L / (CL * rho * V**2)


# ---------------------------------------------------------------
# 2. Stall speed
# ---------------------------------------------------------------
def stall_speed(W, rho, S, CL_max):
    """Stall speed [m/s].  V_stall = sqrt(2W / (rho * S * CL_max))"""
    return math.sqrt(2 * W / (rho * S * CL_max))


def horizontal_flight_speed(W, rho, S, CL):
    """Speed [m/s] needed to fly level (L = W) at a given CL."""
    return math.sqrt(2 * W / (rho * S * CL))


# ---------------------------------------------------------------
# 3. Drag polar
# ---------------------------------------------------------------
def drag_coefficient(CL, CD0, AR, e):
    """CD = CD0 + CL^2 / (pi * AR * e)"""
    return CD0 + (CL**2) / (math.pi * AR * e)


def drag(rho, V, S, CD):
    """Drag force [N].  D = 1/2 * rho * V^2 * S * CD"""
    return 0.5 * rho * V**2 * S * CD


# ---------------------------------------------------------------
# 4. Gliding flight (steady, unpowered)
# ---------------------------------------------------------------
def glide_ratio(CL, CD):
    """L/D = CL/CD  (higher is better)"""
    return CL / CD


def glide_angle_deg(CL, CD):
    """Glide angle gamma [deg].  tan(gamma) = CD/CL"""
    return math.degrees(math.atan(CD / CL))


def glide_range(h, CL, CD):
    """Horizontal distance [m] covered gliding from height h [m]. R = h * CL/CD"""
    return h * glide_ratio(CL, CD)


# ---------------------------------------------------------------
# 5. Reynolds number
# ---------------------------------------------------------------
def reynolds_number(rho, V, c, mu):
    """Re = rho * V * c / mu   (c = chord length [m])"""
    return rho * V * c / mu


# =================================================================
# DAEDALUS
# =================================================================
if __name__ == "__main__":

    
    S = 10.5          # wing area [m^2]
    AR = 21.43         # aspect ratio
    m_empty = 240      # empty mass [kg]
    m_MTOW = 525       # max take-off mass [kg]
    W = m_MTOW * G     # weight [N]

    # Aerodynamic estimates 
    CL_max = 1.4       # max lift coefficient (typical laminar glider airfoil)
    CD0 = 0.012        # zero-lift (parasite) drag coefficient
    e = 0.9            # Oswald efficiency factor

    # A representative cruise CL 
    CL_cruise = 0.6

    # --- Run the calculations ---
    V_stall = stall_speed(W, RHO_SL, S, CL_max)
    CD_cruise = drag_coefficient(CL_cruise, CD0, AR, e)
    LD = glide_ratio(CL_cruise, CD_cruise)
    gamma = glide_angle_deg(CL_cruise, CD_cruise)
    V_cruise = horizontal_flight_speed(W, RHO_SL, S, CL_cruise)
    R = glide_range(h=1000, CL=CL_cruise, CD=CD_cruise)  # glide from 1000 m

    print(f"Stall speed:        {V_stall:6.2f} m/s  ({V_stall*3.6:6.1f} km/h)")
    print(f"Cruise speed @CL:   {V_cruise:6.2f} m/s  ({V_cruise*3.6:6.1f} km/h)")
    print(f"CD at cruise CL:    {CD_cruise:6.4f}")
    print(f"Glide ratio L/D:    {LD:6.2f} : 1")
    print(f"Glide angle:        {gamma:6.2f} deg")
    print(f"Range from 1000 m:  {R/1000:6.2f} km")

    # --- Best glide ratio scanning range of CL values ---
    best_LD = 0
    best_CL = 0
    for CL_test in [i / 100 for i in range(10, 150)]:  # CL from 0.10 to 1.49
        CD_test = drag_coefficient(CL_test, CD0, AR, e)
        LD_test = glide_ratio(CL_test, CD_test)
        if LD_test > best_LD:
            best_LD = LD_test
            best_CL = CL_test

    print(f"\nBest L/D:           {best_LD:6.2f} : 1  at CL = {best_CL:.2f}")
    print(f"Min glide angle:     {glide_angle_deg(best_CL, drag_coefficient(best_CL, CD0, AR, e)):6.2f} deg")
