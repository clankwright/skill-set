### Phase 7: storefront polish

**Context.** A sample SPEC phase used by `tests/test_phase44.py` to exercise the
standalone tester's `--phase` scope resolution (Phase 44.2). Mixes front-end
`[x]` items, a backend-only `[x]` item, a docs-only `[x]` item, and a still-open
`[ ]` item so the resolver's front-end predicate + closed-only filter are both
covered.

- [x] 7.1 [medium] **Checkout route redesign.** Rebuild `web/src/routes/checkout.tsx` and `web/src/components/CartSummary.tsx` so the cart total recomputes on quantity change.
- [x] 7.2 [easy] **Lead-capture form.** Add `web/src/components/LeadForm.jsx` to the storefront footer.
- [x] 7.3 [medium] **Payment webhook handler.** Add `api/webhooks/stripe.py` and `api/models/payment.py`; no UI surface.
- [x] 7.4 [easy] **Docs refresh.** Update `docs/STOREFRONT.md` with the new checkout flow.
- [ ] 7.5 [hard] **Inventory dashboard.** Build `web/src/routes/inventory.tsx` (still open — must be excluded from a `--phase 7` sweep).
