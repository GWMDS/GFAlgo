import csv
import random
from pathlib import Path

# ================================
# Parameter
# ================================
num_jobs = 10
num_operations = 10
machines = [f"M{str(i).zfill(2)}" for i in range(10)]  # M00 bis M09
processing_time_min = 10
processing_time_max = 100
routing_file = "routing.csv"  # Datei wird direkt überschrieben
changes_file = "routing_changes.csv"  # Datei für geänderte Operationen

# ================================
# Alte CSV-Daten laden
# ================================
old_data = {}
if Path(routing_file).exists():
    with open(routing_file, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            job_id = int(row["Routing_ID"])
            op_id = int(row["Operation"])
            if job_id not in old_data:
                old_data[job_id] = {}
            old_data[job_id][op_id] = {
                "Machine": row["Machine"],
                "Processing Time": int(row["Processing Time"])
            }

# ================================
# Einen zufälligen Job auswählen, der komplett neu generiert wird
# ================================
random_job = random.choice(range(num_jobs))

# ================================
# CSV-Dateien überschreiben und Änderungen speichern
# ================================
changed_ops = []  # Liste für geänderte Operationen

with open(routing_file, mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Routing_ID", "Operation", "Machine", "Processing Time"])
    
    for job_id in range(num_jobs):
        for op_id in range(num_operations):

            if job_id == random_job:
                # Komplett neu generieren
                new_machine = random.choice(machines)
                new_pt = random.randint(processing_time_min, processing_time_max)

                # alten Wert abrufen (falls vorhanden)
                if job_id in old_data and op_id in old_data[job_id]:
                    old_machine = old_data[job_id][op_id]["Machine"]
                    old_pt = old_data[job_id][op_id]["Processing Time"]
                else:
                    old_machine = None
                    old_pt = None

                changed_ops.append([job_id, op_id, new_machine, old_pt, new_pt])
                machine = new_machine
                processing_time = new_pt

            else:
                # Unveränderte alten Werte übernehmen
                if job_id in old_data and op_id in old_data[job_id]:
                    machine = old_data[job_id][op_id]["Machine"]
                    processing_time = old_data[job_id][op_id]["Processing Time"]
                else:
                    # falls etwas fehlt → neutral generieren (sollte nicht passieren)
                    machine = random.choice(machines)
                    processing_time = random.randint(processing_time_min, processing_time_max)

            writer.writerow([job_id, op_id, machine, processing_time])

# ================================
# Änderungen in separate CSV schreiben
# ================================
with open(changes_file, mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Routing_ID", "Operation", "Machine", "Old Processing Time", "New Processing Time"])
    writer.writerows(changed_ops)

print(f"Routing-Datei '{routing_file}' erfolgreich aktualisiert.")
print(f"Geänderte Operationen wurden in '{changes_file}' gespeichert.")
print(f"Random-Job vollständig neu generiert: {random_job}")
