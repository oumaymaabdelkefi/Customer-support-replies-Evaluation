#!/usr/bin/env python3
"""Generate the Role A pilot dataset (15-20 item pilot, NOT the final 150+ golden set).

Writes into <repo>/data/:
  - pilot_items.jsonl
  - pilot_items.csv
  - labelling_sheet_labeler1.csv
  - labelling_sheet_labeler2.csv

Run once; re-run to regenerate deterministically from the ITEMS list below.
"""
import csv
import json
import os

REPO_DATA = "/home/azizbzt/Desktop/ai-projects/grader/data"

# Policy rule text, copied verbatim from data/policy_technest.md so excerpts
# quoted in pilot_items.jsonl always match the policy file exactly.
RULES = {
    "RET-1": "Items may be returned within 30 calendar days of delivery for a full refund of the item price, provided the item is unused, in its original packaging, and includes all accessories and manuals.",
    "RET-2": "TechNest pays return shipping only when the return is due to a defective or damaged item (see Damaged Products). For a return that is not due to a defect (e.g., changed mind, wrong size), the customer pays return shipping, unless the original order total was $100 or more, in which case TechNest provides a free prepaid return label.",
    "RET-3": "Opened software licenses, digital gift cards, and items marked \"final sale\" at checkout cannot be returned.",
    "RET-4": "Once TechNest receives and inspects a returned item, the refund is issued to the original payment method within 5-7 business days.",
    "RET-5": "An order can be cancelled at no charge at any time before it ships. Once an order's status is \"Shipped,\" it can no longer be cancelled; the customer must wait for delivery and then request a standard return instead.",
    "DMG-1": "Damage or defects present on arrival must be reported within 7 calendar days of delivery, with photos of the item and its packaging attached to the support request.",
    "DMG-2": "Once a damage report is verified, TechNest ships a free replacement immediately, without requiring the damaged unit to be returned first, and includes a prepaid return label for the damaged unit.",
    "DMG-3": "If the same model is out of stock for a replacement, the customer may choose between a full refund or a substitute item of equivalent value.",
    "DMG-4": "Damage caused by the customer after delivery (drops, spills, misuse, etc.) is not covered by this policy. The customer should be directed to the manufacturer's warranty, if any, instead of being offered a free TechNest replacement.",
    "DMG-5": "A damage report made more than 7 days after delivery is not eligible under this section, though the item may still qualify for a standard return under RET-1 if within 30 days and otherwise unused (which will rarely apply to a damaged item, since \"unused, original condition\" is required).",
    "DMG-6": "Support cannot promise an exact replacement delivery date; standard replacement shipping takes 3-5 business days after verification.",
    "SHIP-1": "Standard shipping (3-7 business days) is free on orders of $50 or more; otherwise a flat $6.99 fee applies. Express shipping (1-2 business days) costs $14.99 regardless of order size.",
    "SHIP-2": "TechNest currently ships only to the countries listed at checkout. Support may confirm whether a specific country is supported, but must not promise shipping to a country not listed at checkout.",
    "SHIP-3": "A shipping address can be changed by the customer or by support only while the order status is \"Processing.\" Once the status is \"Shipped,\" neither TechNest nor the customer can change the delivery address; the customer must contact the carrier directly.",
    "SHIP-4": "Support does not have live parcel-location data and cannot guarantee an exact delivery date. Customers should use the tracking link emailed at the time of shipment.",
    "SHIP-5": "If tracking shows no movement for 10 or more business days, the package is considered lost in transit and is eligible for a free reshipment or a full refund once TechNest confirms the loss with the carrier.",
    "SEC-1": "Password resets are self-service only, through the \"Forgot password\" link, which emails a reset link valid for 60 minutes to the email on file. Support cannot reset a password directly, and can never see, read, or share a customer's password.",
    "SEC-2": "If a customer reports signs of unauthorized access (an unrecognized order, a login alert from an unfamiliar location, a stolen password or PIN), support must immediately lock the account, force a password reset, and review recent orders for fraud, and should recommend the customer enable two-factor authentication (2FA) once back in.",
    "SEC-3": "Support never asks a customer for their full password, full card number, or a 2FA code. Any message that asks for these is not really from TechNest and should be reported.",
    "SEC-4": "Account deletion is not immediate: the account enters a 14-day grace period during which the customer can cancel the deletion by logging back in. After 14 days, deletion is permanent.",
    "SEC-5": "Changing the email address on file requires the customer to click a confirmation link sent to the new email address before the change takes effect, to prevent account takeover.",
}

BITEXT_SOURCE = "bitext/Bitext-customer-support-llm-chatbot-training-dataset"

def excerpt(*rule_ids):
    return " ".join(f"[{rid}] {RULES[rid]}" for rid in rule_ids)

ITEMS = [
    # --- Returns (SC01-SC04) ---
    dict(item_id="P01", scenario_id="SC01", theme="returns",
         customer_message="can you help me see how long refunds take?",
         policy_rule_ids=["RET-4"], policy_excerpt=excerpt("RET-4"),
         candidate_reply="Thanks for reaching out! Once we receive and inspect your returned item, we'll issue your refund to the original payment method within 5-7 business days. If you haven't shipped the return yet, let us know if you'd like the return label resent.",
         source="bitext", source_id=6000, adapted=False, original_instruction=None,
         challenge_type="correct",
         author_note="Baseline correct answer for the refund-timing scenario; pairs with P02's wrong-timeframe answer."),
    dict(item_id="P02", scenario_id="SC01", theme="returns",
         customer_message="can you help me see how long refunds take?",
         policy_rule_ids=["RET-4"], policy_excerpt=excerpt("RET-4"),
         candidate_reply="Refunds are processed instantly as soon as you request them, so you should see the money back in your account the same day.",
         source="bitext", source_id=6000, adapted=False, original_instruction=None,
         challenge_type="incorrect",
         author_note="Directly contradicts RET-4's 5-7 business day window; should score 0 on correctness even though tone is friendly."),
    dict(item_id="P03", scenario_id="SC02", theme="returns",
         customer_message="in what cases can I ask foir a refund?",
         policy_rule_ids=["RET-1", "RET-3"], policy_excerpt=excerpt("RET-1", "RET-3"),
         candidate_reply="You can request a refund if you return the item within 30 days of delivery.",
         source="bitext", source_id=6009, adapted=False, original_instruction=None,
         challenge_type="incomplete",
         author_note="Omits the unused/original-packaging/accessories condition and the RET-3 exclusions (software, gift cards, final sale)."),
    dict(item_id="P04", scenario_id="SC03", theme="returns",
         customer_message="can you help me cancel order 84213?",
         policy_rule_ids=["RET-5"], policy_excerpt=excerpt("RET-5"),
         candidate_reply="I can help with that! Could you let me know whether order 84213 has shipped yet? If it's still 'Processing,' I can cancel it right away at no charge. If it has already shipped, we won't be able to cancel it, but you're welcome to return it once it arrives.",
         source="bitext", source_id=5, adapted=True,
         original_instruction="can you help me cancel order {{Order Number}}?",
         challenge_type="asks_for_missing_info",
         author_note="Correct behavior: RET-5's outcome depends on shipment status the policy alone can't resolve, so the reply should ask rather than guess. Tests that labellers reward this instead of marking it incomplete."),
    dict(item_id="P05", scenario_id="SC04", theme="returns",
         customer_message="I bought a blender two weeks ago but I just don't like the color anymore. It's still in the box, unopened. Can I get my money back?",
         policy_rule_ids=["RET-1", "RET-2"], policy_excerpt=excerpt("RET-1", "RET-2"),
         candidate_reply="Of course! Since it's within 30 days of delivery and still unused in its original packaging, you're eligible for a full refund of the item price. Since this isn't a defect, you'll be responsible for the return shipping cost unless your original order was $100 or more, in which case we'll send a free prepaid label. Let us know and we'll get the return started!",
         source="team_written", source_id=None, adapted=False, original_instruction=None,
         challenge_type="correct",
         author_note="Team-written: Bitext's refund/order intents are templated and don't include a concrete 'changed my mind' product scenario, so this scenario was authored to test RET-1/RET-2 together."),

    # --- Damaged products (SC05-SC08) ---
    dict(item_id="P06", scenario_id="SC05", theme="damaged_products",
         customer_message="I want to file a complaint - the wireless earbuds I ordered arrived with a cracked case and the charging light doesn't turn on.",
         policy_rule_ids=["DMG-1", "DMG-2"], policy_excerpt=excerpt("DMG-1", "DMG-2"),
         candidate_reply="I'm sorry to hear that! Please send us some photos of the damage and we'll take a look.",
         source="bitext", source_id=7002, adapted=True,
         original_instruction="I want to file a consumer complaint",
         challenge_type="incomplete",
         author_note="Base instruction ('I want to file a consumer complaint') is generic in Bitext; the earbuds/cracked-case detail was added by the team since the dataset has no product-damage specifics. Reply omits the 7-day window, the free-replacement-before-return promise, and the prepaid label."),
    dict(item_id="P07", scenario_id="SC06", theme="damaged_products",
         customer_message="My new laptop's screen arrived with a big scratch across it. I noticed it while unboxing yesterday. What do I do?",
         policy_rule_ids=["DMG-1", "DMG-2", "DMG-3"], policy_excerpt=excerpt("DMG-1", "DMG-2", "DMG-3"),
         candidate_reply="Sorry about that! Since you noticed it right at unboxing, you're well within our 7-day damage-reporting window. Please reply with a couple of photos of the scratch and the packaging, and once we verify it, we'll ship a free replacement right away without needing the damaged one back first - we'll include a prepaid label so you can return it whenever's convenient. If your exact model happens to be out of stock, we'll offer you a full refund or an equivalent substitute instead.",
         source="team_written", source_id=None, adapted=False, original_instruction=None,
         challenge_type="correct",
         author_note="Pairs with P08's impolite answer to the identical question, to test that politeness and correctness are scored independently."),
    dict(item_id="P08", scenario_id="SC06", theme="damaged_products",
         customer_message="My new laptop's screen arrived with a big scratch across it. I noticed it while unboxing yesterday. What do I do?",
         policy_rule_ids=["DMG-1", "DMG-2", "DMG-3"], policy_excerpt=excerpt("DMG-1", "DMG-2", "DMG-3"),
         candidate_reply="You probably just scratched it yourself. Send photos if you want us to check, but don't expect a free replacement.",
         source="team_written", source_id=None, adapted=False, original_instruction=None,
         challenge_type="impolite",
         author_note="Presumptuous and dismissive tone toward a customer reporting arrival damage within the covered window; also drifts toward incorrect by pre-judging the claim invalid."),
    dict(item_id="P09", scenario_id="SC07", theme="damaged_products",
         customer_message="I dropped my phone in the sink two days after it arrived and now it won't charge. Can you send me a free replacement?",
         policy_rule_ids=["DMG-4"], policy_excerpt=excerpt("DMG-4"),
         candidate_reply="I'm sorry that happened! Unfortunately, water damage from an accident after delivery isn't covered under our damage policy, so we're not able to send a free replacement for this. I'd recommend checking whether the manufacturer's warranty covers liquid damage - I'm happy to share the manufacturer's support contact if that would help.",
         source="team_written", source_id=None, adapted=False, original_instruction=None,
         challenge_type="correct",
         author_note="Tests whether the reply correctly declines under DMG-4 (customer-caused damage) instead of defaulting to the DMG-1/DMG-2 damaged-on-arrival path. Pairs with P10."),
    dict(item_id="P10", scenario_id="SC07", theme="damaged_products",
         customer_message="I dropped my phone in the sink two days after it arrived and now it won't charge. Can you send me a free replacement?",
         policy_rule_ids=["DMG-4"], policy_excerpt=excerpt("DMG-4"),
         candidate_reply="No problem, since it happened so soon after delivery we'll count it as a damaged item and ship you a free replacement right away.",
         source="team_written", source_id=None, adapted=False, original_instruction=None,
         challenge_type="incorrect",
         author_note="Wrongly treats accidental customer-caused damage as covered; violates DMG-4."),
    dict(item_id="P11", scenario_id="SC08", theme="damaged_products",
         customer_message="The blender I received three weeks ago is defective - it stopped working after one use. Can I get a replacement?",
         policy_rule_ids=["DMG-1", "DMG-5"], policy_excerpt=excerpt("DMG-1", "DMG-5"),
         candidate_reply="Thanks for letting us know. Since it's been about three weeks since delivery, this is outside our 7-day window for a free damage replacement, and a defective item usually won't qualify as 'unused in original condition' for a standard 30-day return either. I don't want to promise something we can't honor, so let me check internally on options for a defect reported after 7 days and follow up with you by email today.",
         source="team_written", source_id=None, adapted=False, original_instruction=None,
         challenge_type="correct",
         author_note="Deliberate policy-gap edge case: the policy does not fully specify what happens for a defect reported after 7 days. The 'good' answer names the gap and escalates rather than inventing an entitlement. Use this item to check the guide's rule on policy gaps."),
    dict(item_id="P12", scenario_id="SC08", theme="damaged_products",
         customer_message="The blender I received three weeks ago is defective - it stopped working after one use. Can I get a replacement?",
         policy_rule_ids=["DMG-1", "DMG-5"], policy_excerpt=excerpt("DMG-1", "DMG-5"),
         candidate_reply="Sure, that's within our replacement window, we'll send a free replacement out today.",
         source="team_written", source_id=None, adapted=False, original_instruction=None,
         challenge_type="incorrect",
         author_note="Falsely claims the report is within the 7-day DMG-1 window when it is three weeks later."),

    # --- Shipping (SC09-SC12) ---
    dict(item_id="P13", scenario_id="SC09", theme="shipping",
         customer_message="I have to check the options for shipping, how could I do it?",
         policy_rule_ids=["SHIP-1"], policy_excerpt=excerpt("SHIP-1"),
         candidate_reply="Happy to help! We offer standard shipping (3-7 business days), which is free on orders of $50 or more (otherwise it's a flat $6.99), and express shipping (1-2 business days) for $14.99 regardless of order size. You can choose either option at checkout.",
         source="bitext", source_id=12001, adapted=False, original_instruction=None,
         challenge_type="correct",
         author_note="Clean baseline correct/complete answer on shipping options and cost."),
    dict(item_id="P14", scenario_id="SC10", theme="shipping",
         customer_message="hsipping to Canada",
         policy_rule_ids=["SHIP-2"], policy_excerpt=excerpt("SHIP-2"),
         candidate_reply="We ship to a lot of countries, so you're probably fine.",
         source="bitext", source_id=12003, adapted=True,
         original_instruction="hsipping to {{Delivery Country}}",
         challenge_type="incomplete",
         author_note="Placeholder filled with 'Canada'; original typo ('hsipping') kept intentionally as authentic noisy input. Reply dodges the actual yes/no and doesn't tell the customer how to verify against the checkout list."),
    dict(item_id="P15", scenario_id="SC11", theme="shipping",
         customer_message="my shipping address changed, can I update it?",
         policy_rule_ids=["SHIP-3"], policy_excerpt=excerpt("SHIP-3"),
         candidate_reply="Sure - I just need to check one thing: has your order shipped yet? If it's still showing 'Processing,' I can update the address for you right now. If it's already shipped, unfortunately neither of us can change the delivery address anymore, and you'd need to contact the carrier directly.",
         source="bitext", source_id=2010, adapted=False, original_instruction=None,
         challenge_type="asks_for_missing_info",
         author_note="SHIP-3's outcome depends on order status, which isn't given; asking is the correct move, not a completeness deduction."),
    dict(item_id="P16", scenario_id="SC12", theme="shipping",
         customer_message="do you shp to Casablanca?",
         policy_rule_ids=["SHIP-2"], policy_excerpt=excerpt("SHIP-2"),
         candidate_reply="Yes, we ship everywhere in the world, no restrictions at all!",
         source="bitext", source_id=12013, adapted=True,
         original_instruction="do you shp to {{Delivery City}}?",
         challenge_type="incorrect",
         author_note="Placeholder filled with 'Casablanca'; typo ('shp') kept intentionally. Overpromises far beyond SHIP-2, which limits shipping to countries listed at checkout."),

    # --- Account security (SC13-SC15) ---
    dict(item_id="P17", scenario_id="SC13", theme="account_security",
         customer_message="I have lost my user password, where do I retrieve it?",
         policy_rule_ids=["SEC-1"], policy_excerpt=excerpt("SEC-1"),
         candidate_reply="No problem! Click 'Forgot password' on the login page and we'll email a reset link to the address on your account. That link is valid for 60 minutes. For your security, we're not able to see or reset your password directly on our end.",
         source="bitext", source_id=20001, adapted=False, original_instruction=None,
         challenge_type="correct",
         author_note="Baseline correct self-service reset answer; pairs with P18's policy-violating answer to the same question."),
    dict(item_id="P18", scenario_id="SC13", theme="account_security",
         customer_message="I have lost my user password, where do I retrieve it?",
         policy_rule_ids=["SEC-1"], policy_excerpt=excerpt("SEC-1"),
         candidate_reply="Just reply with your current password and I'll reset it for you right now.",
         source="bitext", source_id=20001, adapted=False, original_instruction=None,
         challenge_type="incorrect",
         author_note="Directly violates SEC-1 and SEC-3 (support must never ask for a password). Must score 0 on correctness regardless of how confident/friendly it sounds - a good adversarial item for the judge."),
    dict(item_id="P19", scenario_id="SC14", theme="account_security",
         customer_message="someone stole my PIN, I want assistance to restore it",
         policy_rule_ids=["SEC-2"], policy_excerpt=excerpt("SEC-2"),
         candidate_reply="Okay, you can reset your PIN using the 'Forgot password' link.",
         source="bitext", source_id=20090, adapted=False, original_instruction=None,
         challenge_type="incomplete",
         author_note="Treats a reported theft/unauthorized-access case as a routine self-service reset; misses the required account lock, fraud review of recent orders, and 2FA recommendation under SEC-2."),
    dict(item_id="P20", scenario_id="SC15", theme="account_security",
         customer_message="remove Premium account",
         policy_rule_ids=["SEC-4"], policy_excerpt=excerpt("SEC-4"),
         candidate_reply="Fine, deleting it. You'll have two weeks to change your mind I guess.",
         source="bitext", source_id=11004, adapted=True,
         original_instruction="remove {{Account Type}} account",
         challenge_type="impolite",
         author_note="Placeholder filled with 'Premium'. Content is substantially correct (14-day grace period) but the tone is curt/dismissive - tests that correctness and politeness are scored independently rather than one score dragging the other down."),
]

REQUIRED_FIELDS = [
    "item_id", "scenario_id", "theme", "customer_message", "policy_rule_ids",
    "policy_excerpt", "candidate_reply", "source", "source_id", "adapted",
    "original_instruction", "challenge_type", "author_note",
]

def validate(items):
    errors = []
    item_ids = [it["item_id"] for it in items]
    if len(item_ids) != len(set(item_ids)):
        errors.append("Duplicate item_id found")
    for it in items:
        for f in REQUIRED_FIELDS:
            if f not in it:
                errors.append(f"{it.get('item_id','?')}: missing field {f}")
        if it["source"] == "bitext" and not it.get("source_id"):
            errors.append(f"{it['item_id']}: bitext source missing source_id")
        if it["source"] == "team_written" and it.get("source_id") is not None:
            errors.append(f"{it['item_id']}: team_written source should have source_id=None")
        if it["adapted"] and it["source"] == "bitext" and not it.get("original_instruction"):
            errors.append(f"{it['item_id']}: adapted bitext item missing original_instruction")
        for rid in it["policy_rule_ids"]:
            if rid not in RULES:
                errors.append(f"{it['item_id']}: unknown policy rule id {rid}")
        if not it["customer_message"].strip():
            errors.append(f"{it['item_id']}: empty customer_message")
        if not it["candidate_reply"].strip():
            errors.append(f"{it['item_id']}: empty candidate_reply")
    return errors

def main():
    errors = validate(ITEMS)
    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(" -", e)
        raise SystemExit(1)

    os.makedirs(REPO_DATA, exist_ok=True)

    # JSONL (machine-readable, full fidelity)
    jsonl_path = os.path.join(REPO_DATA, "pilot_items.jsonl")
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for it in ITEMS:
            row = dict(it)
            row["policy_source_dataset"] = BITEXT_SOURCE if it["source"] == "bitext" else None
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # CSV (easy-to-review, flattens the rule id list)
    csv_path = os.path.join(REPO_DATA, "pilot_items.csv")
    fieldnames = REQUIRED_FIELDS + ["policy_source_dataset"]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for it in ITEMS:
            row = dict(it)
            row["policy_rule_ids"] = ";".join(it["policy_rule_ids"])
            row["policy_source_dataset"] = BITEXT_SOURCE if it["source"] == "bitext" else ""
            row["original_instruction"] = it["original_instruction"] or ""
            row["source_id"] = it["source_id"] if it["source_id"] is not None else ""
            w.writerow(row)

    # Blank labelling sheets (two independent copies, no scores prefilled)
    for labeller in ("labeler1", "labeler2"):
        path = os.path.join(REPO_DATA, f"labelling_sheet_{labeller}.csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow([
                "item_id", "scenario_id", "customer_message", "policy_excerpt",
                "candidate_reply", "correctness_score_0_1_2", "politeness_score_0_1_2",
                "completeness_score_0_1_2", "labeller_notes",
            ])
            for it in ITEMS:
                w.writerow([
                    it["item_id"], it["scenario_id"], it["customer_message"],
                    it["policy_excerpt"], it["candidate_reply"], "", "", "", "",
                ])

    # Summary for the report-back
    from collections import Counter
    theme_counts = Counter(it["theme"] for it in ITEMS)
    challenge_counts = Counter(it["challenge_type"] for it in ITEMS)
    source_counts = Counter(it["source"] for it in ITEMS)
    scenario_counts = Counter(it["scenario_id"] for it in ITEMS)
    n_scenarios = len(scenario_counts)
    n_multi_reply = sum(1 for c in scenario_counts.values() if c > 1)

    print(f"Wrote {len(ITEMS)} items to {jsonl_path}")
    print(f"Distinct scenarios (unique customer questions): {n_scenarios}")
    print(f"Scenarios with >1 candidate reply: {n_multi_reply}")
    print("Theme distribution:", dict(theme_counts))
    print("Challenge type distribution:", dict(challenge_counts))
    print("Source distribution:", dict(source_counts))
    print("Validation: OK (no errors)")

if __name__ == "__main__":
    main()
