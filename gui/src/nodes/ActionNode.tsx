import { useState } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { ActionNode as ActionNodeType, ActionType } from "../types";
import { ACTION_TYPES, ACTION_DESCRIPTIONS } from "../types";
import { useStore } from "../store";
import { ComboInput } from "../components/ComboInput";
import {
  useSpeedSuggestions,
  useDeviceSuggestions,
} from "../hooks/useSuggestions";

export function ActionNode({ id, data }: NodeProps<ActionNodeType>) {
  const updateNodeData = useStore((s) => s.updateNodeData);
  const speedSuggestions = useSpeedSuggestions();
  const deviceSuggestions = useDeviceSuggestions();
  const [showMore, setShowMore] = useState(false);

  // Show expanded if non-default values are set
  const mirredExpanded =
    showMore || data.direction !== "egress" || data.mode !== "redirect";

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
        <div className="text-[10px] text-gray-400 italic px-1 mb-1">
          {ACTION_DESCRIPTIONS[data.actionType]}
        </div>
        {data.actionType === "mirred" && (
          <>
            <div className="node-field">
              <label>target</label>
              <ComboInput
                value={data.target}
                onChange={(val) => updateNodeData(id, { target: val })}
                suggestions={deviceSuggestions}
                placeholder="ifb0"
              />
            </div>
            {mirredExpanded && (
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
              </>
            )}
            <button
              className="text-[10px] text-gray-400 hover:text-gray-600 cursor-pointer px-1"
              onClick={() => setShowMore(!showMore)}
            >
              {mirredExpanded ? "- less" : "+ more"}
            </button>
          </>
        )}
        {data.actionType === "police" && (
          <>
            <div className="node-field">
              <label>rate</label>
              <ComboInput
                value={data.rate}
                onChange={(val) => updateNodeData(id, { rate: val })}
                suggestions={speedSuggestions}
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
        {data.actionType === "skbedit" && (
          <>
            <div className="node-field">
              <label>mark</label>
              <input
                value={data.mark}
                onChange={(e) => updateNodeData(id, { mark: e.target.value })}
                placeholder="0x1"
              />
            </div>
            <div className="node-field">
              <label>priority</label>
              <input
                value={data.priority}
                onChange={(e) => updateNodeData(id, { priority: e.target.value })}
                placeholder="1"
              />
            </div>
            <div className="node-field">
              <label>queue</label>
              <input
                value={data.queueMapping}
                onChange={(e) => updateNodeData(id, { queueMapping: e.target.value })}
                placeholder="0"
              />
            </div>
          </>
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
