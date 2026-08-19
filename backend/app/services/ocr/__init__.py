"""OCR / vision receipt parsing (Phase D, roadmap G2/G7/G10).

Currently unimplemented; scaffolded so Phase D has a defined home.
- parser.py  : extract Amount, Liters, Rate, Pump Name, Odometer from
               fuel-receipt + odometer photos
- postprocess.py: confidence scoring, low-confidence -> human-review routing
Stored to `expenses.raw_receipt_text` / `receipt_image_url`.
"""
