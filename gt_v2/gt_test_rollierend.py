import pandas as pd
import json
from pathlib import Path
import matplotlib.pyplot as plt
import random
import os

# ==============================================================
# KONFIGURATION
# ==============================================================
CSV_FILE = Path("routing.csv")
NUM_SHIFTS = 22       # Anzahl der Simulations-Runden
SIGMA = 0.1       # Stärke der Störungen

# ==============================================================
# HILFSFUNKTIONEN
# ==============================================================
def simulate_duration(planned_duration, sigma):
    """Erzeugt zufällige Ist-Zeit (Lognormal)"""
    if sigma <= 0: return planned_duration
    mu = -(sigma**2) / 2
    factor = random.lognormvariate(mu, sigma)
    return max(1, int(round(planned_duration * factor)))

def run_single_shift(jobs_data, prev_schedule_list):
    """
    Führt EINEN Planungslauf durch.
    Nutzt prev_schedule_list, um Startzeiten für Stabilität auszulesen.
    """
    
    # Mapping für schnellen Zugriff auf alte Startzeiten erstellen
    prev_starts_map = {}
    if prev_schedule_list:
        for item in prev_schedule_list:
            prev_starts_map[(item["job"], item["op"])] = item["start"]

    # 1. Daten für diesen Lauf vorbereiten (Störung simulieren)
    current_jobs = {}
    machines = {}
    
    for j_id, ops in jobs_data.items():
        current_jobs[j_id] = []
        for op in ops:
            sim_pt = simulate_duration(op["plan_pt"], SIGMA)
            current_jobs[j_id].append({
                "id": op["id"], "machine": op["machine"], "pt": sim_pt,
                "start": None, "end": None, "job_id": j_id
            })
            if op["machine"] not in machines: machines[op["machine"]] = []

    # 2. GT Algorithmus
    scheduled_ops = []
    
    while True:
        startable = []
        all_done = True
        
        for j_id, ops in current_jobs.items():
            for i, op in enumerate(ops):
                if op["start"] is None:
                    all_done = False
                    est_tech = 0
                    if i > 0:
                        prev = ops[i-1]
                        if prev["end"] is None: est_tech = None
                        else: est_tech = prev["end"]
                    
                    if est_tech is not None:
                        m_avail = max([o["end"] for o in machines[op["machine"]]], default=0)
                        actual_est = max(est_tech, m_avail)
                        startable.append({
                            "job_id": j_id, "op_idx": i,
                            "est": actual_est, "eft": actual_est + op["pt"],
                            "op": op
                        })
                    break
        
        if all_done: break
        if not startable: break
        
        min_eft = min(startable, key=lambda x: x["eft"])
        m_curr = min_eft["op"]["machine"]
        c_min = min_eft["eft"]
        conflict = [c for c in startable if c["op"]["machine"] == m_curr and c["est"] < c_min]
        
        # Entscheidung
        k_old = []
        k_new = []
        for c in conflict:
            ps = prev_starts_map.get((c["job_id"], c["op"]["id"]))
            if ps is not None:
                c["prev_start"] = ps
                k_old.append(c)
            else:
                k_new.append(c)
        
        selected = None
        if not prev_schedule_list:
            # Runde 1: KOZ
            selected = min(conflict, key=lambda x: (x["op"]["pt"], x["job_id"]))
        else:
            # Runde X: Minimalinvasiv
            best_old = min(k_old, key=lambda x: (x["prev_start"], x["job_id"])) if k_old else None
            best_new = min(k_new, key=lambda x: (x["op"]["pt"], x["job_id"])) if k_new else None
            
            if best_old and best_new:
                if (best_old["prev_start"] - best_new["eft"]) >= 0: selected = best_new
                else: selected = best_old
            elif best_old: selected = best_old
            elif best_new: selected = best_new
            else: selected = conflict[0]
            
        op = selected["op"]
        op["start"] = selected["est"]
        op["end"] = selected["eft"]
        machines[op["machine"]].append(op)
        
        scheduled_ops.append({
            "job": int(selected["job_id"]),
            "op": int(op["id"]),
            "machine": int(op["machine"]),
            "start": int(op["start"]),
            "end": int(op["end"])
        })
        
    return scheduled_ops

# ==============================================================
# BERECHNUNG DER METRIKEN
# ==============================================================
def calculate_metrics(new_schedule, old_schedule):
    if not old_schedule:
        return 0, 0 # Erste Runde hat keine Abweichung

    # 1. Startzeitabweichung
    old_starts = {(x["job"], x["op"]): x["start"] for x in old_schedule}
    time_dev = 0
    for new_op in new_schedule:
        old_start = old_starts.get((new_op["job"], new_op["op"]))
        if old_start is not None:
            time_dev += abs(new_op["start"] - old_start)

    # 2. Sequenzabweichung
    seq_dev = 0
    
    # Hilfsfunktion: Liste pro Maschine bauen, sortiert nach Startzeit
    def get_machine_queues(schedule_list):
        queues = {}
        # Sortieren wichtig für die Reihenfolge!
        sorted_list = sorted(schedule_list, key=lambda x: (x["machine"], x["start"]))
        for op in sorted_list:
            m = op["machine"]
            if m not in queues: queues[m] = []
            queues[m].append((op["job"], op["op"]))
        return queues

    new_queues = get_machine_queues(new_schedule)
    old_queues = get_machine_queues(old_schedule)

    # Vergleich pro Maschine
    for m, new_q in new_queues.items():
        if m not in old_queues: continue
        old_q = old_queues[m]
        
        # Nur gemeinsame Operationen betrachten
        common = set(new_q) & set(old_q)
        old_filtered = [op for op in old_q if op in common]
        new_filtered = [op for op in new_q if op in common]
        
        # Inversionen zählen
        for i in range(len(old_filtered)):
            for j in range(i + 1, len(old_filtered)):
                op_a = old_filtered[i]
                op_b = old_filtered[j]
                
                # Wenn A in der neuen Liste NACH B kommt, ist es eine Abweichung
                if new_filtered.index(op_a) > new_filtered.index(op_b):
                    seq_dev += 1
                    
    return time_dev, seq_dev

# ==============================================================
# MAIN: ROLLIERENDE SIMULATION
# ==============================================================

if not CSV_FILE.exists():
    print("Bitte routing.csv erstellen!")
    exit()

df = pd.read_csv(CSV_FILE)
df.columns = [c.strip() for c in df.columns]

base_jobs = {}
for _, row in df.iterrows():
    jid = int(row["Routing_ID"])
    if jid not in base_jobs: base_jobs[jid] = []
    base_jobs[jid].append({
        "id": int(row["Operation"]),
        "machine": int(row["Machine"]),
        "plan_pt": int(row["Processing Time"])
    })

# Speicher für Ergebnisse
history_time_dev = []
history_seq_dev = []
current_prev_schedule = [] # Hier speichern wir den kompletten Plan der Vorrunde

print(f"{'Schicht':<8} | {'Zeit-Abw.':<12} | {'Seq-Abw.':<10} | {'Makespan':<8}")
print("-" * 45)

for shift in range(1, NUM_SHIFTS + 1):
    
    # 1. Planen
    new_schedule = run_single_shift(base_jobs, current_prev_schedule)
    
    # 2. Messen
    t_dev, s_dev = calculate_metrics(new_schedule, current_prev_schedule)
    makespan = max(s["end"] for s in new_schedule)
    
    # 3. Speichern
    history_time_dev.append(t_dev)
    history_seq_dev.append(s_dev)
    
    print(f"{shift:02d}       | {t_dev:12d} | {s_dev:10d} | {makespan:8d}")
    
    # Update für nächste Runde
    current_prev_schedule = new_schedule

# ==============================================================
# VISUALISIERUNG (Dual Axis)
# ==============================================================
shifts = range(1, NUM_SHIFTS + 1)

fig, ax1 = plt.subplots(figsize=(10, 6))

color = 'tab:blue'
ax1.set_xlabel('Schicht')
ax1.set_ylabel('Startzeitabweichung (Min)', color=color)
ax1.plot(shifts, history_time_dev, color=color, marker='o', label='Startzeit-Abw.')
ax1.tick_params(axis='y', labelcolor=color)
ax1.grid(True, linestyle='--', alpha=0.5)

# Zweite y-Achse für Sequenzabweichung
ax2 = ax1.twinx()  
color = 'tab:red'
ax2.set_ylabel('Sequenzabweichung (Anzahl Swaps)', color=color)
ax2.plot(shifts, history_seq_dev, color=color, marker='x', linestyle='--', label='Sequenz-Abw.')
ax2.tick_params(axis='y', labelcolor=color)

plt.title(f"Rollierende Planung über {NUM_SHIFTS} Schichten (Sigma={SIGMA})")
fig.tight_layout()
plt.savefig("simulation_full_metrics.png", dpi=300)
print(f"\nGrafik gespeichert als 'simulation_full_metrics.png'.")
plt.show()