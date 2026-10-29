# Retention and Advance on Customer Invoices (Odoo 19)

## How it works (accounting)
Invoice example: work 100,000 + VAT 15,000 = 115,000. Retention 10,000. Advance recovery 20,000.

1. Invoice posts normally: Dr Receivable 115,000 / Cr Revenue 100,000 / Cr VAT 15,000.
2. Retention entry (new misc entry): Dr Retention Receivable 10,000 (due = handover date) / Cr Receivable 10,000. Credit is matched with the invoice.
3. Advance entry (new misc entry, bridge): Cr Receivable 20,000 matched with the invoice, Dr Receivable 20,000 matched with the advance payment.
   Result: invoice residual = 85,000, advance left = 180,000.
4. Release: Dr Receivable (due on release date) / Cr Retention Receivable.
5. Credit note: retention and advance come back in proportion (new entries, no edits).
6. Reset to draft: the generated entries are reversed (never deleted). Posting again creates new ones, so nothing is duplicated.

## Settings
Accounting > Configuration > Settings > "Retention and Advance":
Retention Receivable account (use an asset account of type Current Assets), default retention %, optional journal.

## Assumptions
* "Work done" = invoice amount without VAT. Retention and recovery % are taken on it.
* Project = first sales order found on the invoice lines. No sales order = grouped under the customer only.
* An advance = customer payment (inbound) with no invoice. It is ticked "Advance Payment" automatically when an invoice uses it, and takes the project of that invoice if it has none.
* Credit note must be created from the invoice (reversal) to give retention/advance back.
* Advance given back by a credit note becomes a free open credit of the customer.
* Retention released becomes an open receivable item (journal entry) due on the release date; it is paid by normal payment reconciliation.
* Foreign currency: amounts are converted at the invoice rate. Report is in company currency.

## Manual test
1. Settings: choose Retention Receivable account, default 10%.
2. Register a customer payment 200,000 with no invoice. Tick "Advance Payment".
3. New invoice, line 100,000 + 15% VAT. Tab "Retention and Advance": retention 10%, handover date, advance payment, recovery 20% of work done.
4. Post. Check: amount due 85,000, Retention Receivable +10,000, advance left 180,000.
5. Accounting > Customers > Release Retention: release part, then rest.
6. Credit note (reverse) of the invoice: check retention/advance return.
7. Reset to draft and post again: no duplicate entries (original ones are reversed).
8. Accounting > Reporting > Retention and Advance: Show Report, Export to Excel.
