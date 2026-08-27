// Mirrors `_MIN_COVERAGE_FOR_SUFFICIENT_EVIDENCE` in
// backend/app/services/investment_scoring_service.py -- one of three
// fixed conditions gating a composite score, and the only one directly
// expressible as a coverage percentage for the UI's meters/thresholds.
export const COVERAGE_THRESHOLD_PERCENT = 50;
