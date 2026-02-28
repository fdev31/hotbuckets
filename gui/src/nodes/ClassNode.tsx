import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { ClassNode as ClassNodeType } from "../types";
import { useStore } from "../store";

export function ClassNode({ id, data }: NodeProps<ClassNodeType>) {
  const updateNodeData = useStore((s) => s.updateNodeData);

  return (
    <div className="bg-white rounded-lg shadow-md border-2 border-amber-500 min-w-[180px]">
      <div className="bg-amber-500 text-white px-2 py-1 rounded-t-md text-xs font-bold flex items-center justify-between">
        <span>Class</span>
        <input
          className="bg-amber-600 text-white text-xs rounded px-1 py-0 border-0 w-20 text-right focus:outline-none focus:ring-1 focus:ring-amber-300"
          value={data.label}
          onChange={(e) => updateNodeData(id, { label: e.target.value })}
          onClick={(e) => e.stopPropagation()}
        />
      </div>
      <div className="p-2">
        <div className="node-field">
          <label>rate</label>
          <input
            value={data.rate}
            onChange={(e) => updateNodeData(id, { rate: e.target.value })}
            placeholder="10mbit"
          />
        </div>
        <div className="node-field">
          <label>ceil</label>
          <input
            value={data.ceil}
            onChange={(e) => updateNodeData(id, { ceil: e.target.value })}
            placeholder="100mbit"
          />
        </div>
        <div className="node-field">
          <label>burst</label>
          <input
            value={data.burst}
            onChange={(e) => updateNodeData(id, { burst: e.target.value })}
            placeholder=""
          />
        </div>
        <div className="node-field">
          <label>prio</label>
          <input
            value={data.prio}
            onChange={(e) => updateNodeData(id, { prio: e.target.value })}
            placeholder=""
          />
        </div>
      </div>
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-amber-500 !w-2.5 !h-2.5"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-amber-500 !w-2.5 !h-2.5"
      />
    </div>
  );
}
