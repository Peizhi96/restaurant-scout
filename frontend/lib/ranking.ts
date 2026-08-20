const DEFAULT_CANDIDATE_MIN_COMPLETENESS = 40;

export function candidateMinimumCompleteness(): number {
  const configured = Number(process.env.CANDIDATE_MIN_COMPLETENESS);
  if (!Number.isFinite(configured) || configured < 0 || configured > 100) {
    return DEFAULT_CANDIDATE_MIN_COMPLETENESS;
  }
  return configured;
}
