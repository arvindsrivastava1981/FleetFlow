-- Allow RTO-FINE and DEF (Diesel Exhaust Fluid/AdBlue/Urea) as expense types
ALTER TABLE expenses DROP CONSTRAINT IF EXISTS expenses_exp_type_check;
ALTER TABLE expenses ADD CONSTRAINT expenses_exp_type_check
    CHECK (exp_type IN ('FUEL', 'TOLL', 'REPAIR', 'OTHER', 'CHALLAN', 'MISC', 'RTO-FINE', 'DEF'));

-- Remove the retired goods trading feature and its data.
DROP TABLE IF EXISTS trip_goods;