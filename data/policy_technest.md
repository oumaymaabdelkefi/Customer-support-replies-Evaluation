# TechNest Gadgets — Customer Support Policy (FICTIONAL)

**This is a fictional policy for a made-up online electronics retailer,
"TechNest Gadgets," written by Team SupportScore for CS496 Project 1.
It is not the policy of any real company and must not be presented as one.**

It exists so that our labelling guide and LLM judge have a single, fixed
source of truth to grade customer support replies against. Every
`correctness` judgment in this project — human or LLM — must be traceable
to one of the numbered rules below. If a rule doesn't cover a question, the
right answer is to say so, not to invent one.

## Returns

- **RET-1**: Items may be returned within 30 calendar days of delivery for
  a full refund of the item price, provided the item is unused, in its
  original packaging, and includes all accessories and manuals.
- **RET-2**: TechNest pays return shipping only when the return is due to
  a defective or damaged item (see Damaged Products). For a return that is
  not due to a defect (e.g., changed mind, wrong size), the customer pays
  return shipping, unless the original order total was $100 or more, in
  which case TechNest provides a free prepaid return label.
- **RET-3**: Opened software licenses, digital gift cards, and items
  marked "final sale" at checkout cannot be returned.
- **RET-4**: Once TechNest receives and inspects a returned item, the
  refund is issued to the original payment method within 5-7 business
  days.
- **RET-5**: An order can be cancelled at no charge at any time before it
  ships. Once an order's status is "Shipped," it can no longer be
  cancelled; the customer must wait for delivery and then request a
  standard return instead.

## Damaged or Defective Products

- **DMG-1**: Damage or defects present on arrival must be reported within
  7 calendar days of delivery, with photos of the item and its packaging
  attached to the support request.
- **DMG-2**: Once a damage report is verified, TechNest ships a free
  replacement immediately, without requiring the damaged unit to be
  returned first, and includes a prepaid return label for the damaged
  unit.
- **DMG-3**: If the same model is out of stock for a replacement, the
  customer may choose between a full refund or a substitute item of
  equivalent value.
- **DMG-4**: Damage caused by the customer after delivery (drops, spills,
  misuse, etc.) is not covered by this policy. The customer should be
  directed to the manufacturer's warranty, if any, instead of being
  offered a free TechNest replacement.
- **DMG-5**: A damage report made more than 7 days after delivery is not
  eligible under this section, though the item may still qualify for a
  standard return under RET-1 if within 30 days and otherwise unused
  (which will rarely apply to a damaged item, since "unused, original
  condition" is required). **This is a deliberate policy gap** — the
  policy does not say what happens to a defect reported after 7 days but
  within 30. The correct behavior is to name the gap and escalate, not to
  invent an entitlement.
- **DMG-6**: Support cannot promise an exact replacement delivery date;
  standard replacement shipping takes 3-5 business days after
  verification.

## Shipping

- **SHIP-1**: Standard shipping (3-7 business days) is free on orders of
  $50 or more; otherwise a flat $6.99 fee applies. Express shipping (1-2
  business days) costs $14.99 regardless of order size.
- **SHIP-2**: TechNest currently ships only to the countries listed at
  checkout. Support may confirm whether a specific country is supported,
  but must not promise shipping to a country not listed at checkout.
- **SHIP-3**: A shipping address can be changed by the customer or by
  support only while the order status is "Processing." Once the status is
  "Shipped," neither TechNest nor the customer can change the delivery
  address; the customer must contact the carrier directly.
- **SHIP-4**: Support does not have live parcel-location data and cannot
  guarantee an exact delivery date. Customers should use the tracking
  link emailed at the time of shipment.
- **SHIP-5**: If tracking shows no movement for 10 or more business days,
  the package is considered lost in transit and is eligible for a free
  reshipment or a full refund once TechNest confirms the loss with the
  carrier.

## Account Security

- **SEC-1**: Password resets are self-service only, through the "Forgot
  password" link, which emails a reset link valid for 60 minutes to the
  email on file. Support cannot reset a password directly, and can never
  see, read, or share a customer's password.
- **SEC-2**: If a customer reports signs of unauthorized access (an
  unrecognized order, a login alert from an unfamiliar location, a stolen
  password or PIN), support must immediately lock the account, force a
  password reset, and review recent orders for fraud, and should
  recommend the customer enable two-factor authentication (2FA) once back
  in.
- **SEC-3**: Support never asks a customer for their full password, full
  card number, or a 2FA code. Any message that asks for these is not
  really from TechNest and should be reported.
- **SEC-4**: Account deletion is not immediate: the account enters a
  14-day grace period during which the customer can cancel the deletion
  by logging back in. After 14 days, deletion is permanent.
- **SEC-5**: Changing the email address on file requires the customer to
  click a confirmation link sent to the new email address before the
  change takes effect, to prevent account takeover.

## What support does NOT have access to

- **GEN-1**: For this project, support (human or model) never has live
  access to a real order database. It cannot look up whether a specific
  order number has shipped, its live tracking position, or
  account-specific details. A reply that needs one of those facts to be
  correct should ask the customer, or state the answer conditionally on
  it — it should not guess, and it should not promise to "check and get
  back to you," since that promise can't actually be kept under this
  constraint. This is intentional: several items across the pilot and
  golden set test whether a candidate reply asks for missing information
  instead of inventing an order status or promising a live lookup it
  can't perform.

## Known gaps (not yet covered by any rule)

Sampling real customer questions for the golden set surfaced requests
this policy does not address. These are deliberately **not** patched by
inventing a rule from a single example — see
`GOLDEN_SAMPLE_REVIEW.md` for the evidence review that found them. Until
the team adds rules here, a reply to one of these should say the policy
doesn't cover it and offer to escalate, per the "Policy gaps" guidance in
`labelling_guide.md` — that is the *correct* behavior, not a missing
answer.

- Modifying an existing order's contents (adding/removing items) —
  distinct from cancelling it (RET-5) or returning it after delivery
  (RET-1).
- Sign-up/registration problems (creating a new account, not managing an
  existing one).
- Generic profile-detail edits (name, phone, etc.) — SEC-5 covers only
  the email-change case specifically.
- Switching or upgrading an account tier/plan.
