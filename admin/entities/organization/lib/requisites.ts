// Mirrors src/domains/identity/validation.py so the form can flag a typo before submit;
// the backend re-checks everything and stays the source of truth.

const INN10_WEIGHTS = [2, 4, 10, 3, 5, 9, 4, 6, 8];
const INN12_FIRST_WEIGHTS = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8];
const INN12_SECOND_WEIGHTS = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8];

function checksum(digits: string, weights: number[]): number {
  return (weights.reduce((sum, weight, index) => sum + Number(digits[index]) * weight, 0) % 11) % 10;
}

export function isValidInn(inn: string): boolean {
  if (!/^\d+$/.test(inn)) return false;
  if (inn.length === 10) return checksum(inn, INN10_WEIGHTS) === Number(inn[9]);
  if (inn.length === 12) {
    return (
      checksum(inn, INN12_FIRST_WEIGHTS) === Number(inn[10]) &&
      checksum(inn, INN12_SECOND_WEIGHTS) === Number(inn[11])
    );
  }
  return false;
}

export function isValidOgrn(ogrn: string): boolean {
  if (!/^\d+$/.test(ogrn) || (ogrn.length !== 13 && ogrn.length !== 15)) return false;
  const body = BigInt(ogrn.slice(0, -1));
  const divisor = ogrn.length === 13 ? 11n : 13n;
  return Number((body % divisor) % 10n) === Number(ogrn.at(-1));
}
