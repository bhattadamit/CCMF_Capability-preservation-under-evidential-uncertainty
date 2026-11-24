#!/usr/bin/env python3
"""
CCMF reference executable specification and small-scope verification harness.
Supplementary file S1 to the manuscript.  Standard library only (Python >= 3.8).

Run:  python3 ccmf_spec.py            (full verification, ~1-3 min)
      python3 ccmf_spec.py --example  (worked example only)

The specification implements the decision semantics of Section 4 (evidence-gated readiness,
local feasibility, joint feasibility with the freeze rule, lexicographic objective, release gate).
It is a model of the framework's rules, NOT an implementation of a migration tool.
"""
import itertools, random, sys, json, math
from itertools import combinations, product

ALL_D = ("retire", "replace", "configure", "rebuild", "externalize", "defer")
NEEDS_APPROVAL = {"retire", "defer"}          # need approval records instead of owner+mechanism
STATUSES = ("observed", "inferred", "approved", "contradicted", "unresolved")

class Cap:
    __slots__ = ("name", "ready", "ctrl", "supported", "approved", "cost", "cov", "mods")
    def __init__(self, name, ready, ctrl, supported, approved, cost, cov, mods):
        self.name, self.ready = name, ready
        self.ctrl = ctrl            # d -> 'pass' | 'fail' | 'unevaluable'  (aggregate over mandatory controls)
        self.supported = supported  # d -> bool : accountable owner + supported target mechanism
        self.approved = approved    # d -> bool : approval records for retire/defer
        self.cost = cost            # d -> number (normalised declared estimate, scalarised)
        self.cov = cov              # d -> weighted requirement coverage in [0,1]
        self.mods = mods            # d -> set of shared-dependency ids the disposition modifies/removes

class Inst:
    def __init__(self, caps, shared, D=ALL_D):
        self.caps, self.shared, self.D = caps, shared, tuple(D)   # shared: s -> (users tuple, allowed set of (d_i,d_j) for i<j)

def ready_from_statuses(spec_complete, statuses):
    """Definition 4 (evidence part): specified and no material assertion unresolved/contradicted."""
    return bool(spec_complete) and not any(s in ("unresolved", "contradicted") for s in statuses)

def loc(c, d):
    """Local feasibility Loc_i(d): ready, mandatory controls pass, accountable support / approvals present."""
    if not c.ready or c.ctrl[d] != "pass":
        return False
    return c.approved[d] if d in NEEDS_APPROVAL else c.supported[d]

def feasible(inst, x):
    """Joint feasibility, written directly from Definition 6 (used as the oracle's predicate)."""
    for c, xi in zip(inst.caps, x):
        if xi is not None and not loc(c, xi):
            return False
    for s, (users, allowed) in inst.shared.items():
        for a, b in combinations(users, 2):
            if x[a] is not None and x[b] is not None and (x[a], x[b]) not in allowed:
                return False
        for i in users:                                   # freeze rule
            if x[i] is not None and s in inst.caps[i].mods[x[i]]:
                if any(x[j] is None for j in users if j != i):
                    return False
    return True

def objective(inst, x):
    resolved = sum(v is not None for v in x)
    cost = sum(inst.caps[i].cost[v] for i, v in enumerate(x) if v is not None)
    return (-resolved, cost)                              # lexicographic minimisation

def oracle(inst):
    """Brute-force optimum straight from the definitions."""
    best, bx = None, None
    for x in product((None,) + inst.D, repeat=len(inst.caps)):
        if feasible(inst, x):
            k = objective(inst, x)
            if best is None or k < best:
                best, bx = k, x
    return best, bx

def feasible_set(inst):
    return {x for x in product((None,) + inst.D, repeat=len(inst.caps)) if feasible(inst, x)}

def solve(inst):
    """Algorithm 1: local filtering + depth-first search with incremental pairwise checks; freeze checked at leaves."""
    n = len(inst.caps)
    dom = [[None] + [d for d in inst.D if loc(c, d)] for c in inst.caps]
    pair = {}
    for s, (users, allowed) in inst.shared.items():
        for a, b in combinations(users, 2):
            pair.setdefault((a, b), []).append(allowed)
    best = [None, None]
    def freeze_ok(x):
        for s, (users, _) in inst.shared.items():
            unresolved = [j for j in users if x[j] is None]
            for i in users:
                if x[i] is not None and s in inst.caps[i].mods[x[i]]:
                    if any(j != i for j in unresolved):
                        return False
        return True
    def rec(i, x, cost):
        if i == n:
            if freeze_ok(x):
                k = (-sum(v is not None for v in x), cost)
                if best[0] is None or k < best[0]:
                    best[0], best[1] = k, tuple(x)
            return
        for d in dom[i]:
            ok = True
            if d is not None:
                for j in range(i):
                    if x[j] is not None and (j, i) in pair:
                        if any((x[j], d) not in al for al in pair[(j, i)]):
                            ok = False; break
            if ok:
                rec(i + 1, x + [d], cost + (inst.caps[i].cost[d] if d is not None else 0))
    rec(0, [], 0)
    return best[0], best[1]

# --------------------------------------------------------------------------- release gate
def release_gate(checks, traceability_complete, readiness_established, authorization):
    """Eq. (12). checks: list of 'pass'|'fail'|'skipped'|'not_evaluable' for applicable mandatory checks.
    authorization: 'human_accountable' | 'model' | 'majority_vote' | 'none'."""
    all_pass = all(c == "pass" for c in checks)            # skipped / not_evaluable are not passes
    return bool(all_pass and traceability_complete and readiness_established and authorization == "human_accountable")

# --------------------------------------------------------------------------- random generation
def gen_cap(rng, name, D, shared_ids):
    n_ass = 3
    statuses = rng.choices(STATUSES, weights=(4, 3, 4, 1, 2), k=n_ass)
    ready = ready_from_statuses(rng.random() < 0.9, statuses)
    ctrl = {d: rng.choices(("pass", "fail", "unevaluable"), weights=(6, 3, 1))[0] for d in D}
    supported = {d: rng.random() < 0.6 for d in D}
    approved = {d: rng.random() < 0.5 for d in D}
    cost = {d: rng.randint(1, 9) for d in D}
    cov = {d: round(rng.random(), 2) for d in D}
    mods = {d: {s for s in shared_ids if rng.random() < 0.3} for d in D}
    return Cap(name, ready, ctrl, supported, approved, cost, cov, mods)

def gen_inst(rng, n, D=ALL_D):
    nshared = rng.randint(1, 2)
    shared_ids = [f"s{k}" for k in range(nshared)]
    caps = [gen_cap(rng, f"c{i}", D, shared_ids) for i in range(n)]
    shared = {}
    for s in shared_ids:
        users = tuple(sorted(rng.sample(range(n), rng.randint(2, n))))
        allowed = {(a, b) for a in D for b in D if rng.random() < 0.7}
        shared[s] = (users, allowed)
    return Inst(caps, shared, D)

def perturb_cost_cov(rng, inst):
    caps = []
    for c in inst.caps:
        caps.append(Cap(c.name, c.ready, c.ctrl, c.supported, c.approved,
                        {d: rng.randint(1, 9) for d in inst.D}, {d: round(rng.random(), 2) for d in inst.D}, c.mods))
    return Inst(caps, inst.shared, inst.D)

def refine_ready(inst, i):
    caps = [c for c in inst.caps]
    c = caps[i]
    caps[i] = Cap(c.name, True, c.ctrl, c.supported, c.approved, c.cost, c.cov, c.mods)
    return Inst(caps, inst.shared, inst.D)

def baseline_threshold_planner(inst, threshold=0.75):
    """Comparator: per capability, cheapest disposition with coverage >= threshold; ignores readiness,
    mandatory controls and shared dependencies (the 'coverage is enough' practice the framework rejects)."""
    x = []
    for c in inst.caps:
        cand = [d for d in inst.D if c.cov[d] >= threshold]
        x.append(min(cand, key=lambda d: c.cost[d]) if cand else None)
    return tuple(x)

# --------------------------------------------------------------------------- property checks
def check_instance(inst, rng, stats):
    best_o, x_o = oracle(inst)
    best_s, x_s = solve(inst)
    stats["instances"] += 1
    if best_o != best_s or (x_s is not None and not feasible(inst, x_s)):
        stats["solver_oracle_mismatch"] += 1
    x = x_o
    # S1 readiness / S2 mandatory controls on the optimal plan
    for c, xi in zip(inst.caps, x):
        if not c.ready and xi is not None: stats["S1_violations"] += 1
        if xi is not None and c.ctrl[xi] != "pass": stats["S2_violations"] += 1
    # T1 minimal abstention: any capability left unresolved although ready -> no feasible plan resolves more
    # (the objective is lexicographic, so best_o[0] is the maximum resolved count by construction of oracle)
    fs = feasible_set(inst)
    maxres = max(sum(v is not None for v in y) for y in fs)
    if -best_o[0] != maxres: stats["minimal_abstention_violations"] += 1
    # T2 cost/coverage invariance of feasibility
    if feasible_set(perturb_cost_cov(rng, inst)) != fs: stats["invariance_violations"] += 1
    # T3 evidence monotonicity: refining a non-ready capability to ready cannot reduce decision coverage
    for i, c in enumerate(inst.caps):
        if not c.ready:
            b2, _ = oracle(refine_ready(inst, i))
            stats["refinement_checks"] += 1
            if -b2[0] < -best_o[0]: stats["monotonicity_violations"] += 1
    # T4 coupling gap: product of local feasible sets vs joint feasible set
    local = [[None] + [d for d in inst.D if loc(c, d)] for c in inst.caps]
    prod_all = set(product(*local))
    if not fs <= prod_all: stats["joint_not_subset_of_product"] += 1
    if len(fs) < len(prod_all): stats["strict_coupling_gap_instances"] += 1
    # coupling witness: every capability has a resolved locally feasible option, yet no jointly feasible plan resolves all
    if all(len(l) > 1 for l in local) and maxres < len(inst.caps): stats["coupling_witness_instances"] += 1
    # comparator planner
    xb = baseline_threshold_planner(inst)
    if not feasible(inst, xb):
        stats["baseline_infeasible"] += 1
        # attribute (non-exclusively) to causes
        for c, d in zip(inst.caps, xb):
            if d is not None and not c.ready: stats["baseline_cause_unready"] += 1; break
        for c, d in zip(inst.caps, xb):
            if d is not None and c.ctrl[d] != "pass": stats["baseline_cause_control"] += 1; break

def new_stats():
    keys = ["instances", "solver_oracle_mismatch", "S1_violations", "S2_violations", "minimal_abstention_violations",
            "invariance_violations", "refinement_checks", "monotonicity_violations", "joint_not_subset_of_product",
            "strict_coupling_gap_instances", "coupling_witness_instances", "baseline_infeasible",
            "baseline_cause_unready", "baseline_cause_control"]
    return {k: 0 for k in keys}

def exhaustive_small_scope():
    """n=2 capabilities, D={configure, rebuild}; every combination of the discrete attributes."""
    D = ("configure", "rebuild")
    stats = new_stats(); rng = random.Random(1)
    cost = {"configure": 2, "rebuild": 5}
    cov = {"configure": 0.8, "rebuild": 1.0}
    cap_states = []
    for ready in (False, True):
        for bits in product((0, 1), repeat=6):            # per d: ctrl_ok, supported, modifies
            (c0, s0, m0, c1, s1, m1) = bits
            cap_states.append((ready, (c0, s0, m0), (c1, s1, m1)))
    def mk(name, st):
        ready, a, b = st
        ctrl = {"configure": "pass" if a[0] else "fail", "rebuild": "pass" if b[0] else "fail"}
        sup = {"configure": bool(a[1]), "rebuild": bool(b[1])}
        mods = {"configure": {"s0"} if a[2] else set(), "rebuild": {"s0"} if b[2] else set()}
        return Cap(name, ready, ctrl, sup, {d: False for d in D}, cost, cov, mods)
    pairs = [(a, b) for a in D for b in D]
    for st0 in cap_states:
        for st1 in cap_states:
            for mask in range(16):
                allowed = {pairs[k] for k in range(4) if mask >> k & 1}
                inst = Inst([mk("c0", st0), mk("c1", st1)], {"s0": ((0, 1), allowed)}, D)
                check_instance_small(inst, stats)
    return stats

def check_instance_small(inst, stats):
    """Same properties, cost-perturbation replaced by fixed alternative cost vector (keeps runtime low)."""
    best_o, x_o = oracle(inst); best_s, x_s = solve(inst)
    stats["instances"] += 1
    if best_o != best_s or (x_s is not None and not feasible(inst, x_s)): stats["solver_oracle_mismatch"] += 1
    for c, xi in zip(inst.caps, x_o):
        if not c.ready and xi is not None: stats["S1_violations"] += 1
        if xi is not None and c.ctrl[xi] != "pass": stats["S2_violations"] += 1
    fs = feasible_set(inst)
    if -best_o[0] != max(sum(v is not None for v in y) for y in fs): stats["minimal_abstention_violations"] += 1
    alt = Inst([Cap(c.name, c.ready, c.ctrl, c.supported, c.approved, {"configure": 9, "rebuild": 1}, {"configure": 0.1, "rebuild": 0.3}, c.mods) for c in inst.caps], inst.shared, inst.D)
    if feasible_set(alt) != fs: stats["invariance_violations"] += 1
    for i, c in enumerate(inst.caps):
        if not c.ready:
            b2, _ = oracle(refine_ready(inst, i)); stats["refinement_checks"] += 1
            if -b2[0] < -best_o[0]: stats["monotonicity_violations"] += 1
    local = [[None] + [d for d in inst.D if loc(c, d)] for c in inst.caps]
    prod_all = set(product(*local))
    if not fs <= prod_all: stats["joint_not_subset_of_product"] += 1
    if len(fs) < len(prod_all): stats["strict_coupling_gap_instances"] += 1
    if all(len(l) > 1 for l in local) and max(sum(v is not None for v in y) for y in fs) < 2: stats["coupling_witness_instances"] += 1

def randomized(n, N, seed):
    rng = random.Random(seed); stats = new_stats()
    for _ in range(N):
        check_instance(gen_inst(rng, n), rng, stats)
    return stats

# --------------------------------------------------------------------------- worked example (Section 6)
REQS_C1 = [  # (id, description, weight, mandatory)
    ("r1", "Enforce approval limit", 3, True), ("r2", "Prevent self-approval", 3, True),
    ("r3", "Update workflow state", 2, False), ("r4", "Invoke posting", 2, False),
    ("r5", "Write audit record", 3, True), ("r6", "Show confirmation message", 1, False)]
COVERED_C1 = {  # disposition -> requirement ids supported by declared criterion (unknown treated as not covered)
    "replace": {"r1", "r3", "r4", "r5", "r6"},                      # native function lacks self-approval prevention
    "configure": {"r1", "r2", "r3", "r4", "r5"},                    # native limit table + native self-approval switch
    "rebuild": {"r1", "r2", "r3", "r4", "r5", "r6"},
    "externalize": {"r1", "r2", "r3", "r4", "r5", "r6"}}
def coverage(covered):
    tot = sum(w for _, _, w, _ in REQS_C1)
    return sum(w for r, _, w, _ in REQS_C1 if r in covered) / tot
def mandatory_ok(covered):
    return all(r in covered for r, _, _, m in REQS_C1 if m)

def worked_example():
    out = {}
    out["coverage"] = {d: round(coverage(c), 3) for d, c in COVERED_C1.items()}
    out["mandatory_ok"] = {d: mandatory_ok(c) for d, c in COVERED_C1.items()}
    D = ("replace", "configure", "rebuild", "externalize")
    cost1 = {"replace": 2, "configure": 3, "rebuild": 8, "externalize": 6}
    cost2 = {"replace": 2, "configure": 2, "rebuild": 6, "externalize": 7}
    def c1(ready):
        return Cap("C1 Approve outgoing payment", ready,
                   {d: ("pass" if mandatory_ok(COVERED_C1[d]) else "fail") for d in D},
                   {d: True for d in D}, {}, cost1, {d: coverage(COVERED_C1[d]) for d in D},
                   {"replace": set(), "configure": {"audit"}, "rebuild": set(), "externalize": {"audit"}})
    c2 = Cap("C2 Release held payment", True,
             {"replace": "fail", "configure": "fail", "rebuild": "pass", "externalize": "pass"},
             {"replace": False, "configure": False, "rebuild": True, "externalize": True}, {}, cost2,
             {"replace": 0.5, "configure": 0.5, "rebuild": 1.0, "externalize": 1.0},
             {d: set() for d in D})
    # consistency on shared audit-record writer: (C1 disposition, C2 disposition)
    allowed = {("rebuild", "rebuild"), ("configure", "externalize"), ("externalize", "externalize"),
               ("rebuild", "externalize"), ("replace", "rebuild"), ("replace", "externalize")}
    shared = {"audit": ((0, 1), allowed)}
    inst0 = Inst([c1(False), c2], shared, D)     # phase 0: assertion a3 unresolved -> C1 not ready
    inst1 = Inst([c1(True), c2], shared, D)      # phase 1: a3 observed and approved
    out["phase0"] = oracle(inst0)
    out["phase1"] = oracle(inst1)
    # independent per-capability planning (ignoring sharing): cheapest locally feasible
    local1 = min((d for d in D if loc(inst1.caps[0], d)), key=lambda d: cost1[d])
    local2 = min((d for d in D if loc(inst1.caps[1], d)), key=lambda d: cost2[d])
    out["independent_choice"] = (local1, local2)
    out["independent_cost"] = cost1[local1] + cost2[local2]
    out["independent_feasible"] = feasible(inst1, (local1, local2))
    # threshold-cost planner (coverage >= 0.75 and cheapest) for C1
    cand = [d for d in D if coverage(COVERED_C1[d]) >= 0.75]
    out["threshold_pick_C1"] = min(cand, key=lambda d: cost1[d])
    out["threshold_pick_feasible_locally"] = loc(inst1.caps[0], out["threshold_pick_C1"])
    out["local_feasible_C1"] = [d for d in D if loc(inst1.caps[0], d)]
    out["local_feasible_C2"] = [d for d in D if loc(inst1.caps[1], d)]
    out["joint_feasible_resolved_all"] = sorted(x for x in feasible_set(inst1) if None not in x)
    out["solver_agrees"] = solve(inst1) == oracle(inst1)
    # release gate
    out["gate_a"] = release_gate(["pass", "pass", "pass", "skipped"], True, True, "none")
    out["gate_b"] = release_gate(["pass", "pass", "pass", "pass"], True, True, "model")
    out["gate_c"] = release_gate(["pass", "pass", "pass", "pass"], True, True, "human_accountable")
    return out

def sample_size_noninferiority(p1, p2, margin, alpha=0.025, power=0.8):
    from statistics import NormalDist
    z = NormalDist().inv_cdf
    n = (z(1 - alpha) + z(power)) ** 2 * (p1 * (1 - p1) + p2 * (1 - p2)) / margin ** 2
    return math.ceil(n)

if __name__ == "__main__":
    if "--example" in sys.argv:
        print(json.dumps(worked_example(), indent=2, default=str)); sys.exit()
    res = {}
    print("Worked example ..."); res["example"] = worked_example()
    print("Exhaustive small scope ..."); res["exhaustive_n2_D2"] = exhaustive_small_scope()
    for n, N, seed in ((2, 100000, 11), (3, 40000, 12)):
        print(f"Randomized n={n}, N={N} ..."); res[f"random_n{n}"] = randomized(n, N, seed)
    res["sample_size_ni_p0.10_margin0.05"] = sample_size_noninferiority(0.10, 0.10, 0.05)
    print(json.dumps(res, indent=2, default=str))
    json.dump(res, open("verification_results.json", "w"), indent=2, default=str)
