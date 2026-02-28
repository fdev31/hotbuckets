import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { ActionNode as ActionNodeType, ActionType } from "../types";
import { ACTION_TYPES } from "../types";
import { useStore } from "../store";

export function ActionNode({ id, data }: NodeProps<ActionNodeType>) {
  const updateNodeData = useStore((s) => s.updateNodeData);

  return (
    <div className="bg-white rounded-lg shadow-md border-2 border-red-500 min-w-[180px]">
      <div className="bg-red-500 text-white px-2 py-1 rounded-t-md text-xs font-bold flex items-center justify-between">
        <span>Action</span>
        <input
          className="bg-red-600 text-white text-xs rounded px-1 py-0 border-0 w-20 text-right focus:outline-none focus:ring-1 focus:ring-red-300"
          value={data.label}
          onChange={(e) => updateNodeData(id, { label: e.target.value })}
          onClick={(e) => e.stopPropagation()}
        />
      </div>
      <div className="p-2">
        <div className="node-field">
          <label>type</label>
          <select
            value={data.actionType}
            onChange={(e) => updateNodeData(id, { actionType: e.target.value as ActionType })}
          >
            {ACTION_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        {data.actionType === "mirred" && (
          <>
            <div className="node-field">
              <label>direction</label>
              <select
                value={data.direction}
                onChange={(e) =>
                  updateNodeData(id, { direction: e.target.value })
                }
              >
                <option value="egress">egress</option>
                <option value="ingress">ingress</option>
              </select>
            </div>
            <div className="node-field">
              <label>mode</label>
              <select
                value={data.mode}
                onChange={(e) => updateNodeData(id, { mode: e.target.value })}
              >
                <option value="redirect">redirect</option>
                <option value="mirror">mirror</option>
              </select>
            </div>
            <div className="node-field">
              <label>target</label>
              <input
                value={data.target}
                onChange={(e) =>
                  updateNodeData(id, { target: e.target.value })
                }
                placeholder="ifb0"
              />
            </div>
          </>
        )}
        {data.actionType === "police" && (
          <>
            <div className="node-field">
              <label>rate</label>
              <input
                value={data.rate}
                onChange={(e) => updateNodeData(id, { rate: e.target.value })}
                placeholder="1mbit"
              />
            </div>
            <div className="node-field">
              <label>burst</label>
              <input
                value={data.burst}
                onChange={(e) => updateNodeData(id, { burst: e.target.value })}
                placeholder="10k"
              />
            </div>
          </>
        )}
        {data.actionType === "drop" && (
          <div className="text-[10px] text-gray-400 px-1 italic">
            No parameters
          </div>
        )}
      </div>
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-red-500 !w-2.5 !h-2.5"
      />
    </div>
  );
}
