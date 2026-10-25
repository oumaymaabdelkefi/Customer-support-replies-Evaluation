"""
Build the Excel labelling workbook for the stage-2 items (blind: shows
only message, policy excerpt and reply -- no design notes).

Writes:
  data/labelling_sheet_stage2.xlsx              blank master copy
  data/labels/labelling_stage2_labeller1.xlsx   personal copy, labeller 1
  data/labels/labelling_stage2_labeller2.xlsx   personal copy, labeller 2

Usage: python scripts/make_labelling_xlsx.py
Rows come from data/labelling_sheet_labeler1_stage2.csv (written by
scripts/merge_golden_set.py). Rules summarised from data/labelling_guide.md.
"""
import csv
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.workbook.properties import CalcProperties
from openpyxl.worksheet.datavalidation import DataValidation

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"

rows = list(csv.DictReader(open(DATA / "labelling_sheet_labeler1_stage2.csv", encoding="utf-8-sig")))
pilot = {json.loads(l)["item_id"]: json.loads(l) for l in open(DATA / "pilot_items.jsonl", encoding="utf-8") if l.strip()}
ex = pilot["P20"]

FONT = "Arial"
f = lambda **kw: Font(name=FONT, **kw)
YELLOW = PatternFill("solid", start_color="FFF2CC")
HEADER = PatternFill("solid", start_color="1F3864")
GREY = PatternFill("solid", start_color="F2F2F2")
GREEN = PatternFill("solid", start_color="E2EFDA")
thin = Side(style="thin", color="BFBFBF")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)
WRAP = Alignment(wrap_text=True, vertical="top")


def build(labeller):
    wb = Workbook()

    # ---------------- Instructions ----------------
    ins = wb.active
    ins.title = "Scoring rules"
    ins.column_dimensions["A"].width = 24
    ins.column_dimensions["B"].width = 95
    ins.sheet_view.showGridLines = False

    r = 1

    def put(a, b="", bold=False, size=10, fill=None, height=None):
        nonlocal r
        ins.cell(r, 1, a).font = f(bold=True, size=size)
        c = ins.cell(r, 2, b)
        c.font = f(bold=bold, size=size)
        c.alignment = WRAP
        ins.cell(r, 1).alignment = WRAP
        if fill:
            ins.cell(r, 1).fill = fill
            c.fill = fill
        if height:
            ins.row_dimensions[r].height = height
        r += 1

    ins.cell(r, 1, "SupportScore labelling sheet: 102 items (G29-G130)").font = f(bold=True, size=14)
    r += 2
    who = {1: "Labeller 1", 2: "Labeller 2"}.get(labeller, "Labeller ? (write 1 or 2)")
    put("This copy is for", who, bold=True, fill=YELLOW if labeller is None else GREEN)
    put("Your name", None)
    ins.cell(r - 1, 2).fill = YELLOW
    ins.cell(r - 1, 2).border = BOX
    r += 1
    put("What to do", "Go to the 'Labels' tab. For each row, read the customer message, the policy excerpt and the reply, then give the reply a score of 0, 1 or 2 on each of the three axes, plus a short note.", height=30)
    put("Cells to fill in", "Only the yellow cells in the 'Labels' tab: Correctness, Politeness, Completeness (choose 0, 1, 2 or NA from the dropdown) and Notes (free text). Do not edit any other column.", height=30)
    put("Work alone", "Do not discuss items or look at anyone else's sheet until you have finished. We measure how often two labellers agree, so independent labels are what matter.", height=30)
    put("Source of truth", "The policy excerpt in each row is the ONLY source of truth for correctness. If it says no rule covers the request, the right reply says so and offers to escalate.", height=30)
    put("Progress", None)
    ins.cell(r - 1, 2).value = '=COUNTA(Labels!F2:F103)&" of 102 items scored for correctness"'
    ins.cell(r - 1, 2).font = f(bold=True, color="1F3864")
    r += 1

    ins.cell(r, 1, "Scoring rules (summary of data/labelling_guide.md)").font = f(bold=True, size=12)
    r += 1
    put("Score each axis independently", "A rude but correct reply still gets 2 for correctness. A warm but wrong reply still gets 0 for correctness.", height=28)
    put("Correctness 2", "Everything the reply says about policy, timeframes, cost or process matches the excerpt. Also 2: asking for missing info (e.g. 'has it shipped?') instead of guessing, or naming a policy gap and offering to escalate.", height=42, fill=GREY)
    put("Correctness 1", "Right core outcome but a minor inaccuracy, an unsupported soft promise ('we'll try to expedite'), right answer for the wrong reason, extra detail the policy neither confirms nor contradicts, or promising to 'check and get back to you' (support has no live order access, GEN-1).", height=55, fill=GREY)
    put("Correctness 0", "Contradicts the policy, invents a rule / order status / discount / date, or gives a confident answer where the policy has a gap.", height=30, fill=GREY)
    put("Politeness 2", "Respectful and empathetic; acknowledges the customer's situation. Very warm or effusive replies still get 2 unless they read as mocking.", height=30)
    put("Politeness 1", "Neutral or curt, reads like a terse note, skips an expected apology, but nothing rude.", height=28)
    put("Politeness 0", "Blame, sarcasm, condescension or dismissiveness, even if the content is right.", height=28)
    put("Completeness 2", "Covers everything the customer needs to act: every relevant condition (timeframe, evidence/steps, who pays, what happens next). If info is missing, clearly asking for it counts as complete.", height=42, fill=GREY)
    put("Completeness 1", "Covers the main point but misses a detail (e.g. confirms a refund but not the timeframe, forgets the required photos).", height=30, fill=GREY)
    put("Completeness 0", "Doesn't answer the actual question, or is so short/generic there's no next step.", height=28, fill=GREY)
    put("OMISSION RULE (v0.3)", "If a reply LEAVES OUT a rule that applies but doesn't say anything wrong, lower COMPLETENESS only, not correctness. Lower correctness only when you can point to a sentence that is untrue under the policy, an invented rule/date/discount, or a promise support can't keep (e.g. 'I'll check and get back to you'). Example: 'you can change your address anytime' is a wrong statement (correctness drops); simply not mentioning the 'Processing' condition is an omission (completeness drops).", bold=True, fill=PatternFill("solid", start_color="FCE4D6"), height=80)
    put("Items you wrote", "If you wrote an item yourself, choose NA for all three and write 'I wrote this item' in Notes.", height=28)
    put("NA", "Only if an item genuinely can't be judged: choose NA for all three and explain in Notes.", height=28)
    put("Notes", "One line naming the issue that drove any score below 2 (cite the rule, e.g. 'Contradicts SHIP-3'). This lets us discuss disagreements later.", height=30)
    r += 1

    ins.cell(r, 1, "Worked example (already-labelled pilot item P20, not part of your 102)").font = f(bold=True, size=12)
    r += 1
    put("Customer message", ex["customer_message"], height=30)
    put("Policy excerpt", ex["policy_excerpt"], height=45)
    put("Reply", ex["candidate_reply"], height=45)
    put("Scores", "Correctness 2  ·  Politeness 0  ·  Completeness 1", bold=True, fill=GREEN)
    put("Note", "14-day grace period stated correctly; 'Fine, deleting it... I guess' is dismissive; doesn't say how to cancel (log back in).", fill=GREEN, height=30)

    # ---------------- Labels ----------------
    ws = wb.create_sheet("Labels")
    headers = ["Item", "Theme", "Customer message", "Policy excerpt", "Reply to grade",
               "Correctness", "Politeness", "Completeness", "Notes"]
    widths = [7, 12, 30, 42, 46, 12, 11, 13, 36]
    for col, (h, w) in enumerate(zip(headers, widths), start=1):
        c = ws.cell(1, col, h)
        c.font = f(bold=True, color="FFFFFF")
        c.fill = HEADER
        c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        c.border = BOX
        ws.column_dimensions[c.column_letter].width = w
    ws.row_dimensions[1].height = 30
    ws.cell(1, 6).comment = Comment("0 = contradicts policy, 1 = partly consistent, 2 = fully consistent. See Instructions.", "SupportScore")
    ws.cell(1, 7).comment = Comment("0 = disrespectful, 1 = curt/neutral, 2 = respectful & empathetic.", "SupportScore")
    ws.cell(1, 8).comment = Comment("0 = no actionable answer, 1 = misses a detail, 2 = covers what's needed to act.", "SupportScore")

    for i, row in enumerate(rows, start=2):
        values = [row["item_id"], row["theme"].replace("_", " "), row["customer_message"],
                  row["policy_excerpt"], row["candidate_reply"], None, None, None, None]
        longest = max(len(row["policy_excerpt"]) / 48, len(row["candidate_reply"]) / 52, len(row["customer_message"]) / 34)
        ws.row_dimensions[i].height = max(45, min(300, 13 * (int(longest) + 2)))
        for col, v in enumerate(values, start=1):
            c = ws.cell(i, col, v)
            c.font = f(size=10, bold=(col == 1))
            c.alignment = WRAP if col not in (6, 7, 8) else Alignment(horizontal="center", vertical="top")
            c.border = BOX
            if col >= 6:
                c.fill = YELLOW
    last = len(rows) + 1

    dv = DataValidation(type="list", formula1='"0,1,2,NA"', allow_blank=True,
                        showErrorMessage=True, errorTitle="Invalid score",
                        error="Choose 0, 1, 2 or NA.", promptTitle="Score",
                        prompt="0, 1, 2 (or NA)", showInputMessage=True)
    dv.add(f"F2:H{last}")
    ws.add_data_validation(dv)
    # Turn a fully scored row green so progress is visible at a glance.
    done = FormulaRule(formula=[f'COUNTA($F2:$H2)=3'], fill=PatternFill("solid", start_color="E2EFDA"))
    ws.conditional_formatting.add(f"F2:H{last}", done)
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:I{last}"

    # Open straight onto the items to label; the rules tab is reference only.
    wb.move_sheet("Labels", offset=-1)
    wb.active = 0
    ins.sheet_view.tabSelected = False
    ws.sheet_view.tabSelected = True
    wb.calculation = CalcProperties(fullCalcOnLoad=True)
    return wb


def main():
    (DATA / "labels").mkdir(exist_ok=True)
    targets = {
        1: DATA / "labels" / "labelling_stage2_labeller1.xlsx",
        2: DATA / "labels" / "labelling_stage2_labeller2.xlsx",
        None: DATA / "labelling_sheet_stage2.xlsx",
    }
    for labeller, path in targets.items():
        if labeller is not None and path.exists():
            print(f"kept {path.relative_to(REPO_ROOT)} (already exists -- may contain labels)")
            continue
        try:
            build(labeller).save(path)
        except PermissionError:
            print(f"SKIPPED {path.relative_to(REPO_ROOT)}: it is open in Excel -- close it and re-run")
            continue
        print(f"wrote {path.relative_to(REPO_ROOT)} ({len(rows)} items)")


if __name__ == "__main__":
    main()
