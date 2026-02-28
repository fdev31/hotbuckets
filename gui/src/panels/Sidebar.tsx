import { type DragEvent, useState, useCallback } from "react";
import { useStore } from "../store";
import { NODE_COLORS, type KeyValueEntry } from "../types";
import { BUILTIN_WORKSPACES } from "../builtins";

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

// ── Relative time formatter ─────────────────────────────────────

function timeAgo(ts: number): string {
  const sec = Math.floor((Date.now() - ts) / 1000);
  if (sec < 60) return "just now";
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hrs = Math.floor(min / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

// ── Workspace panel ─────────────────────────────────────────────

function WorkspacePanel() {
  const activeWorkspaceId = useStore((s) => s.activeWorkspaceId);
  const activeWorkspaceName = useStore((s) => s.activeWorkspaceName);
  const setActiveWorkspaceName = useStore((s) => s.setActiveWorkspaceName);
  const saveWorkspace = useStore((s) => s.saveWorkspace);
  const loadWorkspace = useStore((s) => s.loadWorkspace);
  const deleteWorkspace = useStore((s) => s.deleteWorkspace);
  const newWorkspace = useStore((s) => s.newWorkspace);
  const listWorkspaces = useStore((s) => s.listWorkspaces);

  // Force re-render after save/delete/load so the list updates
  const [, setTick] = useState(0);
  const refresh = useCallback(() => setTick((t) => t + 1), []);

  const workspaces = listWorkspaces();

  const handleSave = () => {
    saveWorkspace();
    refresh();
  };

  const handleNew = () => {
    newWorkspace();
    refresh();
  };

  const handleLoad = (id: string) => {
    loadWorkspace(id);
    refresh();
  };

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    deleteWorkspace(id);
    refresh();
  };

  return (
    <div className="p-3 border-b border-gray-200">
      <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-2">
        Workspace
      </h2>

      {/* Active workspace name */}
      <input
        className="text-xs border border-gray-300 rounded px-1.5 py-1 w-full bg-white focus:outline-none focus:ring-1 focus:ring-blue-400 mb-1.5"
        value={activeWorkspaceName}
        onChange={(e) => setActiveWorkspaceName(e.target.value)}
        placeholder="Workspace name"
      />

      {/* Action buttons */}
      <div className="flex gap-1.5 mb-2">
        <button
          onClick={handleSave}
          className="flex-1 text-xs px-2 py-1 rounded border border-blue-400 bg-blue-500 text-white hover:bg-blue-600 cursor-pointer"
        >
          Save
        </button>
        <button
          onClick={handleNew}
          className="flex-1 text-xs px-2 py-1 rounded border border-gray-300 bg-white text-gray-700 hover:bg-gray-100 cursor-pointer"
        >
          New
        </button>
      </div>

      {/* Saved workspace list */}
      {workspaces.length > 0 && (
        <div className="max-h-36 overflow-y-auto space-y-0.5">
          {workspaces.map((ws) => (
            <div
              key={ws.id}
              onClick={() => handleLoad(ws.id)}
              className={`group flex items-center justify-between px-2 py-1 rounded cursor-pointer text-xs transition-colors ${
                ws.id === activeWorkspaceId
                  ? "bg-blue-50 border border-blue-300"
                  : "hover:bg-gray-100 border border-transparent"
              }`}
            >
              <div className="min-w-0 flex-1">
                <div className="font-medium text-gray-800 truncate">
                  {ws.name}
                </div>
                <div className="text-[10px] text-gray-400">
                  {timeAgo(ws.savedAt)}
                </div>
              </div>
              <button
                onClick={(e) => handleDelete(e, ws.id)}
                className="text-gray-300 hover:text-red-500 ml-1 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
                title="Delete workspace"
              >
                x
              </button>
            </div>
          ))}
        </div>
      )}

      {workspaces.length === 0 && (
        <div className="text-[10px] text-gray-400 italic">
          No saved workspaces
        </div>
      )}

      {/* Built-in examples */}
      <div className="mt-3 pt-2 border-t border-gray-200">
        <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide">
          Examples
        </span>
        <div className="mt-1 space-y-0.5">
          {BUILTIN_WORKSPACES.map((bw) => (
            <div
              key={bw.id}
              onClick={() => handleLoad(bw.id)}
              className="px-2 py-1 rounded cursor-pointer text-xs hover:bg-gray-100 border border-transparent transition-colors"
            >
              <div className="font-medium text-gray-700">{bw.name}</div>
              <div className="text-[10px] text-gray-400">
                {bw.description}
              </div>
            </div>
          ))}
        </div>
      </div>
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
      {/* Workspace save/load */}
      <WorkspacePanel />

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
