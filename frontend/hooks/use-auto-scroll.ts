"use client";

import { useEffect } from "react";
import type { RefObject } from "react";

export function useAutoScroll<T extends HTMLElement>(
  ref: RefObject<T>,
  deps: unknown[]
) {
  useEffect(() => {
    if (!ref.current) return;
    ref.current.scrollTop = ref.current.scrollHeight;
  }, deps);
}
