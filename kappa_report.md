# Kappa Report

Items scored by both labellers: 48

## Kappa per axis

| Axis | N (both scored) | Skipped (NA/blank) | Kappa | Interpretation |
|---|---|---|---|---|
| correctness | 48 | 0 | 0.621 | substantial (meets the >= 0.6 target) |
| politeness | 48 | 0 | 0.263 | fair (below the 0.6 target) |
| completeness | 48 | 0 | 0.176 | slight (below the 0.6 target) |

## Disagreements by axis

### correctness (12 disagreements)

| item_id | batch | labeler1 | labeler2 | labeler1 notes | labeler2 notes |
|---|---|---|---|---|---|
| G01 | golden_sample_stage1 | 0 | 1 | Gives cancel steps without checking/asking shipped status (RET-5 is conditional); GEN-1 - can't know order state. | Elaborates standard steps/support info not in policy (correctness 1). |
| G02 | golden_sample_stage1 | 0 | 1 | Same as G01 - no shipped-status check before promising self-service cancellation. | Elaborates standard cancellation steps (correctness 1). |
| G03 | golden_sample_stage1 | 1 | 0 | Policy gap (no rule for adding items) - proceeds as routine request instead of flagging gap/escalating. | Policy gap item: fails to state policy gap and offer escalation. |
| G04 | golden_sample_stage1 | 1 | 0 | Policy gap (no rule for removing items) - same issue as G03, no gap acknowledgment. | Policy gap item: fails to state policy gap and offer escalation. |
| G17 | golden_sample_stage1 | 2 | 1 | Reasonable clarifying questions about the technical issue; doesn't consider/mention that inability to submit may be because the order already shipped (SHIP-3). | Asks for troubleshooting details; reasonable response. |
| G23 | golden_sample_stage1 | 2 | 1 | Accurately elaborates the self-service reset flow; misses explicitly stating support can't see/reset the password directly. | Elaborates step-by-step instructions and support info beyond SEC-1. |
| G24 | golden_sample_stage1 | 1 | 0 | Policy gap (signup issue not covered) - asks for details rather than acknowledging gap/escalating, but doesn't invent a false answer. | Policy gap item: fails to state policy gap and offer escalation. |
| G25 | golden_sample_stage1 | 0 | 1 | Describes ordinary subscription-cancellation steps and 'active until end of billing cycle' framing; never mentions the mandated 14-day grace period / ability to reverse by logging back in (SEC-4). | Elaborates subscription cancellation steps not mentioned in SEC-4. |
| G26 | golden_sample_stage1 | 1 | 0 | Never mentions the SEC-5 confirmation-link requirement for email changes - the one substantive rule relevant to this request. | Contradicts SEC-5 by omitting required email confirmation link. |
| G28 | golden_sample_stage1 | 1 | 0 | Policy gap (account opening not covered) - asks for reasonable signup details without falsely asserting a confirmed process, similar to G03/G04. | Policy gap item: collects account details instead of stating gap. |
| P06 | pilot | 1 | 2 |  | Correctly asks for photos per DMG-1, but omits replacement details. |
| P08 | pilot | 0 | 1 |  | Disrespectful tone ('you probably scratched it yourself') violates politeness. |

### politeness (7 disagreements)

| item_id | batch | labeler1 | labeler2 | labeler1 notes | labeler2 notes |
|---|---|---|---|---|---|
| G16 | golden_sample_stage1 | 1 | 2 | Same SHIP-3 omission as G15; also curt/generic, no acknowledgment of the request. | Contradicts SHIP-3 by claiming customer can update address anytime. |
| P02 | pilot | 1 | 2 |  | Contradicts policy on refund timeframe (says instant instead of 5-7 days). |
| P03 | pilot | 1 | 2 |  | Correct 30-day timeframe but misses item condition details. |
| P12 | pilot | 1 | 2 | Same issue as P10: skips the real applicable content (7-day window passed, standard-return path unlikely) entirely. | Contradicts DMG-5 by treating 3-week-old defect as within window. |
| P14 | pilot | 1 | 2 |  | Violates SHIP-2 by making an unsupported vague promise. |
| P19 | pilot | 1 | 2 | Treats stolen PIN as ordinary password reset; misses SEC-2 mandatory steps (lock account, review orders, recommend 2FA). | Contradicts SEC-2 for stolen PIN by suggesting password reset instead of lock. |
| P20 | pilot | 0 | 1 | Facts roughly match 14-day grace period, but 'Fine, deleting it... I guess' reads dismissive; doesn't say how to reverse (log back in). | Politeness 1 due to curt tone; correctness 2 for 14-day grace period. |

### completeness (29 disagreements)

| item_id | batch | labeler1 | labeler2 | labeler1 notes | labeler2 notes |
|---|---|---|---|---|---|
| G01 | golden_sample_stage1 | 1 | 2 | Gives cancel steps without checking/asking shipped status (RET-5 is conditional); GEN-1 - can't know order state. | Elaborates standard steps/support info not in policy (correctness 1). |
| G02 | golden_sample_stage1 | 1 | 2 | Same as G01 - no shipped-status check before promising self-service cancellation. | Elaborates standard cancellation steps (correctness 1). |
| G05 | golden_sample_stage1 | 0 | 2 | Lists refund reasons (defect, event cancellation, unauthorized charges, etc.) not in RET-1/RET-3 excerpt at all - fabricated, doesn't mention actual 30-day/unused-condition rule. | Contradicts policy by inventing commercial refund reasons. |
| G07 | golden_sample_stage1 | 0 | 2 | Deflects to phone/live chat instead of stating the actual RET-1/RET-4 info it already has (30-day window, 5-7 day refund). | Adds general support contact info not in policy. |
| G08 | golden_sample_stage1 | 0 | 1 | Generic 'give me details' with no reference to the 30-day/unused-condition policy already available. | Elaborates generic conversational prompts without 30-day anchor. |
| G09 | golden_sample_stage1 | 0 | 1 | GEN-1 violation: 'let me quickly check the progress and get back to you' - promises a live lookup support can't do; also never states actual 5-7 day timeframe. | Violates GEN-1 by promising a live lookup/check and follow-up. |
| G10 | golden_sample_stage1 | 0 | 2 | GEN-1 violation: asks for reference number and promises to 'verify...provide latest updates' - implies live lookup; omits actual 5-7 day policy figure. | Asks for compensation claim details; implies lookup (correctness 1). |
| G11 | golden_sample_stage1 | 1 | 2 | Confidently promises delivery to Sfax without confirmation - directly against SHIP-2 ('must not promise shipping to a country not listed at checkout'). | Violates SHIP-2 by promising shipping to Sfax without verification. |
| G12 | golden_sample_stage1 | 0 | 2 | Mentions 'overnight shipping' and 'in-store pickup' not in SHIP-1 excerpt (unverified elaboration) and never gives the actual $50/$6.99/$14.99 figures the customer needs. | Elaborates website navigation and support contact info. |
| G13 | golden_sample_stage1 | 1 | 2 | GEN-1 pattern: asks for tracking/order number implying it can then give an estimated delivery date, which SHIP-4 says support cannot guarantee; doesn't mention the emailed tracking link. | Asks for tracking/order number to provide estimate (correctness 1). |
| G14 | golden_sample_stage1 | 1 | 2 | Describes a website 'Order Tracking' page rather than the emailed tracking link from SHIP-4 (unverified alternate mechanism); doesn't state that an exact date can't be guaranteed. | Elaborates tracking steps and support contact info. |
| G15 | golden_sample_stage1 | 0 | 1 | No mention of the Processing-vs-Shipped condition from SHIP-3 at all; treats address correction as always available. | Fails to check order status per SHIP-3, offering direct address change. |
| G17 | golden_sample_stage1 | 1 | 2 | Reasonable clarifying questions about the technical issue; doesn't consider/mention that inability to submit may be because the order already shipped (SHIP-3). | Asks for troubleshooting details; reasonable response. |
| G18 | golden_sample_stage1 | 1 | 2 | Detailed steps given but never mentions the Processing-vs-Shipped restriction from SHIP-3. | Contradicts SHIP-3 by giving address entry steps without order check. |
| G19 | golden_sample_stage1 | 0 | 2 | Pure complaint-intake boilerplate; never applies DMG-1/DMG-2 (7-day window, photos, free replacement) despite router issue being well within scope. | Asks for general complaint details rather than DMG-1 photo requirements. |
| G20 | golden_sample_stage1 | 0 | 2 | Deflects to 'our customer support team' (redundant, since this is support) without ever stating DMG-1/DMG-2 (7-day window, photos, free replacement). | Directs to customer support team instead of DMG-1 process. |
| G21 | golden_sample_stage1 | 0 | 2 | Generic complaint-lodging instructions; never states the actual DMG-1/DMG-2/DMG-3 entitlements that clearly apply here. | Directs to general contact page rather than damage reporting process. |
| G22 | golden_sample_stage1 | 0 | 2 | Vague request for 'details/documentation'; never mentions 7-day window, photos, or free replacement despite policy being directly relevant. | Asks for claim details and supporting documentation. |
| G23 | golden_sample_stage1 | 1 | 2 | Accurately elaborates the self-service reset flow; misses explicitly stating support can't see/reset the password directly. | Elaborates step-by-step instructions and support info beyond SEC-1. |
| G25 | golden_sample_stage1 | 1 | 2 | Describes ordinary subscription-cancellation steps and 'active until end of billing cycle' framing; never mentions the mandated 14-day grace period / ability to reverse by logging back in (SEC-4). | Elaborates subscription cancellation steps not mentioned in SEC-4. |
| G26 | golden_sample_stage1 | 0 | 2 | Never mentions the SEC-5 confirmation-link requirement for email changes - the one substantive rule relevant to this request. | Contradicts SEC-5 by omitting required email confirmation link. |
| G27 | golden_sample_stage1 | 0 | 2 | Policy gap (no 'Gold account' in policy) - confidently invents a 5-step upgrade process instead of flagging the gap, exactly what the guide's policy-gap rule warns against rewarding. | Policy gap item: invents specific upgrade steps instead of escalation. |
| P03 | pilot | 0 | 1 |  | Correct 30-day timeframe but misses item condition details. |
| P10 | pilot | 0 | 2 | Fabricates coverage DMG-4 excludes; gives no real next step (manufacturer warranty), so completeness scored against the actual applicable rule, not the reply's invented framing. | Contradicts DMG-4 by covering customer drop as transit damage. |
| P12 | pilot | 0 | 2 | Same issue as P10: skips the real applicable content (7-day window passed, standard-return path unlikely) entirely. | Contradicts DMG-5 by treating 3-week-old defect as within window. |
| P14 | pilot | 0 | 1 |  | Violates SHIP-2 by making an unsupported vague promise. |
| P16 | pilot | 1 | 2 |  | Contradicts SHIP-2 by claiming shipping 'everywhere in the world'. |
| P18 | pilot | 0 | 1 |  | Contradicts SEC-1 by asking for password and offering direct reset. |
| P20 | pilot | 1 | 2 | Facts roughly match 14-day grace period, but 'Fine, deleting it... I guess' reads dismissive; doesn't say how to reverse (log back in). | Politeness 1 due to curt tone; correctness 2 for 14-day grace period. |

## Items needing tie-break discussion: 38

G01, G02, G03, G04, G05, G07, G08, G09, G10, G11, G12, G13, G14, G15, G16, G17, G18, G19, G20, G21, G22, G23, G24, G25, G26, G27, G28, P02, P03, P06, P08, P10, P12, P14, P16, P18, P19, P20
