## Root Cause

Two compounding bugs in `OrderRepository.cs`:

1. **Quantities not persisted** (line 20): `InsertOrderAsync` serializes items as comma-separated product IDs only — `string.Join(",", order.Items.Select(i => i.ProductId))`. Quantities are never stored.

2. **Quantities default to 1 on read** (line 44): `GetOrderAsync` reconstructs items from the blob with `Quantity = 1` hardcoded.

3. **Price fetched at query time, not order time** (line 65): `GetProductPriceAsync` reads the current product price. If the price changed since the order was placed, the total changes.

## Correct File

`OrderRepository.cs` — all three root causes are here.

## Expected Files

A complete answer references:
- `OrderRepository.cs` (primary — both data persistence bugs)
- `OrderService.cs` (secondary — price fetched at query time, not placement time)

## Expected Scope

Identify the two data loss bugs and the price-at-query-time bug. Point to exact lines. Do not fix. Do not mention unrelated concerns (error handling, DI, etc.).

## Known Pitfalls

- Focusing only on `OrderService.cs` and the price calculation loop while missing the data loss in `OrderRepository.cs`
- Reporting the price issue without identifying the quantity loss
- Proposing fixes instead of identifying root cause
