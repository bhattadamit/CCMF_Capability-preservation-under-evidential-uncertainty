"""Compare package outputs with the values printed in the manuscript (Manuscript 6, JAIS format).
Run from the code/ folder after `python3 ccmf_spec.py` (or use the shipped results/ files)."""
import csv, json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
res = os.path.join(here, "..", "results")
dat = os.path.join(here, "..", "data")
ver = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(res, "verification_results.json")))
# Values transcribed from the manuscript.
T8 = {  # field: (exhaustive n=2, random n=2, random n=3)
 "instances": (262144, 100000, 40000), "solver_oracle_mismatch": (0, 0, 0), "S1_violations": (0, 0, 0),
 "S2_violations": (0, 0, 0), "invariance_violations": (0, 0, 0), "minimal_abstention_violations": (0, 0, 0),
 "refinement_checks": (262144, 112913, 67865), "monotonicity_violations": (0, 0, 0),
 "joint_not_subset_of_product": (0, 0, 0), "strict_coupling_gap_instances": (59295, 45426, 21814),
 "coupling_witness_instances": (5392, 1360, 426)}
T11 = {(0.05, 0.03): 829, (0.10, 0.05): 566, (0.10, 0.03): 1570, (0.15, 0.05): 801, (0.20, 0.05): 1005}
bad = 0
def chk(name, got, want):
    global bad
    ok = got == want; bad += (not ok)
    print(("OK   " if ok else "FAIL ") + f"{name}: got {got}, manuscript {want}")
for k, want in T8.items():
    got = tuple(ver[r][k] for r in ("exhaustive_n2_D2", "random_n2", "random_n3"))
    chk(f"Table 8 {k}", got, want)
for r in csv.DictReader(open(os.path.join(dat, "table_sample_size_noninferiority.csv"))):
    chk(f"Table 11 p={r['p_control']} margin={r['margin']}", int(r["n_per_arm"]), T11[(float(r["p_control"]), float(r["margin"]))])
we = open(os.path.join(res, "worked_example_output.txt")).read()
w = json.loads(we[we.index("{"):])
chk("Worked example phase 0 optimum", w["phase0"], [[-1, 6], [None, "rebuild"]])
chk("Worked example phase 1 optimum", w["phase1"], [[-2, 10], ["configure", "externalize"]])
chk("Independent cheapest choice / cost", (w["independent_choice"], w["independent_cost"]), (["configure", "rebuild"], 9))
chk("Independent choice jointly feasible", w["independent_feasible"], False)
chk("Threshold planner picks replace (fails mandatory)", (w["threshold_pick_C1"], w["threshold_pick_feasible_locally"]), ("replace", False))
chk("Release gate cases a/b/c", (w["gate_a"], w["gate_b"], w["gate_c"]), (False, False, True))
print("ALL MATCH" if not bad else f"{bad} MISMATCH(ES)")
sys.exit(1 if bad else 0)
