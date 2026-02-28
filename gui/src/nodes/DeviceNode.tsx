import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { DeviceNode as DeviceNodeType } from "../types";
import { useStore } from "../store";

export function DeviceNode({ id, data }: NodeProps<DeviceNodeType>) {
  const updateNodeData = useStore((s) => s.updateNodeData);

  return (
    <div className="bg-white rounded-lg shadow-md border-2 border-blue-500 min-w-[180px]">
      <div className="bg-blue-500 text-white px-2 py-1 rounded-t-md text-xs font-bold flex items-center justify-between">
        <span>Device</span>
        <input
          className="bg-blue-600 text-white text-xs rounded px-1 py-0 border-0 w-20 text-right focus:outline-none focus:ring-1 focus:ring-blue-300"
          value={data.label}
          onChange={(e) => updateNodeData(id, { label: e.target.value })}
          onClick={(e) => e.stopPropagation()}
        />
      </div>
      <div className="p-2">
        <div className="node-field">
          <label>dev</label>
          <input
            value={data.dev}
            onChange={(e) => updateNodeData(id, { dev: e.target.value })}
            placeholder="eth0"
          />
        </div>
        <div className="node-field">
          <label>virtual</label>
          <input
            type="checkbox"
            checked={data.virtual}
            onChange={(e) =>
              updateNodeData(id, {
                virtual: e.target.checked,
                devType: e.target.checked ? "ifb" : "",
              })
            }
          />
        </div>
        {data.virtual && (
          <div className="node-field">
            <label>type</label>
            <select
              value={data.devType}
              onChange={(e) => updateNodeData(id, { devType: e.target.value })}
            >
              <option value="ifb">ifb</option>
              <option value="veth">veth</option>
            </select>
          </div>
        )}
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-blue-500 !w-2.5 !h-2.5"
      />
    </div>
  );
}
