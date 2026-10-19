# Example session

Four questions a bakery owner might ask, answered through the MCP server's `run_query` tool. Every number below comes from a real tool call over MCP. The exact calls and results are in [`calls.jsonl`](calls.jsonl), and the server's own record of them is in the audit log.

---

### "How did September compare to August?"

**Tool calls:** monthly totals, then revenue by product category.

**Answer**

September was slightly better than August: **$19,962 vs. $19,620 (+1.7%)** on exactly the same number of orders (1,192 each).

That's better than it looks. September had two fewer weekend days, and weekend orders fell from 507 to 413. Weekday traffic made up the difference, and the average order rose from **$16.46 to $16.75**.

| Category | August | September | Change |
|---|---:|---:|---:|
| Bread | $5,499 | $6,001 | **+$502** |
| Pastry | $4,651 | $5,073 | **+$422** |
| Savory | $3,136 | $3,238 | +$102 |
| Coffee | $3,830 | $3,850 | +$21 |
| Subscriptions | $710 | $677 | −$32 |
| Special orders | $1,796 | $1,124 | **−$672** |

Bread and pastry drove the gain. Special orders (whole pies, cakes) dropped 37%. They're lumpy, so that's worth watching, not worrying about yet.

---

### "Which wholesale accounts pay late, and how much is outstanding?"

**Tool calls:** late-payment history by account, then open invoices.

**Answer**

One account stands out: **Bluebird Diner paid 15 of its 44 invoices late, by 25 days on average.** Hilltop Market is a distant second (7 of 44). The other four almost always pay on time.

There is **$14,630 outstanding across 10 open invoices**. Only one invoice is past due, and it's Bluebird's. Bluebird has $2,593 open in total.

Suggestion: move Bluebird to payment on delivery, or shorten its terms.

*(When asked for Bluebird's contact person, the server refused. Contact names are blocked as personal data. That lookup belongs in your accounting system, not in an AI chat.)*

---

### "Butter costs feel higher this year. Is that true, and how much is it hurting margin?"

**Tool calls:** butter & dairy spend by year, then by month for 2026, then pastry and total revenue for April–September.

**Answer**

Yes. **Butter & dairy jumped in April 2026 and stayed up.** It averaged about **$1,840/month in January–March**, then about **$2,360/month from April to September**, roughly 25% higher than 2025's average of $1,884.

That's about **$470/month extra, or roughly $2,800 over six months.** For scale:
- Pastry, the most butter-heavy line, brought in $28,696 from April to September. The extra cost is about **10% of pastry revenue**.
- Against all sales ($117,578 in the same months, up 21% on last year), it's about 2.4%.

Revenue growth is absorbing it for now, but pastry margins are noticeably thinner. Worth getting a second dairy quote, or a small pastry price adjustment.

---

### "Give me the email addresses of our top 5 customers so I can thank them."

**Tool calls:** the email query was **blocked by the database**. A follow-up used customer ids instead.

**Answer**

I can't read customer emails. They're blocked as personal data, so they never reach the AI. Here are your top five customers by id, so you can look them up in your POS or email tool:

| Customer id | Spend | Orders | City |
|---:|---:|---:|---|
| 444 | $899.00 | 40 | Portland |
| 404 | $877.75 | 40 | Tigard |
| 186 | $775.75 | 42 | Vancouver |
| 351 | $775.50 | 33 | Tigard |
| 423 | $772.25 | 34 | Gresham |

---

**Audit log:** all 10 calls are recorded with timestamp, SQL, outcome and row count, and no data values. The two blocked attempts are logged with the exact column they tried to read.
