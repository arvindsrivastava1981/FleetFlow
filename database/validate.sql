-- =============================================================================
-- VahanKhata Validation: Financial Netting for Trip 4191-1
-- -----------------------------------------------------------------------------
-- Run after `seed_test_trip.sql`. Recomputes the settlement from the seeded
-- rows and FAILS (RAISE EXCEPTION) on any mismatch with the expected figures.
--
-- Reference settlement for trip 4191-1:
--   Total Cr  = Advance ₹30,000.00 + Goods Sale ₹14,000.00 = ₹44,000.00
--   Total Dr  = Fuel ₹20,240 + DEF ₹1,200 + Toll ₹1,800 + Repair ₹600
--             + Challan ₹1,000 + Misc ₹500 + Goods Buy ₹8,000
--             + Driver Batta ₹2,500.00  = ₹35,840.00
--   Net       = +₹8,160.00  => REFUNDABLE TO FLEET
--
--   Mileage   = (121450 - 120000) / 220.0 L = 6.59 km/L
--
-- Netting rules encoded here (mirror the settlement contract):
--   * Only expenses with manager_status = 'APPROVED' count toward debits,
--     taken at their approved_amount.  The flagged FUEL anomaly is left
--     PENDING with approved_amount = NULL, so it is EXCLUDED automatically.
--   * GOODS_SALE (approved) is income -> goes to the Credit side.
--   * advance_amount and driver_batta_amount come from the trips row.
-- =============================================================================

DO $$
DECLARE
    v_advance        NUMERIC := 0.00;
    v_batta          NUMERIC := 0.00;
    v_start_odo      NUMERIC := 0.00;
    v_current_odo    NUMERIC := 0.00;
    v_goods_sale     NUMERIC := 0.00;
    v_expense_debit  NUMERIC := 0.00;
    v_total_cr       NUMERIC := 0.00;
    v_total_dr       NUMERIC := 0.00;
    v_net            NUMERIC := 0.00;
    v_km             NUMERIC := 0.00;
    v_fuel_liters    NUMERIC := 0.00;
    v_mileage        NUMERIC := 0.00;

    -- Expected values
    c_exp_advance    CONSTANT NUMERIC := 30000.00;
    c_exp_goods_sale CONSTANT NUMERIC := 14000.00;
    c_exp_batta      CONSTANT NUMERIC := 2500.00;
    c_exp_total_cr   CONSTANT NUMERIC := 44000.00;
    c_exp_total_dr   CONSTANT NUMERIC := 35840.00;
    c_exp_net        CONSTANT NUMERIC := 8160.00;
    c_exp_km         CONSTANT NUMERIC := 1450.00;
    c_exp_mileage    CONSTANT NUMERIC := 6.59;
    c_precision      CONSTANT NUMERIC := 0.01;
BEGIN
    -- ------------------------------------------------------------------
    -- Pull reality from the seeded rows for trip 4191-1
    -- ------------------------------------------------------------------
    SELECT advance_amount, driver_batta_amount, start_odo, current_odo
      INTO v_advance, v_batta, v_start_odo, v_current_odo
      FROM trips
     WHERE trip_code = '4191-1';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Validation FAILED: trip 4191-1 not found. Run seed_test_trip.sql first.';
    END IF;

    -- Approved Goods Sale (income, credit side)
    SELECT COALESCE(SUM(approved_amount), 0.00) INTO v_goods_sale
      FROM expenses
     WHERE trip_code = '4191-1'
       AND exp_type = 'GOODS_SALE'
       AND manager_status = 'APPROVED'
       AND approved_amount IS NOT NULL;

    -- Approved expense debits, EXCLUDING income (GOODS_SALE) and the
    -- flagged/unapproved anomaly (approved_amount NULL => excluded too).
    SELECT COALESCE(SUM(approved_amount), 0.00) INTO v_expense_debit
      FROM expenses
     WHERE trip_code = '4191-1'
       AND exp_type <> 'GOODS_SALE'
       AND manager_status = 'APPROVED'
       AND approved_amount IS NOT NULL;

    -- Approved fuel litres for mileage
    SELECT COALESCE(SUM(liters), 0.00) INTO v_fuel_liters
      FROM expenses
     WHERE trip_code = '4191-1'
       AND exp_type = 'FUEL'
       AND manager_status = 'APPROVED';
-- ------------------------------------------------------------------
    -- Compose the ledger
    -- ------------------------------------------------------------------
    v_total_cr := v_advance + v_goods_sale;
    v_total_dr := v_batta + v_expense_debit;
    v_net      := v_total_cr - v_total_dr;

    v_km       := v_current_odo - v_start_odo;
    IF v_fuel_liters > 0 THEN
        v_mileage := ROUND(v_km / v_fuel_liters, 2);
    END IF;

    -- ------------------------------------------------------------------
    -- Assert every figure; fail loudly on the first mismatch
    -- ------------------------------------------------------------------
    IF ABS(v_advance - c_exp_advance) > c_precision THEN
        RAISE EXCEPTION 'Validation FAILED: advance_amount = % (expected %)', v_advance, c_exp_advance;
    END IF;

    IF ABS(v_goods_sale - c_exp_goods_sale) > c_precision THEN
        RAISE EXCEPTION 'Validation FAILED: approved Goods Sale = % (expected %)', v_goods_sale, c_exp_goods_sale;
    END IF;

    IF ABS(v_batta - c_exp_batta) > c_precision THEN
        RAISE EXCEPTION 'Validation FAILED: driver batta = % (expected %)', v_batta, c_exp_batta;
    END IF;

    IF ABS(v_total_cr - c_exp_total_cr) > c_precision THEN
        RAISE EXCEPTION 'Validation FAILED: Total Cr = % (expected %)', v_total_cr, c_exp_total_cr;
    END IF;

    IF ABS(v_total_dr - c_exp_total_dr) > c_precision THEN
        RAISE EXCEPTION 'Validation FAILED: Total Dr = % (expected %)', v_total_dr, c_exp_total_dr;
    END IF;

    IF ABS(v_net - c_exp_net) > c_precision THEN
        RAISE EXCEPTION 'Validation FAILED: Net Balance = % (expected %). Status should be REFUNDABLE TO FLEET.',
                        v_net, c_exp_net;
    END IF;

    IF v_net <= 0 THEN
        RAISE EXCEPTION 'Validation FAILED: Net balance % is not positive (expected refundable-to-fleet balance)',
                        v_net;
    END IF;

    IF ABS(v_km - c_exp_km) > c_precision THEN
        RAISE EXCEPTION 'Validation FAILED: Distance = % km (expected % km)', v_km, c_exp_km;
    END IF;

    IF ABS(v_mileage - c_exp_mileage) > c_precision THEN
        RAISE EXCEPTION 'Validation FAILED: Avg mileage = % km/L (expected %)', v_mileage, c_exp_mileage;
    END IF;

    -- ------------------------------------------------------------------
    -- All good
    -- ------------------------------------------------------------------
    RAISE NOTICE 'VALIDATION PASSED for trip 4191-1';
    RAISE NOTICE '  Total Cr (Advance + Goods Sale): %', v_total_cr;
    RAISE NOTICE '  Total Dr (Expenses + Batta):      %', v_total_dr;
    RAISE NOTICE '  Net Balance:                      %  => REFUNDABLE TO FLEET', v_net;
    RAISE NOTICE '  Distance: % km | Fuel: % L | Mileage: % km/L',
                 v_km, v_fuel_liters, v_mileage;
END $$;