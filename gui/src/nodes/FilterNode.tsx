import { useState } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { FilterNode as FilterNodeType, FilterType } from "../types";
import { FILTER_TYPES, FILTER_DESCRIPTIONS } from "../types";
import { useStore } from "../store";
import { ComboInput } from "../components/ComboInput";
import { useHostSuggestions } from "../hooks/useSuggestions";

export function FilterNode({ id, data }: NodeProps<FilterNodeType>) {
  const updateNodeData = useStore((s) => s.updateNodeData);
  const hostSuggestions = useHostSuggestions();
  const [showMore, setShowMore] = useState(false);

  // Show expanded if protocol is non-default
  const expanded = showMore || (data.protocol !== "ip" && data.protocol !== "");

  const updateIpMatch = (key: string, value: string) => {
    updateNodeData(id, { ipMatches: { ...data.ipMatches, [key]: value } });
  };

  const updateMatchParam = (key: string, value: string) => {
    updateNodeData(id, { matchParams: { ...(data.matchParams || {}), [key]: value } });
  };

  return (
    <div className="bg-white rounded-lg shadow-md border-2 border-purple-500 min-w-[200px]">
      <div className="bg-purple-500 text-white px-2 py-1 rounded-t-md text-xs font-bold flex items-center justify-between">
        <span>Filter</span>
        <input
          className="bg-purple-600 text-white text-xs rounded px-1 py-0 border-0 w-20 text-right focus:outline-none focus:ring-1 focus:ring-purple-300"
          value={data.label}
          onChange={(e) => updateNodeData(id, { label: e.target.value })}
          onClick={(e) => e.stopPropagation()}
        />
      </div>
      <div className="p-2">
        <div className="node-field">
          <label>type</label>
          <select
            value={data.filterType}
            onChange={(e) =>
              updateNodeData(id, {
                filterType: e.target.value as FilterType,
                handle: "",
                ipMatches: {},
                matchParams: {},
              })
            }
          >
            {FILTER_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        <div className="text-[10px] text-gray-400 italic px-1 mb-1">
          {FILTER_DESCRIPTIONS[data.filterType]}
        </div>
        <div className="node-field">
          <label>prio</label>
          <input
            value={data.prio}
            onChange={(e) => updateNodeData(id, { prio: e.target.value })}
            placeholder=""
          />
        </div>
        {expanded && (
          <div className="node-field">
            <label>protocol</label>
            <select
              value={data.protocol}
              onChange={(e) => updateNodeData(id, { protocol: e.target.value })}
            >
              <option value="ip">ip</option>
              <option value="ipv6">ipv6</option>
              <option value="">—</option>
            </select>
          </div>
        )}
        <button
          className="text-[10px] text-gray-400 hover:text-gray-600 cursor-pointer px-1 mb-1"
          onClick={() => setShowMore(!showMore)}
        >
          {expanded ? "- less" : "+ more"}
        </button>
        {data.filterType === "fw" && (
          <div className="node-field">
            <label>handle</label>
            <input
              value={data.handle}
              onChange={(e) => updateNodeData(id, { handle: e.target.value })}
              placeholder="42"
            />
          </div>
        )}
        {data.filterType === "u32" && (
          <>
            <div className="mt-1 mb-0.5 text-[10px] text-gray-400 font-semibold uppercase tracking-wide px-1">
              IP Match
            </div>
            {(["dst", "src"] as const).map((field) => (
              <div className="node-field" key={field}>
                <label>{field}</label>
                <ComboInput
                  value={data.ipMatches[field] || ""}
                  onChange={(val) => updateIpMatch(field, val)}
                  suggestions={hostSuggestions}
                  placeholder="192.168.1.0/24"
                />
              </div>
            ))}
            {(["dport", "sport"] as const).map((field) => (
              <div className="node-field" key={field}>
                <label>{field}</label>
                <input
                  value={data.ipMatches[field] || ""}
                  onChange={(e) => updateIpMatch(field, e.target.value)}
                  placeholder="80"
                />
              </div>
            ))}
          </>
        )}
        {data.filterType === "flower" && (
          <>
            <div className="mt-1 mb-0.5 text-[10px] text-gray-400 font-semibold uppercase tracking-wide px-1">
              Flower Match
            </div>
            {(["dst_ip", "src_ip"] as const).map((field) => (
              <div className="node-field" key={field}>
                <label>{field}</label>
                <ComboInput
                  value={(data.matchParams || {})[field] || ""}
                  onChange={(val) => updateMatchParam(field, val)}
                  suggestions={hostSuggestions}
                  placeholder="192.168.1.0/24"
                />
              </div>
            ))}
            {(["dst_port", "src_port"] as const).map((field) => (
              <div className="node-field" key={field}>
                <label>{field}</label>
                <input
                  value={(data.matchParams || {})[field] || ""}
                  onChange={(e) => updateMatchParam(field, e.target.value)}
                  placeholder="80"
                />
              </div>
            ))}
            <div className="node-field">
              <label>ip_proto</label>
              <select
                value={(data.matchParams || {}).ip_proto || ""}
                onChange={(e) => updateMatchParam("ip_proto", e.target.value)}
              >
                <option value="">--</option>
                <option value="tcp">tcp</option>
                <option value="udp">udp</option>
                <option value="icmp">icmp</option>
              </select>
            </div>
            {(["src_mac", "dst_mac"] as const).map((field) => (
              <div className="node-field" key={field}>
                <label>{field}</label>
                <input
                  value={(data.matchParams || {})[field] || ""}
                  onChange={(e) => updateMatchParam(field, e.target.value)}
                  placeholder="aa:bb:cc:dd:ee:ff"
                />
              </div>
            ))}
            {(["vlan_id", "vlan_prio", "indev"] as const).map((field) => (
              <div className="node-field" key={field}>
                <label>{field}</label>
                <input
                  value={(data.matchParams || {})[field] || ""}
                  onChange={(e) => updateMatchParam(field, e.target.value)}
                  placeholder=""
                />
              </div>
            ))}
          </>
        )}
      </div>
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-purple-500 !w-2.5 !h-2.5"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-purple-500 !w-2.5 !h-2.5"
      />
    </div>
  );
}
