#!/usr/bin/env python3
"""Convergence extrapolation for the Chromatic Census.

Fits multiple convergence models to the census results at four grid
resolutions, then extrapolates to h → 0 to estimate the true number
of perceptually distinguishable colors.

Usage:
    python results/convergence_extrapolation.py
"""

import numpy as np
from scipy.optimize import minimize

# ── Census data ──────────────────────────────────────────────────────
# L* step is the characteristic grid spacing (a*/b* steps are always 2×L*)
RUNS = {
    "Coarse":    {"h": 1.0,    "JND": 172_588, "Acceptability": 35_873, "Obvious": 12_467},
    "Fine":      {"h": 0.5,    "JND": 276_941, "Acceptability": 45_038, "Obvious": 15_446},
    "Superfine": {"h": 0.125,  "JND": 299_370, "Acceptability": 48_675, "Obvious": 16_456},
    "Ultrafine": {"h": 0.0625, "JND": 321_930, "Acceptability": 51_868, "Obvious": 17_313},
}

TIERS = ["JND", "Acceptability", "Obvious"]
DELTA_E = {"JND": 2.3, "Acceptability": 5.0, "Obvious": 10.0}

h_vals = np.array([r["h"] for r in RUNS.values()])
run_names = list(RUNS.keys())


# ── Model A: Power law  N(h) = N∞ + a·h^p ───────────────────────────
def power_law(h, N_inf, a, p):
    return N_inf + a * np.power(h, p)


def fit_power_law(tier):
    """Fit power-law model using least squares with multiple restarts."""
    counts = np.array([r[tier] for r in RUNS.values()], dtype=float)
    best_cost = np.inf
    best_params = None

    for N_inf_mult in [1.05, 1.1, 1.2, 1.5, 2.0]:
        for p_init in [0.3, 0.5, 1.0, 1.5, 2.0]:
            N_inf_0 = counts[-1] * N_inf_mult
            a_0 = (counts[0] - N_inf_0) / (h_vals[0] ** p_init)

            def cost(params):
                N_inf, a, p = params
                if p <= 0 or N_inf <= 0:
                    return 1e18
                pred = power_law(h_vals, N_inf, a, p)
                return np.sum(((pred - counts) / counts) ** 2)

            res = minimize(cost, [N_inf_0, a_0, p_init],
                           method="Nelder-Mead", options={"maxiter": 50000, "xatol": 1, "fatol": 1e-12})
            if res.fun < best_cost and res.x[0] > counts[-1] and res.x[2] > 0:
                best_cost = res.fun
                best_params = res.x

    if best_params is None:
        return None

    N_inf, a, p = best_params
    fitted = power_law(h_vals, *best_params)
    rel_err = np.abs((fitted - counts) / counts) * 100
    return {"N_inf": N_inf, "a": a, "p": p, "fitted": fitted,
            "rel_err": rel_err, "counts": counts}


# ── Model B: Logarithmic  N(h) = N∞ + a·ln(h) ──────────────────────
def log_model(h, N_inf, a):
    return N_inf + a * np.log(h)


def fit_log_model(tier):
    """Fit logarithmic convergence model."""
    counts = np.array([r[tier] for r in RUNS.values()], dtype=float)
    log_h = np.log(h_vals)

    def cost(params):
        N_inf, a = params
        pred = N_inf + a * log_h
        return np.sum(((pred - counts) / counts) ** 2)

    # Initial guess from linear regression on log(h)
    slope = (counts[-1] - counts[0]) / (log_h[-1] - log_h[0])
    intercept = counts[-1] - slope * log_h[-1]

    res = minimize(cost, [intercept, slope], method="Nelder-Mead",
                   options={"maxiter": 50000})
    N_inf, a = res.x
    fitted = log_model(h_vals, N_inf, a)
    rel_err = np.abs((fitted - counts) / counts) * 100
    return {"N_inf": N_inf, "a": a, "fitted": fitted,
            "rel_err": rel_err, "counts": counts}


# ── Model C: Inverse power  N(h) = N∞ - b/(c + 1/h)^q ──────────────
# (saturating function of grid density)
def saturating_model(h, N_inf, b, c, q):
    density = 1.0 / h
    return N_inf - b / np.power(c + density, q)


def fit_saturating(tier):
    """Fit saturating-density model."""
    counts = np.array([r[tier] for r in RUNS.values()], dtype=float)
    best_cost = np.inf
    best_params = None

    for N_inf_mult in [1.05, 1.1, 1.2, 1.5, 2.0, 3.0]:
        for q_init in [0.5, 1.0, 1.5]:
            N_inf_0 = counts[-1] * N_inf_mult
            def cost(params):
                N_inf, b, c, q = params
                if N_inf <= 0 or b <= 0 or c < 0 or q <= 0:
                    return 1e18
                pred = saturating_model(h_vals, N_inf, b, c, q)
                if np.any(pred <= 0):
                    return 1e18
                return np.sum(((pred - counts) / counts) ** 2)

            res = minimize(cost, [N_inf_0, N_inf_0, 1.0, q_init],
                           method="Nelder-Mead",
                           options={"maxiter": 100000, "xatol": 1, "fatol": 1e-12})
            if res.fun < best_cost and res.x[0] > counts[-1]:
                best_cost = res.fun
                best_params = res.x

    if best_params is None:
        return None

    N_inf, b, c, q = best_params
    fitted = saturating_model(h_vals, *best_params)
    rel_err = np.abs((fitted - counts) / counts) * 100
    return {"N_inf": N_inf, "b": b, "c": c, "q": q, "fitted": fitted,
            "rel_err": rel_err, "counts": counts}


# ── Volumetric estimate (theoretical upper bound) ────────────────────
def volumetric_estimate():
    """Estimate maximum packing from sRGB gamut volume in CIELAB.

    The sRGB gamut volume in CIELAB is approximately 830,000 ΔE³ units.
    (Measured empirically by many studies; Pointer's gamut is ~920,000.)

    For sphere packing, the maximum density is π/(3√2) ≈ 0.7405 (FCC).
    Random packing achieves ~0.64. Greedy packing (sequential, not
    optimized) typically achieves ~0.55-0.60 of maximum.

    Volume of a ΔE sphere = (4/3)π(ΔE/2)³
    """
    V_gamut = 830_000  # ΔE³ — approximate sRGB CIELAB volume

    # NOTE: ΔE2000 warps the space non-uniformly, so sphere volumes vary
    # by region. This is a rough estimate using CIELAB ΔE76 volume as proxy.
    print("  Gamut volume: ~830,000 ΔE³ (CIELAB, approximate)")
    print("  Packing efficiencies: FCC optimal 74%, random 64%, greedy ~55-60%")
    print()

    for tier in TIERS:
        de = DELTA_E[tier]
        V_sphere = (4/3) * np.pi * (de/2)**3
        N_fcc = int(V_gamut * 0.7405 / V_sphere)
        N_random = int(V_gamut * 0.64 / V_sphere)
        N_greedy = int(V_gamut * 0.58 / V_sphere)
        print(f"  {tier} (ΔE={de}):")
        print(f"    Sphere vol = {V_sphere:.1f} ΔE³")
        print(f"    FCC optimal:  {N_fcc:>10,}")
        print(f"    Random pack:  {N_random:>10,}")
        print(f"    Greedy pack:  {N_greedy:>10,}")
        print()


# ── Main ─────────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("CHROMATIC CENSUS — CONVERGENCE EXTRAPOLATION")
    print("=" * 70)
    print()
    print("Grid spacings (L* step): ", [f"{h}" for h in h_vals])
    print("Note: Fine→Superfine is a 4× jump, others are 2×")
    print()

    # ── Fit all models ───────────────────────────────────────────────
    all_results = {}

    for model_name, fit_fn, desc in [
        ("Power law", fit_power_law, "N(h) = N∞ + a·h^p"),
        ("Logarithmic", fit_log_model, "N(h) = N∞ + a·ln(h)"),
        ("Saturating", fit_saturating, "N(h) = N∞ - b/(c + 1/h)^q"),
    ]:
        print("─" * 70)
        print(f"MODEL: {model_name}  —  {desc}")
        print("─" * 70)

        for tier in TIERS:
            result = fit_fn(tier)
            if result is None:
                print(f"\n  {tier}: FAILED TO FIT")
                continue

            all_results.setdefault(model_name, {})[tier] = result
            counts = result["counts"]
            fitted = result["fitted"]
            rel_err = result["rel_err"]

            print(f"\n  {tier}:  N∞ = {result['N_inf']:,.0f}")
            print(f"    {'Run':<12} {'Observed':>10} {'Fitted':>10} {'Error':>8}")
            for name, obs, fit, err in zip(run_names, counts, fitted, rel_err):
                print(f"    {name:<12} {obs:>10,.0f} {fit:>10,.0f} {err:>7.2f}%")
            print(f"    Max error: {rel_err.max():.2f}%")

        print()

    # ── Volumetric upper bound ───────────────────────────────────────
    print("─" * 70)
    print("VOLUMETRIC ESTIMATE (theoretical, from gamut volume + sphere packing)")
    print("─" * 70)
    print()
    volumetric_estimate()

    # ── Summary comparison ───────────────────────────────────────────
    print("=" * 70)
    print("SUMMARY — Extrapolated limits (N∞) by model")
    print("=" * 70)
    print()
    print(f"  {'Tier':<16}", end="")
    for model_name in all_results:
        print(f" {model_name:>12}", end="")
    print(f" {'Ultrafine':>12}")

    for tier in TIERS:
        print(f"  {tier:<16}", end="")
        estimates = []
        for model_name in all_results:
            if tier in all_results[model_name]:
                val = all_results[model_name][tier]["N_inf"]
                estimates.append(val)
                print(f" {val:>12,.0f}", end="")
            else:
                print(f" {'FAIL':>12}", end="")
        current = RUNS["Ultrafine"][tier]
        print(f" {current:>12,}")

        if len(estimates) >= 2:
            lo, hi = min(estimates), max(estimates)
            mid = np.mean(estimates)
            captured = current / mid * 100
            # Excluding the log model for the "definitive" range if it diverges
            finite_est = [e for e in estimates if e > 0 and e < current * 10]
            if finite_est:
                lo_f, hi_f = min(finite_est), max(finite_est)

    # ── Best estimate ────────────────────────────────────────────────
    print()
    print("─" * 70)
    print("BEST ESTIMATE")
    print("─" * 70)
    print()
    print("  The logarithmic model N(h) = N∞ + a·ln(h) implies NO finite limit —")
    print("  as the grid gets finer, counts grow without bound (slowly).")
    print()
    print("  If the log model fits well, it means the census hasn't reached the")
    print("  asymptotic regime and more resolution will always find more colors.")
    print()
    print("  The power-law and saturating models DO have finite limits.")
    print("  Their agreement (or disagreement) indicates confidence.")
    print()

    for tier in TIERS:
        estimates = []
        for model_name in ["Power law", "Saturating"]:
            if model_name in all_results and tier in all_results[model_name]:
                estimates.append(all_results[model_name][tier]["N_inf"])

        # Check log model fit quality
        log_err = 999
        if "Logarithmic" in all_results and tier in all_results["Logarithmic"]:
            log_err = all_results["Logarithmic"][tier]["rel_err"].max()

        pw_err = all_results.get("Power law", {}).get(tier, {})
        pw_err = pw_err["rel_err"].max() if pw_err else 999

        current = RUNS["Ultrafine"][tier]

        if estimates:
            lo, hi = min(estimates), max(estimates)
            mid = int(np.mean(estimates))
            spread_pct = (hi - lo) / mid * 100

            print(f"  {tier}:")
            print(f"    Finite-limit models: {lo:,.0f} — {hi:,.0f}  (spread: {spread_pct:.1f}%)")
            print(f"    Midpoint estimate:   {mid:,}")
            print(f"    Log model max error: {log_err:.2f}%  (lower = log model fits well = no finite limit)")
            print(f"    Power-law max error: {pw_err:.2f}%")
            print(f"    Ultrafine captures:  {current/mid*100:.1f}% of midpoint estimate")
            print()

    print("─" * 70)
    print("RECOMMENDATION")
    print("─" * 70)
    print()
    print("  Compare the max errors of the logarithmic vs power-law models.")
    print("  If the log model fits significantly better, the counts are still")
    print("  growing logarithmically and a single 'definitive number' requires")
    print("  either (a) a much finer run to enter the asymptotic regime, or")
    print("  (b) acknowledging that the answer depends on measurement precision.")
    print()


if __name__ == "__main__":
    main()
