import { describe, expect, it } from "vitest";
import {
  SETTLEMENT_TRANSFER,
  impliedRate,
  isImageTooLarge,
  isInvalidAmount,
  isOdometerRollback,
  isSupportedImageType,
  parseBulkRows,
  parseReceiptDataUrl,
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

  describe("receipt intake", () => {
    it("isSupportedImageType accepts jpeg/png/webp only", () => {
      expect(isSupportedImageType("image/jpeg")).toBe(true);
      expect(isSupportedImageType("image/PNG")).toBe(true);
      expect(isSupportedImageType("image/webp")).toBe(true);
      expect(isSupportedImageType("image/gif")).toBe(false);
      expect(isSupportedImageType("application/pdf")).toBe(false);
    });

    it("isImageTooLarge estimates the decoded size", () => {
      expect(isImageTooLarge("A".repeat(3_400_000))).toBe(true);
      expect(isImageTooLarge("aGVsbG8=")).toBe(false);
    });

    it("parseReceiptDataUrl splits a data URL", () => {
      expect(parseReceiptDataUrl("data:image/jpeg;base64,AAA")).toEqual({
        image_content_type: "image/jpeg",
        image_base64: "AAA",
      });
      expect(parseReceiptDataUrl("nope")).toBeNull();
    });
  });
});

describe("bulk entry", () => {
  it("parses comma/tab-separated rows", () => {
    const { rows, skipped } = parseBulkRows(
      "FUEL, 4500, 50, 102000\nTOLL, 320\n",
    );
    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({
      exp_type: "FUEL",
      amount: 4500,
      liters: 50,
      odometer: 102000,
    });
    expect(rows[1]).toMatchObject({ exp_type: "TOLL", amount: 320 });
    expect(skipped).toHaveLength(0);
  });

  it("reports skipped lines for unknown types / bad amounts", () => {
    const { rows, skipped } = parseBulkRows(
      "NOPE, 100\nREPAIR, abc\nREPAIR, -5\n",
    );
    expect(rows).toHaveLength(0);
    expect(skipped).toHaveLength(3);
    expect(skipped[0].reason).toContain("unknown type");
    expect(skipped[1].reason).toContain("bad amount");
  });
});
