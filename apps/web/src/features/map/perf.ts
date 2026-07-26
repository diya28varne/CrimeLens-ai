/** Round bbox coords so tiny pan jitter does not retrigger fetches. */
export function normalizeBbox(bbox: string, digits = 4): string {
  return bbox
    .split(",")
    .map((part) => {
      const n = Number(part);
      return Number.isFinite(n) ? n.toFixed(digits) : part.trim();
    })
    .join(",");
}

export function createDebouncedRunner(delayMs: number) {
  let timer: ReturnType<typeof setTimeout> | null = null;

  return {
    run(fn: () => void, immediate = false) {
      if (timer != null) {
        clearTimeout(timer);
        timer = null;
      }
      if (immediate) {
        fn();
        return;
      }
      timer = setTimeout(() => {
        timer = null;
        fn();
      }, delayMs);
    },
    cancel() {
      if (timer != null) {
        clearTimeout(timer);
        timer = null;
      }
    },
  };
}
