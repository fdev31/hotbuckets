import { useMemo } from "react";
import { useStore } from "../store";
import type { Suggestion } from "../components/ComboInput";
import type { DeviceData } from "../types";

/** Speed alias suggestions from the sidebar [speeds] config. */
export function useSpeedSuggestions(): Suggestion[] {
  const speeds = useStore((s) => s.speeds);
  return useMemo(
    () =>
      speeds
        .filter((s) => s.key)
        .map((s) => ({ label: s.key, detail: s.value })),
    [speeds],
  );
}

/** Host alias suggestions from the sidebar [hosts] config. */
export function useHostSuggestions(): Suggestion[] {
  const hosts = useStore((s) => s.hosts);
  return useMemo(
    () =>
      hosts
        .filter((h) => h.key)
        .map((h) => ({ label: h.key, detail: h.value })),
    [hosts],
  );
}

/** Device label suggestions from all DeviceNode instances on the canvas. */
export function useDeviceSuggestions(): Suggestion[] {
  const nodes = useStore((s) => s.nodes);
  return useMemo(
    () =>
      nodes
        .filter((n) => n.type === "device")
        .map((n) => {
          const d = n.data as DeviceData;
          return { label: d.label, detail: d.dev };
        })
        .filter((s) => s.label),
    [nodes],
  );
}
