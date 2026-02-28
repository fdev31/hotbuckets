import { useMemo, useState } from "react";
import { useStore } from "../store";
import { exportToml } from "../export/toml";

export function TomlPreview() {
  const nodes = useStore((s) => s.nodes);
  const edges = useStore((s) => s.edges);
  const variables = useStore((s) => s.variables);
  const speeds = useStore((s) => s.speeds);
  const hosts = useStore((s) => s.hosts);
  const tc = useStore((s) => s.tc);
  const unit = useStore((s) => s.unit);

  const [copied, setCopied] = useState(false);

  const toml = useMemo(
    () =>
      exportToml({ nodes, edges, variables, speeds, hosts, tc, unit }),
    [nodes, edges, variables, speeds, hosts, tc, unit],
  );

  const handleCopy = async () => {
    await navigator.clipboard.writeText(toml);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleDownload = () => {
    const blob = new Blob([toml], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "hotbuckets.toml";
    a.click();
    URL.revokeObjectURL(url);
  };

  const isEmpty =
    nodes.length === 0 &&
    variables.length === 0 &&
    speeds.length === 0 &&
    hosts.length === 0;

  return (
    <div className="w-80 bg-gray-50 border-l border-gray-200 flex flex-col">
      <div className="p-3 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-xs font-bold text-gray-700 uppercase tracking-wide">
          TOML Output
        </h2>
        <div className="flex gap-1.5">
          <button
            onClick={handleCopy}
            disabled={isEmpty}
            className="text-xs px-2 py-0.5 rounded border border-gray-300 bg-white hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
          <button
            onClick={handleDownload}
            disabled={isEmpty}
            className="text-xs px-2 py-0.5 rounded border border-gray-300 bg-white hover:bg-gray-100 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            Download
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        {isEmpty ? (
          <div className="text-xs text-gray-400 italic">
            Add nodes to the canvas to generate TOML configuration.
          </div>
        ) : (
          <pre className="text-[11px] leading-relaxed text-gray-800 whitespace-pre-wrap font-mono">
            {toml}
          </pre>
        )}
      </div>
    </div>
  );
}
