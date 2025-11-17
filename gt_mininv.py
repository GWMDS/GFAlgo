# ==============================================================
# Giffler-Thompson Algorithmus mit DEVIATION (Quadratische Abweichung)
# ==============================================================

import pandas as pd
import json
from pathlib import Path
import matplotlib.pyplot as plt

# -------------------------------
# Dateien
# -------------------------------
csv_file = "routing.csv"
previous_schedule_file = Path("previous_schedule.json")

# -------------------------------
# CSV einlesen
# -------------------------------
df = pd.read_csv(csv_file)
df.columns = [c.strip() for c in df.columns] #entfernt führende und nachfolgende Leerzeichen aus allen Spaltennamen

# -------------------------------
# Datenstruktur vorbereiten
# -------------------------------
jobs = {}
machines = {}
machine_ids = sorted(df["Machine"].unique()) #sortiert alle Maschinen

for _, row in df.iterrows(): #gibt jede Zeile der CSV Datei zurück
    job_id = int(row["Routing_ID"])      #liest die Daten ein und wandelt sie gegebenfalls um
    op_id = int(row["Operation"])
    machine = row["Machine"]
    pt = int(row["Processing Time"])

    if job_id not in jobs: #Jobs anlegen im Dictionary, falls noch nicht vorhanden 0-9
        jobs[job_id] = []
    jobs[job_id].append({ #Operation zum Job hinzufügen
        "op": op_id,
        "machine": machine,
        "pt": pt,
        "start": None,
        "end": None
    })

    if machine not in machines: #Prüfung ob Maschine schon vorhanden, wenn nicht leere Liste der Maschinen anlegen
        machines[machine] = []

# -------------------------------
# Previous schedule laden (KOZ-Plan)
# -------------------------------
if previous_schedule_file.exists(): #Prüfen ob ein Vortagsplan existiert

   #Backup
    backup_file = Path("previous_schedule_backup.json") #Datei festlegen
    with open(previous_schedule_file, "r") as f_src: #Erstellung eines Backups--> vllt Ergänzung eines
        with open(backup_file, "w") as f_backup:
            f_backup.write(f_src.read())

    with open(previous_schedule_file, "r") as f: #Vortags Plan einlesen
        previous_schedule = json.load(f)    #konvertierung in lesbares Dictionary
else:
    previous_schedule = []


def get_prev_start(job_id, op_id): #Startzeitpunkt der vorherigen Planung zurückgeben
    for op in previous_schedule:    #durchlaufen jeder einzelnen Operation
        if op["job"] == job_id and op["op"] == op_id + 1: #Prüfung ob gleicher Job gefunden wird, +1 da JSON Datei dort anfängt
            return op["start"] # Abweichung zum neuen Plan, für Berechnung
    return None

# -------------------------------
# Giffler-Thompson Hauptschleife
# -------------------------------
scheduled_ops = [] #leere Liste für geplante Operationen

while any(any(op["start"] is None for op in ops) for ops in jobs.values()): #Prüfung ob Job noch nicht geplante Operationen hat; 
                                                                            #erstes any prüft über alle Jobs hinweg; values gibt alle Operationen zurück
    # 1. Nächste planbare Operationen pro Job
    next_ops = [] #Speicher für nächste planbare Operationen pro Job
    for job_id, ops in jobs.items(): #liefert job_id, operationsliste(1: [op1, op2, op3])
        for idx, op in enumerate(ops): # gibt idx und Wert zurück der Operation
            if op["start"] is None: #Schauen ob die Operation noch keinen Startzeitpunkt hat
                prev_end = 0 #Startwert des Vorgängers, im ersten Durchlauf 0
                if idx > 0: #direkten Vorgänger aus Liste holen, wenn Index nicht NUll
                    prev_op = ops[idx - 1]
                    if prev_op["end"] is None:#Falls Vorgänger noch in Bearbeitung, Abbrechen
                        break
                    prev_end = prev_op["end"]#Vorgänger Ende Übernehmen
                next_ops.append((job_id, idx, prev_end, op)) #Operation einplanen, mit Vorgänger Ende als Startzeit
                break #Nur die erste ungeschedulte Operation pro Job

    if not next_ops: #Falls es keine planbaren Operationen gibt → Ende
        break

    # 2. Konfliktmenge pro Maschine identifizieren
    conflict_ops_per_machine = {} #Konfliktmenge pro Maschine
    for job_id, idx, earliest_start, op in next_ops: #aktuell einplanbare Operationen durchlaufen wegen next_ops
        m_schedule = machines[op["machine"]]# auslesen um zu sehen wann MAschine frei
        m_available = max([o["end"] for o in m_schedule], default=0) #liste der Endzeiten aller Maschinen
        start_time = max(earliest_start, m_available)#Tatsächlicher Startzeitpunkt der Operation
        end_time = start_time + op["pt"] #Endzeit berechnen mithilfe der Processing Time

        if op["machine"] not in conflict_ops_per_machine: #Konfliktliste für diese Maschine anlegen
            conflict_ops_per_machine[op["machine"]] = []
        conflict_ops_per_machine[op["machine"]].append(#Speicherung des Tupels 
            (job_id, idx, start_time, end_time, op)
        )

    # ------------------------------------------------------
    # 3. DEVIATION (Quadratische Abweichung)
    # ------------------------------------------------------
    selected_ops = []#Liste zur Speicherung der ausgwählten Operationen

    for m, candidates in conflict_ops_per_machine.items(): #Konfliktliste pro Maschine durchgehen
        deviations = [] # Liste zur Speicherung der Berechnung
        for job_id, idx, start_time, end_time, op in candidates: #jeder Operation durchgehen die um die Maschine konkurriert

            prev_start = get_prev_start(job_id, idx) #Startzeit der vorherigen Operation des Vortages

            if prev_start is not None:
                raw_dev = abs(prev_start - start_time) #absolute Abweichung berechnen
                deviation = raw_dev ** 2      #Quadratische Abweichungsstrafe
            else:
                deviation = float('inf') #jobs werden nur gewählt wenn es keine andere Wahl gibt

            # Speichere: (deviation, end_time, job_id, idx, original_data)
            deviations.append(
                (deviation, end_time, job_id, idx,
                 (job_id, idx, start_time, end_time, op))
            )

        # kleinstes deviation → stabilster Plan; deviations=(deviation, end_time, job_id, idx, 'original_data')
        best = min(deviations, key=lambda x: (x[0], x[1], x[2]))#Kriterien --> deviation --> end_time--> job_id
        selected_ops.append(best[4])#original Tupel anfügen (job_id, idx, start_time, end_time, op)

    # 4. Unter allen Maschinen: Operation mit kleinstem Endzeitpunkt
    job_id, idx, start_time, end_time, op = min(selected_ops, key=lambda x: x[3])#Operation mit frühester Endzeit

    # 5. Operation einplanen
    op["start"] = start_time # berechneten Startzeitpunkt eintragen
    op["end"] = end_time
    machines[op["machine"]].append(op) #eingeplante Operation in Mshcinen Dictionary eintragen
    scheduled_ops.append((job_id, idx, op["machine"], start_time, end_time))# Operation in die finale Schedule-Liste eintragen

# -------------------------------
# Schedule speichern
# -------------------------------
schedule = [
    {"job": job_id, "op": idx + 1, "machine": m, "start": start, "end": end}
    for job_id, idx, m, start, end in scheduled_ops
]

schedule.sort(key=lambda x: (machine_ids.index(x["machine"]), x["start"]))

with open(previous_schedule_file, "w") as f:
    json.dump(schedule, f, indent=4)

makespan = max(s["end"] for s in schedule)
print(f"Makespan: {makespan}")

# -------------------------------
# Farben für Jobs festlegen
# -------------------------------
job_ids = sorted(jobs.keys())
colors_palette = [
    'tab:blue','tab:orange','tab:green','tab:red','tab:purple',
    'tab:brown','tab:pink','tab:gray','tab:olive','tab:cyan'
]
job_colors = {job_id: colors_palette[i % len(colors_palette)]
              for i, job_id in enumerate(job_ids)}

# -------------------------------
# Gantt-Diagramm
# -------------------------------
fig, ax = plt.subplots(figsize=(12, 6))

for s in schedule:
    color = job_colors[s['job']]
    ax.barh(
        f"Maschine {s['machine']}",
        s['end'] - s['start'],
        left=s['start'],
        color=color,
        edgecolor='black'
    )
    ax.text(
        s['start'] + (s['end'] - s['start']) / 2,
        f"Maschine {s['machine']}",
        f"Job {s['job']}",
        va='center',
        ha='center',
        color='white',
        fontsize=9
    )

ax.set_xlabel("Zeit")
ax.set_ylabel("Maschinen")
ax.set_title("Giffler-Thompson mit quadratischer DEVIATION_INSERT")
ax.grid(True, axis='x', linestyle='--', alpha=0.6)
plt.tight_layout()

output_file = "gantt_schedule.png"
plt.savefig(output_file, dpi=300)
print(f"Gantt-Diagramm gespeichert als {output_file}")

plt.show()
