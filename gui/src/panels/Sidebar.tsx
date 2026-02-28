import { type DragEvent } from "react";
import { useStore } from "../store";
import { NODE_COLORS, type KeyValueEntry } from "../types";

const NODE_PALETTE = [
  { type: "device", label: "Device", desc: "Network interface" },
  { type: "qdisc", label: "Qdisc", desc: "Queuing discipline" },
  { type: "class", label: "Class", desc: "Traffic class" },
  { type: "filter", label: "Filter", desc: "Packet matcher" },
  { type: "action", label: "Action", desc: "Filter action" },
] as const;

function onDragStart(event: DragEvent, nodeType: string) {
  event.dataTransfer.setData("application/hotbuckets-node", nodeType);
  event.dataTransfer.effectAllowed = "move";
}

// ── Key-value pair editor ───────────────────────────────────────

function KVEditor({
  label,
  entries,
  onChange,
}: {
  label: string;
  entries: KeyValueEntry[];
  onChange: (entries: KeyValueEntry[]) => void;
}) {
  const update = (i: number, field: "key" | "value", val: string) => {
    const next = entries.map((e, j) =>
      j === i ? { ...e, [field]: val } : e,
    );
    onChange(next);
  };

  const add = () => onChange([...entries, { key: "", value: "" }]);

  const remove = (i: number) => onChange(entries.filter((_, j) => j !== i));

  return (
    <div className="mb-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          {label}
        </span>
        <button
          onClick={add}
          className="text-xs text-blue-500 hover:text-blue-700 cursor-pointer"
        >
          + Add
        </button>
      </div>
      {entries.length === 0 && (
        <div className="text-[10px] text-gray-400 italic">None</div>
      )}
      {entries.map((entry, i) => (
        <div key={i} className="flex items-center gap-1 mb-1">
          <input
            className="text-xs border border-gray-300 rounded px-1.5 py-0.5 w-20 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
            value={entry.key}
            onChange={(e) => update(i, "key", e.target.value)}
            placeholder="name"
          />
          <span className="text-gray-400 text-xs">=</span>
          <input
            className="text-xs border border-gray-300 rounded px-1.5 py-0.5 flex-1 min-w-0 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
            value={entry.value}
            onChange={(e) => update(i, "value", e.target.value)}
            placeholder="value"
          />
          <button
            onClick={() => remove(i)}
            className="text-gray-400 hover:text-red-500 text-xs cursor-pointer"
          >
            x
          </button>
        </div>
      ))}
    </div>
  );
}

// ── Sidebar ─────────────────────────────────────────────────────

export function Sidebar() {
  const variables = useStore((s) => s.variables);
  const speeds = useStore((s) => s.speeds);
  const hosts = useStore((s) => s.hosts);
  const tc = useStore((s) => s.tc);
  const unit = useStore((s) => s.unit);
  const setVariables = useStore((s) => s.setVariables);
  const setSpeeds = useStore((s) => s.setSpeeds);
  const setHosts = useStore((s) => s.setHosts);
  const setTc = useStore((s) => s.setTc);
  const setUnit = useStore((s) => s.setUnit);

  return (
    <div className="w-56 bg-gray-50 border-r border-gray-200 flex flex-col overflow-y-auto">
      {/* Node palette */}
      <div className="p-3 border-b border-gray-200">
        <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">
          Nodes
        </h2>
        <div className="space-y-1.5">
          {NODE_PALETTE.map(({ type, label, desc }) => (
            <div
              key={type}
              draggable
              onDragStart={(e) => onDragStart(e, type)}
              className="flex items-center gap-2 px-2 py-1.5 rounded-md border border-gray-200 bg-white cursor-grab active:cursor-grabbing hover:shadow-sm transition-shadow"
            >
              <div
                className="w-3 h-3 rounded-sm shrink-0"
                style={{ backgroundColor: NODE_COLORS[type] }}
              />
              <div>
                <div className="text-xs font-medium text-gray-800">
                  {label}
                </div>
                <div className="text-[10px] text-gray-400">{desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Global config */}
      <div className="p-3 flex-1">
        <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">
          Config
        </h2>

        {/* tc path */}
        <div className="mb-3">
          <label className="text-xs text-gray-500 block mb-0.5">
            tc path
          </label>
          <input
            className="text-xs border border-gray-300 rounded px-1.5 py-0.5 w-full bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
            value={tc}
            onChange={(e) => setTc(e.target.value)}
            placeholder="tc"
          />
        </div>

        {/* unit */}
        <div className="mb-3">
          <label className="text-xs text-gray-500 block mb-0.5">
            unit
          </label>
          <input
            className="text-xs border border-gray-300 rounded px-1.5 py-0.5 w-full bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
            placeholder="mbit"
          />
        </div>

        <KVEditor
          label="Variables"
          entries={variables}
          onChange={setVariables}
        />
        <KVEditor label="Speeds" entries={speeds} onChange={setSpeeds} />
        <KVEditor label="Hosts" entries={hosts} onChange={setHosts} />
      </div>
    </div>
  );
}
