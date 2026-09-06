// Pure, framework-free helpers for the expense-entry forms. Kept isolated from
// React so they can be unit-tested under Vitest without a DOM, and shared
// between the manager quick-entry page and the trip-detail form.

// The closing entry type whose amount is recomputed server-side (never taken
// from the client). Mirrors backend/services/audit/cash.py::SETTLEMENT_TRANSFER_TYPE.
export const SETTLEMENT_TRANSFER = "SETTLEMENT_TRANSFER";

// Audit D-1 (client mirror): a non-positive amount is never a legitimate
// expense line. The backend rejects it with INVALID_AMOUNT; surfacing the same
// gate here keeps WhatsApp/direct-API and the manual form in lockstep. The
// SETTLEMENT_TRANSFER type is exempt because its amount is server-computed.
export function isInvalidAmount(amount, expType) {
  if (expType === SETTLEMENT_TRANSFER) return false;
  const amt = Number(amount);
  if (!Number.isFinite(amt)) return true;
  return amt <= 0;
}

// Implied per-litre rate for a FUEL/DEF entry: amount ÷ litres, rounded to
// paise precision (2 dp). Returns null when it can't be derived (missing or
// non-positive term). This is the client-side counterpart to the rules
// engine's ₹/L cross-check.
export function impliedRate(amount, liters) {
  const amt = Number(amount);
  const ltr = Number(liters);
  if (!Number.isFinite(amt) || !Number.isFinite(ltr)) return null;
  if (amt <= 0 || ltr <= 0) return null;
  return Math.round((amt / ltr) * 100) / 100;
}

// An odometer reading below the trip's last known reading is a rollback. The
// backend silently floors odometer at the last value (GREATEST); this lets the
// form flag the mistake inline instead.
export function isOdometerRollback(odometer, baseline) {
  const odo = Number(odometer);
  const base = Number(baseline);
  if (!Number.isFinite(odo) || !Number.isFinite(base)) return false;
  if (odo <= 0 || base <= 0) return false;
  return odo < base;
}

// ---- Receipt photo intake (mirrors backend api/v1/expenses.py) --------------
export const MAX_RECEIPT_BYTES = 2_500_000;
export const RECEIPT_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

// True when the MIME type is an allowed receipt image.
export function isSupportedImageType(contentType) {
  return RECEIPT_IMAGE_TYPES.has(String(contentType || "").toLowerCase());
}

// Estimated decoded byte size of a base64 string (x3/4, ignoring padding).
export function isImageTooLarge(base64) {
  const b = String(base64 || "");
  return Math.floor((b.length * 3) / 4) > MAX_RECEIPT_BYTES;
}

// Split a FileReader data URL (data:<type>;base64,<data>) into the fields the
// backend expects: { image_content_type, image_base64 }. Returns null when the
// string is not a valid image data URL.
export function parseReceiptDataUrl(dataUrl) {
  const match = /^data:(image\/[a-z0-9.+-]+);base64,(.*)$/i.exec(
    String(dataUrl || ""),
  );
  if (!match) return null;
  return { image_content_type: match[1].toLowerCase(), image_base64: match[2] };
}
