import { useState, useRef, useEffect, useCallback } from "react";
import { useStore } from "../store";

export interface Suggestion {
  label: string;
  detail?: string;
}

interface ComboInputProps {
  value: string;
  onChange: (val: string) => void;
  suggestions: Suggestion[];
  placeholder?: string;
}

export function ComboInput({
  value,
  onChange,
  suggestions,
  placeholder,
}: ComboInputProps) {
  const variables = useStore((s) => s.variables);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // Determine if the user is typing a variable reference (after `{`)
  const cursorInVar = value.includes("{") && !value.endsWith("}");
  const varPrefix = cursorInVar ? value.slice(value.lastIndexOf("{") + 1) : "";

  // Build the filtered list based on context
  const filtered: Suggestion[] = cursorInVar
    ? variables
        .filter(
          (v) =>
            v.key && v.key.toLowerCase().includes(varPrefix.toLowerCase()),
        )
        .map((v) => ({ label: `{${v.key}}`, detail: v.value }))
    : suggestions.filter(
        (s) =>
          !value || s.label.toLowerCase().includes(value.toLowerCase()),
      );

  // Close on click outside
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Scroll highlighted item into view
  useEffect(() => {
    if (!open || !listRef.current) return;
    const item = listRef.current.children[highlight] as HTMLElement | undefined;
    item?.scrollIntoView({ block: "nearest" });
  }, [highlight, open]);

  // Reset highlight when filtered list changes
  useEffect(() => {
    setHighlight(0);
  }, [filtered.length]);

  const select = useCallback(
    (s: Suggestion) => {
      if (cursorInVar) {
        // Replace everything from the last `{` onward with the selected var
        const before = value.slice(0, value.lastIndexOf("{"));
        onChange(before + s.label);
      } else {
        onChange(s.label);
      }
      setOpen(false);
      inputRef.current?.focus();
    },
    [cursorInVar, value, onChange],
  );

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!open || filtered.length === 0) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlight((h) => (h + 1) % filtered.length);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlight((h) => (h - 1 + filtered.length) % filtered.length);
      } else if (e.key === "Enter") {
        e.preventDefault();
        select(filtered[highlight]);
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    },
    [open, filtered, highlight, select],
  );

  const showDropdown = open && filtered.length > 0;

  return (
    <div ref={wrapperRef} className="relative flex-1 min-w-0">
      <input
        ref={inputRef}
        className="combo-input text-xs border border-gray-300 rounded px-1.5 py-0.5 bg-white w-full"
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        autoComplete="off"
      />
      {showDropdown && (
        <ul
          ref={listRef}
          className="absolute left-0 right-0 top-full mt-0.5 bg-white border border-gray-300 rounded shadow-lg z-50 max-h-32 overflow-y-auto text-xs"
        >
          {filtered.map((s, i) => (
            <li
              key={s.label}
              className={`px-1.5 py-1 cursor-pointer flex items-center justify-between gap-2 ${
                i === highlight ? "bg-blue-100" : "hover:bg-gray-50"
              }`}
              onMouseDown={(e) => {
                e.preventDefault(); // prevent blur
                select(s);
              }}
              onMouseEnter={() => setHighlight(i)}
            >
              <span className="truncate font-medium">{s.label}</span>
              {s.detail && (
                <span className="text-gray-400 truncate text-[10px]">
                  {s.detail}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
