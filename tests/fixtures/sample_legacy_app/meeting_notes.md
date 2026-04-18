# Meeting Notes — InventoryPro Modernization Kickoff

**Date:** 2024-01-22  
**Attendees:** Sarah Chen (VP Ops), Mike Torres (IT Director), Priya Patel (Lead Dev), James Wu (Warehouse Manager), Lisa Tran (Finance)  
**Facilitator:** Priya Patel

---

## Agenda

1. Review BRD v1.4
2. Technical assessment of current system
3. Supplier integration timeline
4. Open questions and decisions

---

## Discussion & Decisions

### Authentication
- **Decision:** SSO migration to SAML 2.0 is confirmed. IT has already started the IdP configuration.
- **Decision:** Account lockout policy: 3 failed attempts → 30-minute lockout was agreed upon. Mike confirmed this aligns with the new corporate security policy effective March 2024.
- James asked about warehouse staff who share tablets — **Decision:** Warehouse staff will use badge-based login (scan employee badge) instead of username/password. This requires integration with the existing HID badge reader system via USB HID protocol.

### Inventory & Reorder
- Sarah clarified that the reorder quantity calculation in the BRD (2x minimum stock level) is a starting point. **Decision:** The system should also consider average daily consumption rate over the past 90 days when calculating reorder quantities. Formula: `max(2 * min_stock, avg_daily_consumption * supplier_lead_time_days * 1.5)`.
- James raised that some products are seasonal — winter gear vs summer gear. The reorder logic needs to account for seasonality. **Action Item:** Priya to research demand forecasting approaches. Due: Feb 15.
- **Decision:** Every reorder request must log the calculation method and inputs used, for audit purposes.

### Order Processing
- Lisa (Finance) asked about the approval threshold. Current BRD says $5,000. Sarah confirmed $5,000 is correct and that the old $10,000 threshold in the code was a mistake that was never corrected.
- **Decision:** Three-tier approval: $5K-$25K needs manager, $25K+ needs executive, under $5K is auto-approved. This is already in the BRD.
- **NEW REQUIREMENT (not in BRD):** Lisa requested that all orders must capture a cost center code for accounting purposes. Each department has a unique cost center code. Orders without a cost center should be rejected.

### Supplier Integration
- Mike confirmed that **two suppliers have agreed to API integration**: Acme Parts (REST/JSON) and GlobalSupply Co (SOAP/XML). APIs are expected to be available by April 2024.
- **Decision:** Start with Acme Parts integration first as a pilot, then add GlobalSupply.
- The supplier API will provide: real-time pricing, stock availability, estimated delivery dates, and bulk discount tiers.
- **Risk:** GlobalSupply's SOAP API has no sandbox/test environment. We'll need to build a mock service for development.

### Reporting
- Lisa requested a **weekly inventory valuation report** in addition to the monthly summary in the BRD. This shows the total value of inventory on hand (quantity × unit cost) grouped by category and warehouse.
- **Decision:** Reports module must support scheduled generation (daily, weekly, monthly) with email delivery to configured recipients.

### Data Migration
- Priya noted the existing database has ~2.3 million product records and ~15 million order records spanning 5 years.
- **Concern:** Some legacy data has NULL supplier_id values (about 8% of products). These were manually ordered products. **Decision:** Map these to a "Manual/Other" supplier during migration.

---

## Action Items

| # | Action | Owner | Due Date |
|---|--------|-------|----------|
| 1 | Research demand forecasting for reorder quantities | Priya | Feb 15, 2024 |
| 2 | Negotiate sandbox access with GlobalSupply Co | Mike | Feb 28, 2024 |
| 3 | Document badge reader integration requirements | James | Feb 10, 2024 |
| 4 | Update BRD with cost center requirement | Sarah | Feb 5, 2024 |
| 5 | Assess data migration complexity and create plan | Priya | Feb 20, 2024 |

---

## Open Questions

1. Should we support offline mode for the warehouse mobile app? (James raised this — WiFi can be spotty in the far end of Warehouse B)
2. Do we need to support multi-currency for international suppliers? (Lisa asked — currently all transactions are USD)
3. What is the retention policy for order history? (Compliance says 7 years, but storing 7 years of data in the primary DB may hurt performance)
