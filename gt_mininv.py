# -*- coding: utf-8 -*-
# Giffler–Thompson mit "Plan-Treue + MinInv" + PDF-Export (robust für Windows/PowerShell)

import math
import os
import sys

# ---- Konsole auf UTF-8 umstellen (wenn möglich), sonst drucken wir ASCII ----
try:
    sys.stdout.reconfigure(encoding="utf-8")
    ARROW = "→"
except Exception:
    ARROW = "->"

# ---- Matplotlib headless nutzen, damit nur PDFs geschrieben werden ----
import matplotlib
matplotlib.use("Agg")  # kein GUI/Display erforderlich
import matplotlib.pyplot as plt
import pandas as pd

# -------------------------------------------------------------
# Eingabedaten (Beispiel – bei Bedarf anpassen)
# -------------------------------------------------------------
jobs = {
    1: [(1, 2), (2, 5), (3, 4)],  # Auftrag 1
    2: [(2, 2), (3, 3), (1, 5)],  # Auftrag 2
    3: [(3, 4), (1, 2), (2, 3)]   # Auftrag 3
}

# Vorplan-Infos (Vortag)
prev_start = {
    (1,0): 1,  (1,1): 6,  (1,2): 10,
    (2,0): 1,  (2,1): 4,  (2,2): 9,
    (3,0): 2,  (3,1): 5,  (3,2): 8,
}

prev_seq_per_machine = {
    1: [(1,0), (3,1), (2,2)],
    2: [(2,0), (1,1), (3,2)],
    3: [(3,0), (2,1), (1,2)]
}

# Parameter
USE_CYCLIC_TOD = True    # Tageszeit-Vergleich (01:00 ≈ 01:00 Folgetag)
DAY_PERIOD     = 24
W_TIME = 1.0             # Gewicht Plan-Treue
W_SEQ  = 0.1             # Gewicht Maschinenreihenfolge

# -------------------------------------------------------------
# Hilfsfunktionen
# -------------------------------------------------------------
def cyclic_distance(x, y, period=24):
    a = (x - y) % period
    b = (y - x) % period
    return min(a, b)

def time_deviation_cost(cand_start, preferred, use_cyclic, period):
    if preferred is None or math.isinf(preferred):
        return 0.0
    return cyclic_distance(cand_start, preferred, period) if use_cyclic else abs(cand_start - preferred)

def seq_position_cost(machine, op, prev_seq_per_machine):
    seq = prev_seq_per_machine.get(machine, [])
    return seq.index(op) if op in seq else 10**6

# -------------------------------------------------------------
# Giffler-Thompson (Plan-Treue + MinInv)
# -------------------------------------------------------------
machines = {1: 0, 2: 0, 3: 0}
S = [(j, 0) for j in jobs]
t = {(j, i): 0 for j in jobs for i in range(len(jobs[j]))}
start_times, end_times = {}, {}

while S:
    # Früheste Endzeit je Operation
    d = {}
    for job, i in S:
        m, p = jobs[job][i]
        est = max(t[(job, i)], machines[m])
        d[(job, i)] = est + p

    # Konfliktmaschine
    omin = min(d, key=d.get)
    dmin = d[omin]
    mach_min = jobs[omin[0]][omin[1]][0]

    # Konfliktmenge
    K = [(j, i) for j, i in S if jobs[j][i][0] == mach_min and t[(j, i)] < dmin]

    # Auswahlregel: Plan-Treue -> Reihenfolge -> KOZ
    def selection_score(op):
        j, i = op
        m, p = jobs[j][i]
        cand_start = max(t[(j, i)], machines[m])
        pref = prev_start.get((j, i))
        c_time = time_deviation_cost(cand_start, pref, USE_CYCLIC_TOD, DAY_PERIOD)
        c_seq  = seq_position_cost(m, op, prev_seq_per_machine)
        return (W_TIME * c_time, W_SEQ * c_seq, p)

    o_bar = min(K, key=selection_score)

    # Einplanung
    j, i = o_bar
    m, p = jobs[j][i]
    start = max(t[(j, i)], machines[m])
    end = start + p
    start_times[o_bar] = start
    end_times[o_bar] = end
    machines[m] = end

    # t-Update für K\{o_bar}
    for o in K:
        if o != o_bar:
            t[o] = end

    # Nachfolger hinzufügen
    if i + 1 < len(jobs[j]):
        S.append((j, i + 1))
        t[(j, i + 1)] = end

    S.remove(o_bar)

# -------------------------------------------------------------
# DataFrames erzeugen
# -------------------------------------------------------------
# Neuer Plan
rows_current = []
for (job, i), start in start_times.items():
    mach, dur = jobs[job][i]
    rows_current.append({
        "Job": job, "Op": i+1, "Maschine": mach,
        "Start": float(start), "Ende": float(end_times[(job, i)])
    })
df_current = pd.DataFrame(rows_current).sort_values(["Maschine", "Start"]).reset_index(drop=True)

# Vorplan
rows_prev = []
for (job, i), s in prev_start.items():
    mach, dur = jobs[job][i]
    rows_prev.append({
        "Job": job, "Op": i+1, "Maschine": mach,
        "Start": float(s), "Ende": float(s + dur)
    })
df_prev = pd.DataFrame(rows_prev).sort_values(["Maschine", "Start"]).reset_index(drop=True)

# -------------------------------------------------------------
# Gantt-Funktion (PDF-Export)
# -------------------------------------------------------------
def gantt_to_pdf(df, title, pdf_path):
    machines_sorted = sorted(df["Maschine"].unique())
    y_positions = {m: idx for idx, m in enumerate(machines_sorted[::-1])}

    plt.figure(figsize=(10, 4 + 0.4*len(machines_sorted)))
    for _, r in df.iterrows():
        y = y_positions[r["Maschine"]]
        plt.barh(y, r["Ende"] - r["Start"], left=r["Start"])  # keine Farbe explizit setzen
        label = f"J{int(r['Job'])}-O{int(r['Op'])}"
        x_center = r["Start"] + (r["Ende"] - r["Start"]) / 2.0
        plt.text(x_center, y, label, va="center", ha="center")

    plt.yticks(list(y_positions.values()), [f"M{m}" for m in machines_sorted[::-1]])
    plt.xlabel("Zeit")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(pdf_path, format="pdf")
    plt.close()

# -------------------------------------------------------------
# Diagramme speichern (im selben Ordner wie dieses Skript)
# -------------------------------------------------------------
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
pdf_prev = os.path.join(OUT_DIR, "Gantt_Vortag.pdf")
pdf_curr = os.path.join(OUT_DIR, "Gantt_Aktuell.pdf")

gantt_to_pdf(df_prev,    "Gantt – Vortag (Vorplan)", pdf_prev)
gantt_to_pdf(df_current, "Gantt – aktueller Tag (neuer Plan)", pdf_curr)

# -------------------------------------------------------------
# Ergebnis ausgeben
# -------------------------------------------------------------
print(df_current.to_string(index=False))
makespan_current = df_current["Ende"].max()
print("\nMakespan (aktueller Plan):", makespan_current)
print(f"\nPDF-Dateien gespeichert als:\n  {ARROW} {pdf_prev}\n  {ARROW} {pdf_curr}")
