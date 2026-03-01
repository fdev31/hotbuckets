import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { QdiscNode as QdiscNodeType, QdiscType } from "../types";
import { QDISC_TYPES, QDISC_PARAMS, QDISC_DESCRIPTIONS } from "../types";
import { useStore } from "../store";
import { ComboInput } from "../components/ComboInput";
import { useSpeedSuggestions } from "../hooks/useSuggestions";

export function QdiscNode({ id, data }: NodeProps<QdiscNodeType>) {
  const updateNodeData = useStore((s) => s.updateNodeData);
  const speedSuggestions = useSpeedSuggestions();

  const paramDefs = QDISC_PARAMS[data.qdiscType] || [];

  const updateParam = (key: string, value: string) => {
    updateNodeData(id, { params: { ...data.params, [key]: value } });
  };

  return (
    <div className="bg-white rounded-lg shadow-md border-2 border-green-500 min-w-[200px]">
      <div className="bg-green-500 text-white px-2 py-1 rounded-t-md text-xs font-bold flex items-center justify-between">
        <span>Qdisc</span>
        <input
          className="bg-green-600 text-white text-xs rounded px-1 py-0 border-0 w-24 text-right focus:outline-none focus:ring-1 focus:ring-green-300"
          value={data.label}
          onChange={(e) => updateNodeData(id, { label: e.target.value })}
          onClick={(e) => e.stopPropagation()}
        />
      </div>
      <div className="p-2">
        <div className="node-field">
          <label>type</label>
          <select
            value={data.qdiscType}
            onChange={(e) =>
              updateNodeData(id, {
                qdiscType: e.target.value as QdiscType,
                params: {},
                handle: (e.target.value === "ingress" || e.target.value === "clsact") ? "ffff:" : "",
              })
            }
          >
            {QDISC_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        <div className="text-[10px] text-gray-400 italic px-1 mb-1">
          {QDISC_DESCRIPTIONS[data.qdiscType]}
        </div>
        {(data.qdiscType === "ingress" || data.qdiscType === "clsact") && (
          <div className="node-field">
            <label>handle</label>
            <input
              value={data.handle}
              onChange={(e) => updateNodeData(id, { handle: e.target.value })}
              placeholder="ffff:"
            />
          </div>
        )}
        {paramDefs.map((p) =>
          p.type === "toggle" ? (
            <div className="node-field" key={p.key}>
              <label title={p.description}>{p.label}</label>
              <input
                type="checkbox"
                checked={data.params[p.key] === "true"}
                onChange={(e) =>
                  updateParam(p.key, e.target.checked ? "true" : "")
                }
              />
            </div>
          ) : p.type === "speed" ? (
            <div className="node-field" key={p.key}>
              <label title={p.description}>{p.label}</label>
              <ComboInput
                value={data.params[p.key] || ""}
                onChange={(val) => updateParam(p.key, val)}
                suggestions={speedSuggestions}
                placeholder={p.placeholder}
              />
            </div>
          ) : (
            <div className="node-field" key={p.key}>
              <label title={p.description}>{p.label}</label>
              <input
                value={data.params[p.key] || ""}
                onChange={(e) => updateParam(p.key, e.target.value)}
                placeholder={p.placeholder}
              />
            </div>
          ),
        )}
      </div>
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-green-500 !w-2.5 !h-2.5"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-green-500 !w-2.5 !h-2.5"
      />
    </div>
  );
}
