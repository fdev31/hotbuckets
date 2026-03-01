import { useState } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { ClassNode as ClassNodeType, ClassType } from "../types";
import { useStore } from "../store";
import { ComboInput } from "../components/ComboInput";
import { useSpeedSuggestions } from "../hooks/useSuggestions";

export function ClassNode({ id, data }: NodeProps<ClassNodeType>) {
  const updateNodeData = useStore((s) => s.updateNodeData);
  const speedSuggestions = useSpeedSuggestions();
  const [showMore, setShowMore] = useState(false);

  const classType = data.classType || "htb";

  // Show expanded if non-default values are set (htb only)
  const expanded = showMore || !!data.burst || !!data.prio;

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
          <label>type</label>
          <select
            value={classType}
            onChange={(e) => updateNodeData(id, { classType: e.target.value as ClassType })}
          >
            <option value="htb">htb</option>
            <option value="hfsc">hfsc</option>
            <option value="prio">prio</option>
          </select>
        </div>
        {classType === "htb" && (
          <>
            <div className="node-field">
              <label>rate</label>
              <ComboInput
                value={data.rate}
                onChange={(val) => updateNodeData(id, { rate: val })}
                suggestions={speedSuggestions}
                placeholder="10mbit"
              />
            </div>
            <div className="node-field">
              <label>ceil</label>
              <ComboInput
                value={data.ceil}
                onChange={(val) => updateNodeData(id, { ceil: val })}
                suggestions={speedSuggestions}
                placeholder="100mbit"
              />
            </div>
            {expanded && (
              <>
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
              </>
            )}
            <button
              className="text-[10px] text-gray-400 hover:text-gray-600 cursor-pointer px-1"
              onClick={() => setShowMore(!showMore)}
            >
              {expanded ? "- less" : "+ more"}
            </button>
          </>
        )}
        {classType === "hfsc" && (
          <>
            {(["sc", "rt", "ls", "ul"] as const).map((field) => (
              <div className="node-field" key={field}>
                <label>{field}</label>
                <input
                  value={data[field] || ""}
                  onChange={(e) => updateNodeData(id, { [field]: e.target.value })}
                  placeholder={field === "sc" ? "m1 100mbit d 10ms m2 50mbit" : ""}
                />
              </div>
            ))}
          </>
        )}
        {classType === "prio" && (
          <div className="text-[10px] text-gray-400 px-1 italic">
            No parameters (bands configured on qdisc)
          </div>
        )}
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
