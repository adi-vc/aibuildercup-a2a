import { describe, expect, it } from 'vitest';
import { factMark, factsInBeatOrder } from './factMark';

describe('factMark', () => {
  it('formats the fixture values for a tile', () => {
    expect(factMark({ value: '30', unit: 'cm' })).toBe('30 cm');
    expect(factMark({ value: '129900', unit: 'INR' })).toBe('₹1,29,900');
    expect(factMark({ value: '4h30m', unit: '' })).toBe('4 h 30 m');
    expect(factMark({ value: '3yr/30000km', unit: '' })).toBe('3 years');
    expect(factMark({ value: '8.2', unit: 's' })).toBe('8.2 s');
  });
});

describe('factsInBeatOrder', () => {
  it('follows the beats, then any facts no beat cites, each once', () => {
    const beats = [{ fact_ids: [] }, { fact_ids: ['b', 'a'] }, { fact_ids: ['a', 'c'] }];
    expect(factsInBeatOrder(beats, { a: 1, b: 1, c: 1, z: 1 })).toEqual(['b', 'a', 'c', 'z']);
  });
});
