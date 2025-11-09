# -*- coding: utf-8 -*-
# Minimalinvasives Job-Shop-Scheduling (Giffler–Thompson + MinInv-Tie-Break)
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set
import math

# =========================
# Beispiel-Daten
# =========================
# jobs[job_id] = Liste von (machine_id, duration)
jobs: Dict[int, List[Tuple[int, int]]] = {
    1: [(1, 2), (2, 5), (3, 4)],      # Job 1: O11 auf M1, O12 auf M2, O13 auf M3
    2: [(2, 2), (1, 3), (3, 2)],      # Job 2: O21 auf M2, O22 auf M1, O23 auf M3
    3: [(3, 3), (2, 2)]               # Job 3: O31 auf M3, O32 auf M2
}
machines: Set[int] = set(m for ops in jobs.values() for (m, _) in ops)

# -------------------------
# "Basisplan": Plan-Treue
# -------------------------
# Baseline-Reihenfolge pro Maschine (aus einem alten Plan):
# (job_id, op_index) => Reihenfolge auf Maschine
base_order: Dict[int, List[Tuple[int, int]]] = {
    1: [(1, 0), (2, 1)],                # M1: erst (1,0), dann (2,1)
    2: [(1, 1), (2, 0), (3, 1)],        # M2: (1,1) -> (2,0) -> (3,1)
    3: [(1, 2), (2, 2), (3, 0)],        # M3: (1,2) -> (2,2) -> (3,0)
}

# Geplante Startzeiten aus dem Basisplan (nur als Orientierung/Plan-Treue).
# Negative Zeit => „überfällig“ (war gestern geplant, noch offen).
plan_start: Dict[Tuple[int, int], float] = {
    (1, 0): 0.0,   (1, 1): 2.0,  (1, 2): 7.0,
    (2, 0): 0.5,   (2, 1): 3.0,  (2, 2): 6.5,
    (3, 0): -1.0,  (3, 1): 1.5,               # (3,0) ist überfällig (war „gestern“)
}

NOW = 0.0                     # „Jetzt“-Zeitpunkt (Rolling Horizon Start)
ROLLING_HORIZON_END = 8.0     # Alles mit Planstart >> Horizont bleibt zunächst eingefroren

# MinInv-Gewichte: Überfälligkeit/Verspätung >> Reihenfolgeabweichung >= Startverschiebung
ALPHA = 10.0
BETA  = 3.0
GAMMA = 1.0

# =========================
# Hilfsstrukturen
# =========================
@dataclass(frozen=True)
class Op:
    job: int
    idx: int
    machine: int
    duration: float

def build_ops(jobs: Dict[int, List[Tuple[int, int]]]) -> Dict[Tuple[int, int], Op]:
    ops = {}
    for j, seq in jobs.items():
        for i, (m, d) in enumerate(seq):
            ops[(j, i)] = Op(j, i, m, float(d))
    return ops

OPS = build_ops(jobs)

# =========================
# GT-Hilfsfunktionen
# =========================
def pos_in_base(machine: int, op_key: Tuple[int, int]) -> int:
    """Position einer Operation im Basisplan auf der Maschine (klein = früh)."""
    if machine not in base_order:
        return 10**6
    order = base_order[machine]
    try:
        return order.index(op_key)
    except ValueError:
        return 10**6

def is_overdue(op_key: Tuple[int, int]) -> bool:
    """Überfällig: geplanter Start < NOW."""
    return plan_start.get(op_key, math.inf) < NOW

def in_rolling_horizon(op_key: Tuple[int, int]) -> bool:
    """Im Rolling Horizon: plane vor allem, was jetzt bis Horizont relevant ist."""
    ps = plan_start.get(op_key, NOW)
    # Überfällige und kurzfristige OPs sind im Fokus:
    return (ps <= ROLLING_HORIZON_END) or is_overdue(op_key)

def earliest_start_time(
    op_key: Tuple[int, int],
    scheduled_on_machine: Dict[int, List[Tuple[float, float, Tuple[int, int]]]],
    op_finish: Dict[Tuple[int, int], float],
) -> float:
    """Frühester Start unter Beachtung: Vorgänger im Job & aktueller Maschinenbelegung (ohne Lücken-Suche)."""
    op = OPS[op_key]
    # Vorgänger-Zwang (innerhalb des Jobs)
    prev_end = 0.0
    if op.idx > 0:
        prev_key = (op.job, op.idx - 1)
        prev_end = op_finish.get(prev_key, 0.0)

    # Maschine frei ab:
    m = op.machine
    if m not in scheduled_on_machine or not scheduled_on_machine[m]:
        mach_free = 0.0
    else:
        # Wir bauen sequentiell: „frei ab“ = Ende der letzten belegten OP
        mach_free = scheduled_on_machine[m][-1][1]

    return max(prev_end, mach_free)

def earliest_completion_time(op_key, scheduled_on_machine, op_finish) -> float:
    est = earliest_start_time(op_key, scheduled_on_machine, op_finish)
    return est + OPS[op_key].duration

def conflict_set_and_critical(
    ready_ops: List[Tuple[int, int]],
    scheduled_on_machine: Dict[int, List[Tuple[float, float, Tuple[int, int]]]],
    op_finish: Dict[Tuple[int, int], float],
) -> Tuple[float, int, List[Tuple[int, int]]]:
    """
    Klassischer GT-Schritt:
    - finde kritisches frühestes Fertigstellen t* und dazugehörige Maschine M*
    - baue Konfliktset C = alle OPs auf M*, deren EST < t*
    """
    # 1) kritischer Abschluss
    best_t = math.inf
    best_m = None
    best_op = None
    for o in ready_ops:
        t = earliest_completion_time(o, scheduled_on_machine, op_finish)
        if t < best_t:
            best_t = t
            best_m = OPS[o].machine
            best_op = o

    # 2) Konfliktset auf der kritischen Maschine: alle mit EST < t*
    C = []
    for o in ready_ops:
        if OPS[o].machine != best_m:
            continue
        est = earliest_start_time(o, scheduled_on_machine, op_finish)
        if est < best_t:
            C.append(o)

    return best_t, best_m, C

def sequence_deviation_on_machine(op_key: Tuple[int, int], machine: int, scheduled_on_machine) -> int:
    """
    Approximierte Plan-Treue: Abweichung zur Basisreihenfolge.
    Wir vergleichen die geplante Position mit der „Ist“-Position (nächster Slot auf Maschine).
    """
    planned_pos = pos_in_base(machine, op_key)
    current_pos = len(scheduled_on_machine.get(machine, []))  # nächste Position, wenn wir jetzt einplanen
    return abs(planned_pos - current_pos)

def mininv_score(
    op_key: Tuple[int, int],
    scheduled_on_machine,
    op_finish,
    alpha=ALPHA, beta=BETA, gamma=GAMMA
) -> float:
    est = earliest_start_time(op_key, scheduled_on_machine, op_finish)
    delay = max(0.0, est - plan_start.get(op_key, est))          # Verspätung ggü. Basis
    seqdev = sequence_deviation_on_machine(op_key, OPS[op_key].machine, scheduled_on_machine)
    startshift = abs(est - plan_start.get(op_key, est))
    return alpha * delay + beta * seqdev + gamma * startshift

def pick_with_mininv(C: List[Tuple[int, int]], scheduled_on_machine, op_finish) -> Tuple[int, int]:
    """MinInv-Tie-Break: (1) überfällige/affektierte bevorzugen, (2) Score-Minimum, (3) früheste Fertigstellung."""
    # 1) Pflichtmenge: überfällige zuerst
    mandatory = [o for o in C if is_overdue(o)]
    candidate_set = mandatory if mandatory else C

    # 2) Score-Minimum + 3) sekundär kleinste ECT
    best = None
    bestScore = math.inf
    bestECT = math.inf
    for o in candidate_set:
        s = mininv_score(o, scheduled_on_machine, op_finish)
        ect = earliest_completion_time(o, scheduled_on_machine, op_finish)
        if (s < bestScore) or (math.isclose(s, bestScore) and ect < bestECT):
            best, bestScore, bestECT = o, s, ect
    return best

# =========================
# GT-Hauptschleife (MinInv)
# =========================
def giffler_thompson_mininv(jobs: Dict[int, List[Tuple[int, int]]]) -> Dict[int, List[Tuple[float, float, Tuple[int, int]]]]:
    # Zustand
    next_op_idx: Dict[int, int] = {j: 0 for j in jobs}           # nächste unbelegte OP je Job
    op_finish: Dict[Tuple[int, int], float] = {}                 # Fertigstellzeiten
    scheduled_on_machine: Dict[int, List[Tuple[float, float, Tuple[int, int]]]] = {m: [] for m in machines}

    # Menge aller OPs
    total_ops = sum(len(v) for v in jobs.values())

    while len(op_finish) < total_ops:
        # Freigegebene OPs: erste nicht-geplante OP je Job,
        # zusätzlich Rolling-Horizon-Filter (Plan-Treue stabil halten)
        ready_ops: List[Tuple[int, int]] = []
        for j, k in next_op_idx.items():
            if k >= len(jobs[j]):
                continue
            key = (j, k)
            if in_rolling_horizon(key):
                ready_ops.append(key)

        # Falls durch Horizon keine OP frei: weite Fenster minimal
        if not ready_ops:
            # nächster nicht-geplanter op (ohne Horizon) erzwingen
            for j, k in next_op_idx.items():
                if k < len(jobs[j]):
                    ready_ops.append((j, k))
                    break

        # Kritische Maschine & Konfliktset
        t_star, M_star, C = conflict_set_and_critical(ready_ops, scheduled_on_machine, op_finish)

        # MinInv-Auswahl
        chosen = pick_with_mininv(C, scheduled_on_machine, op_finish)

        # Einplanen
        est = earliest_start_time(chosen, scheduled_on_machine, op_finish)
        s = est
        e = est + OPS[chosen].duration
        scheduled_on_machine[M_star].append((s, e, chosen))
        op_finish[chosen] = e
        # nächste OP im Job freigeben
        j = chosen[0]
        next_op_idx[j] += 1

    return scheduled_on_machine

# =========================
# Ausführen & Ausgabe
# =========================
schedule = giffler_thompson_mininv(jobs)

print("---- Ergebnisplan (minimalinvasiv) ----")
for m in sorted(schedule):
    print(f"Maschine M{m}:")
    for (s, e, (j, i)) in schedule[m]:
        overdue_mark = " (überfällig bevorzugt)" if is_overdue((j, i)) else ""
        print(f"  Op J{j}-O{i+1}: {s:.2f} -> {e:.2f}{overdue_mark}")
    print()

# =========================
# Optional: einfaches Gantt (ASCII)
# =========================
def ascii_gantt(schedule, resolution=0.5):
    print("---- Gantt (ASCII, grob) ----")
    horizon = max(e for m in schedule for (_, e, _) in schedule[m])
    ticks = int(math.ceil(horizon / resolution))
    for m in sorted(schedule):
        line = [" "] * ticks
        labels = []
        for (s, e, (j, i)) in schedule[m]:
            a = int(s / resolution)
            b = int(e / resolution)
            for k in range(a, b):
                line[k] = "#"
            labels.append((a, f"J{j}O{i+1}"))
        print(f"M{m} |{''.join(line)}|")
        # primitive Label-Ausgabe
        lbl = "    "
        for a, t in labels:
            lbl += " " * max(0, a - len(lbl) + 4) + t
        print(lbl)
    print()

ascii_gantt(schedule)
