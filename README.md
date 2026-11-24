# Replication package: Capability-Contract Migration Framework (CCMF)

Companion to the manuscript "Capability Preservation Under Evidential Uncertainty: A Design Theory and Governance Framework for Evidence-Aware Enterprise Modernization" (Manuscript 6, JAIS format, Nov 2026).
Authors: Amit Bhattad, Aditya Mantri, Durga Bhattad. Repository location and persistent identifier: [github.com_CCMF_Capability-preservation-under-evidential-uncertainty], as in the manuscript's data and code availability statement; insert the final URL or DOI on deposit.

## What this package is, and is not
- It reproduces every derived number in the manuscript: the model-level verification counts (Table 8), the worked example (Section 7.3, Tables 9 and 10), and the noninferiority sample sizes (Table 11 and its sensitivity cases).
- These are model-level results. They check the internal consistency of the formal model against a brute-force oracle. They are not empirical evidence about real migrations. No real case data are included because none has been collected (manuscript Section 8.7 and Appendix E).
- It does not contain the "Conversion Weekends" study. That is a separate paper whose data and results were not available. See `CONVERSION_WEEKENDS_NOTE.md`.

## Contents
- `code/ccmf_spec.py`: reference executable specification (manuscript Supplementary File S1); standard library only.
- `code/check_against_manuscript.py`: compares the shipped (or freshly generated) results with the values printed in the manuscript; prints OK or FAIL per number.
- `results/verification_results.json`: output of the full run (Supplementary File S2).
- `results/worked_example_output.txt`: output of `--example` (Section 7.3).
- `data/table8_manuscript_layout.csv`: the counts of Table 8 with the manuscript's row labels and the matching JSON field names.
- `data/table_model_level_verification.csv`: the same counts in raw form, plus baseline diagnostics not reported in the manuscript.
- `data/table10_worked_example_inputs.csv`: coverage, mandatory-control outcome, cost and local feasibility behind Table 10 (Table 9's requirement list is in `ccmf_spec.py`).
- `data/table_sample_size_noninferiority.csv`: sample sizes behind Table 11 (one-sided alpha 0.025, power 0.80).
- `logs/run_stdout.txt`: console output of the full run.
- `CHECKSUMS.sha256`: SHA-256 of every file.

## Crosswalk: manuscript item to package file
| Manuscript | Package |
|---|---|
| Section 7.1, Supplementary File S1 | `code/ccmf_spec.py` |
| Section 7.2, Table 8, Supplementary File S2 | `results/verification_results.json`, `data/table8_manuscript_layout.csv` |
| Section 7.3, Tables 9 and 10 | `results/worked_example_output.txt`, `data/table10_worked_example_inputs.csv` |
| Section 8.3, Table 11 | `data/table_sample_size_noninferiority.csv` |
| Section 7.4 (availability) | this README |

## Reproduce
```
cd code
python3 ccmf_spec.py            # about 1 minute; writes verification_results.json to the current directory
python3 ccmf_spec.py --example  # worked example of Section 7.3
python3 check_against_manuscript.py verification_results.json
```
Seeds are fixed (random n=2: seed 11, N=100,000; random n=3: seed 12, N=40,000). A rerun in the build environment produced a file byte-identical to `results/verification_results.json`, and `check_against_manuscript.py` reports ALL MATCH for Manuscript 6.

## Licence and citation
Licence: [choose before deposit, for example MIT for code and CC BY 4.0 for data]. Cite the manuscript and the repository identifier once assigned.
