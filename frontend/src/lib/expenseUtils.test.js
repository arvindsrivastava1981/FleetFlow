import { describe, expect, it } from "vitest";
import {
  SETTLEMENT_TRANSFER,
  impliedRate,
  isInvalidAmount,
  isOdometerRollback,
} from "./expenseUtils.js";

describe("expenseUtils", () => {
  describe("isInvalidAmount (audit D-1 mirror)", () => {
    it("flags zero and negative amounts for normal types", () => {
      expect(isInvalidAmount(0, "FUEL")).toBe(true);
      expect(isInvalidAmount(-250, "REPAIR")).toBe(true);
      expect(isInvalidAmount("0", "TOLL")).toBe(true);
    });

    it("rejects empty / non-numeric amounts", () => {
      expect(isInvalidAmount("", "FUEL")).toBe(true);
      expect(isInvalidAmount(undefined, "FUEL")).toBe(true);
      expect(isInvalidAmount("abc", "FUEL")).toBe(true);
    });

    it("accepts positive amounts", () => {
      expect(isInvalidAmount(1000, "FUEL")).toBe(false);
      expect(isInvalidAmount(0.5, "TOLL")).toBe(false);
    });

    it("exempts SETTLEMENT_TRANSFER (server-computed amount)", () => {
      expect(isInvalidAmount(0, SETTLEMENT_TRANSFER)).toBe(false);
      expect(isInvalidAmount(-1, SETTLEMENT_TRANSFER)).toBe(false);
    });
  });

  describe("impliedRate", () => {
    it("derives ₹/L from amount and litres", () => {
      expect(impliedRate(2000, 20)).toBe(100);
      expect(impliedRate(453.4, 5)).toBe(90.68);
    });

    it("returns null when a term is missing or non-positive", () => {
      expect(impliedRate(0, 20)).toBeNull();
      expect(impliedRate(2000, 0)).toBeNull();
      expect(impliedRate("", 20)).toBeNull();
      expect(impliedRate(2000, "x")).toBeNull();
    });
  });

  describe("isOdometerRollback", () => {
    it("flags a reading below the baseline", () => {
      expect(isOdometerRollback(99000, 100000)).toBe(true);
    });

    it("allows an equal or higher reading", () => {
      expect(isOdometerRollback(100000, 100000)).toBe(false);
      expect(isOdometerRollback(100500, 100000)).toBe(false);
    });

    it("ignores missing / zero inputs", () => {
      expect(isOdometerRollback(0, 100000)).toBe(false);
      expect(isOdometerRollback(100500, 0)).toBe(false);
      expect(isOdometerRollback("", 100000)).toBe(false);
    });
  });
});
