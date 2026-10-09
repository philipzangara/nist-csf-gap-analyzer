# NIST CSF 2.0 Control Gap Analyzer

A Python tool that compares a self assessment against the real NIST Cybersecurity Framework (CSF) 2.0 and generates a gap report. It shows coverage by Function, Category, and Subcategory, and flags what's not fully implemented yet.

This is an Applied Series project. I drove the architecture and every design decision. The implementation was AI assisted and reviewed by me before I called any piece done.

## Project Metrics

• 106 CSF 2.0 Subcategories Assessed
• 22 CSF Categories Evaluated
• 6 CSF Functions Analyzed
• Markdown Report Generation
• Interactive HTML Heatmap Visualization
• Assessment Validation Against NIST Reference Data

## Why I built this

Most portfolio projects that touch a framework like CSF just print out the category list and call it a demo. I wanted something that actually does the comparison work a real assessment would need: load the real framework data, validate a user's input against it, compute honest coverage numbers, and produce a report someone could actually hand to a stakeholder.

## What it does

You give it a YAML file with your self assessed status for however many CSF subcategories you've evaluated. It tells you:

- Overall coverage percentage across all 106 real CSF 2.0 subcategories
- Coverage broken down by Function (GOVERN, IDENTIFY, PROTECT, DETECT, RESPOND, RECOVER) and by Category within each Function
- A "quick wins" list: subcategories marked partial, since those are usually the fastest path to closing a gap
- A full gap list, grouped by Function and Category, with the real subcategory description so you don't need the CSF spec open in another tab
- An interactive coverage heatmap, styled after MITRE ATT&CK Navigator, with every cell linking out to its real csf.tools reference page

## How coverage is scored

This was the core design decision in the project, so I want to be upfront about it instead of burying it in the code.

- A subcategory counts toward coverage only if it's marked `implemented`. `partial` gets tracked as its own separate count, not blended into the percentage. I didn't want a tool that could show 80% coverage when half of that was really "kind of started."
- A subcategory that's missing from the assessment file entirely (never assessed) is treated the same as `not_implemented`. If you haven't assessed it, you can't claim credit for it.
- Category coverage is the average of its subcategories' scores. Function coverage is computed the same way across all subcategories in that Function directly, not by averaging its Categories' percentages. That matters because Categories don't all have the same number of subcategories. GV.PO has 2, GV.SC has 10. Averaging percentages would let a tiny Category with one thing done count as much as a big Category that's mostly a gap.

## Where the framework data comes from

`data/csf_2_0_reference.yaml` is generated from NIST's actual CPRT export, not hand typed or recalled from memory. The conversion script (`convert_csf_reference.py`) documents exactly how I pulled the real 6 Functions, 22 Categories, and 106 Subcategories out of the raw export and filtered out the withdrawn CSF 1.1 elements that get bundled into that same file. Those counts match NIST's published totals, which I checked rather than assumed.

The sample assessment in `assessments/example_assessment.yaml` is synthetic. I built it specifically to exercise the gap engine: a couple of Categories at 100%, a couple with a deliberate mix of implemented/partial/not_implemented, and a Category left out entirely to prove the missing-defaults-to-not-implemented rule actually works. It's not based on a real business or a real assessment.

## The heatmap

Each Function is a column. Each Subcategory is a row stacked underneath. Cells are colored red, yellow, or green by status. Columns are allowed to be different heights, since GOVERN has 31 subcategories and RECOVER has 8. Forcing equal height would misrepresent how much work is actually in each Function.

Every cell links out to that subcategory's real page on csf.tools, so a reader can click straight through to the actual control language instead of taking my report's word for it.

## Project structure

```
nist-csf-gap-analyzer/
├── data/
│   └── csf_2_0_reference.yaml    # Real CSF 2.0 data, generated from NIST's CPRT export
├── assessments/
│   └── example_assessment.yaml   # Synthetic test fixture assessment
├── src/
│   ├── csf_loader.py             # Loads and looks up the CSF reference
│   ├── assessment.py             # Loads and validates an assessment file
│   ├── gap_engine.py             # Coverage and gap calculation logic
│   ├── report_generator.py       # Renders results into a Markdown report and an HTML heatmap
│   └── cli.py                    # Command line entry point
├── tests/
│   └── test_gap_engine.py        # Unit tests against a small, hand verified fixture
├── reports/                       # Generated reports land here (gitignored)
├── convert_csf_reference.py      # One off script: raw NIST JSON -> project's YAML schema
├── pytest.ini
├── requirements.txt
└── README.md
```

## Running it

```
pip install -r requirements.txt
python -m src.cli --assessment assessments/example_assessment.yaml --output reports/gap_report.md --heatmap reports/heatmap.html
```

This prints a summary to the terminal, writes the full report to `reports/gap_report.md`, and writes the heatmap to `reports/heatmap.html`. The `--heatmap` flag is optional. Leave it off if you only want the Markdown report.

To run the tests:

```
pytest tests/test_gap_engine.py -v
```

## What I'd add next

- Priority or severity weighting per subcategory, so a gap in something high risk stands out more than a gap in something low priority
- Owner and target remediation date fields in the assessment schema, closer to what a real GRC tool would track
