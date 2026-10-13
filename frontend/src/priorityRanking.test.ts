import { describe, expect, it } from "vitest";

import {
  assignPriority,
  EMPTY_PRIORITY_RANKING,
  isCompleteRanking,
  priorityState,
} from "./priorityRanking";
import type { PriorityRanking } from "./types";

const complete: PriorityRanking = {
  never_stop_working: 1,
  lowest_cost: 2,
  fast_under_load: 3,
  protect_information: 4,
};

describe("assignPriority", () => {
  it("assigns a free position without touching the others", () => {
    const result = assignPriority(EMPTY_PRIORITY_RANKING, "lowest_cost", 2);

    expect(result).toEqual({ ...EMPTY_PRIORITY_RANKING, lowest_cost: 2 });
  });

  it("swaps positions when another priority already holds it", () => {
    const result = assignPriority(complete, "protect_information", 1);

    expect(result).toEqual({
      never_stop_working: 4,
      lowest_cost: 2,
      fast_under_load: 3,
      protect_information: 1,
    });
  });

  it("leaves the previous holder without position when the new one had none", () => {
    const result = assignPriority(
      { ...EMPTY_PRIORITY_RANKING, never_stop_working: 1 },
      "lowest_cost",
      1,
    );

    expect(result).toEqual({ ...EMPTY_PRIORITY_RANKING, lowest_cost: 1 });
  });

  it("clears a position with null and never mutates the input", () => {
    const result = assignPriority(complete, "lowest_cost", null);

    expect(result.lowest_cost).toBeNull();
    expect(complete.lowest_cost).toBe(2);
  });

  it("keeps every assigned position unique after any assignment", () => {
    let ranking = complete;
    for (const [key, position] of [
      ["lowest_cost", 1],
      ["fast_under_load", 1],
      ["never_stop_working", 3],
    ] as const) {
      ranking = assignPriority(ranking, key, position);
      const positions = Object.values(ranking).filter((value) => value !== null);
      expect(new Set(positions).size).toBe(positions.length);
    }
  });
});

describe("priorityState", () => {
  it("distinguishes empty, partial, detected and edited orders", () => {
    expect(priorityState(EMPTY_PRIORITY_RANKING, EMPTY_PRIORITY_RANKING)).toBe("empty");
    expect(priorityState({ ...EMPTY_PRIORITY_RANKING, lowest_cost: 1 }, complete)).toBe("partial");
    expect(priorityState(complete, complete)).toBe("detected");
    expect(priorityState(complete, EMPTY_PRIORITY_RANKING)).toBe("edited");
  });

  it("only treats four positions as a complete order", () => {
    expect(isCompleteRanking(complete)).toBe(true);
    expect(isCompleteRanking({ ...complete, protect_information: null })).toBe(false);
  });
});
