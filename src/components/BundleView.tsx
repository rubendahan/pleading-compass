import { useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type {
  AppData,
  ClaimNode,
  DocumentNode,
} from "@/lib/pleading";
import { COLORS, verdictColor } from "@/lib/pleading";

interface Props {
  data: AppData;
  selectedId: string | null;
  hoveredId: string | null;
  highlightedIds: Set<string>;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
  mode?: "stress" | "coherence";
}

interface BundleItem {
  doc: DocumentNode;
  claims: ClaimNode[];
}

// Build "bundle items" by grouping bundle/legal-overlay claims under the document
// they are sourced from (resolved via the claim's anchor prefix, e.g. "07¶9" → doc:07).
function buildBundle(data: AppData): {
  items: BundleItem[];
  orphanClaims: ClaimNode[];
} {
  const docs = data.nodes.filter((n) => n.layer === "document") as DocumentNode[];
  const docByLabel = new Map(docs.map((d) => [d.label, d]));

  const items = new Map<string, BundleItem>();
  for (const d of docs) items.set(d.id, { doc: d, claims: [] });

  const orphans: ClaimNode[] = [];
  for (const n of data.nodes) {
    if (n.layer !== "claim") continue;
    const c = n as ClaimNode;
    // Pleading-side claims live in the pleading panel, not in the bundle.
    if (c.polarity === "pleading") continue;
    const anchorDoc = c.anchor?.split("¶")[0];
    const doc = anchorDoc ? docByLabel.get(anchorDoc) : undefined;
    if (doc) items.get(doc.id)!.claims.push(c);
    else orphans.push(c);
  }
  return { items: Array.from(items.values()), orphanClaims: orphans };
}

const TYPE_LABEL: Record<string, string> = {
  contract: "Contract",
  correspondence: "Email",
  witness: "Witness statement",
  expert: "Expert report",
  record: "Record",
};

export default function BundleView(props: Props) {
  const { data, onSelect, onHover, selectedId, hoveredId, highlightedIds } = props;
  const built = useMemo(() => buildBundle(data), [data]);

  const [order, setOrder] = useState<string[]>(() => built.items.map((i) => i.doc.id));
  const [activeId, setActiveId] = useState<string | null>(null);

  const itemMap = useMemo(() => {
    const m = new Map<string, BundleItem>();
    for (const i of built.items) m.set(i.doc.id, i);
    return m;
  }, [built]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
  );

  function handleDragStart(e: DragStartEvent) {
    setActiveId(String(e.active.id));
  }
  function handleDragEnd(e: DragEndEvent) {
    setActiveId(null);
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    setOrder((o) => {
      const oldIdx = o.indexOf(String(active.id));
      const newIdx = o.indexOf(String(over.id));
      return arrayMove(o, oldIdx, newIdx);
    });
  }

  const activeItem = activeId ? itemMap.get(activeId) : null;

  return (
    <section
      className="flex h-full flex-col overflow-hidden rounded-sm border"
      style={{ borderColor: COLORS.hair, background: COLORS.panel }}
    >
      <header className="border-b px-5 py-4" style={{ borderColor: COLORS.hair }}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="rule-label">Trial Bundle</div>
            <h2 className="mt-1 font-display text-[20px] italic leading-tight">
              Evidence &amp; coherent claims
            </h2>
            <p className="mt-1.5 text-[12px] leading-relaxed text-ink-dim">
              Each item is a document in the bundle. Drag to re-order. The claims
              nested under each document are the quote-grounded statements drawn
              from it.
            </p>
          </div>
          <div className="hidden shrink-0 flex-col items-end gap-0.5 sm:flex">
            <span className="font-mono text-[9px] uppercase tracking-[0.22em] text-ink-dim">
              items
            </span>
            <span className="font-mono text-[13px]">{built.items.length}</span>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <SortableContext items={order} strategy={verticalListSortingStrategy}>
            <ul className="space-y-2.5">
              {order.map((id, idx) => {
                const item = itemMap.get(id);
                if (!item) return null;
                return (
                  <SortableDocCard
                    key={id}
                    index={idx}
                    item={item}
                    selectedId={selectedId}
                    hoveredId={hoveredId}
                    highlightedIds={highlightedIds}
                    onSelect={onSelect}
                    onHover={onHover}
                  />
                );
              })}
            </ul>
          </SortableContext>
          <DragOverlay>
            {activeItem ? (
              <DocCardInner
                item={activeItem}
                index={order.indexOf(activeItem.doc.id)}
                selectedId={null}
                hoveredId={null}
                highlightedIds={new Set()}
                onSelect={() => {}}
                onHover={() => {}}
                dragging
              />
            ) : null}
          </DragOverlay>
        </DndContext>

        {built.orphanClaims.length > 0 && (
          <div className="mt-6">
            <div className="rule-label mb-2">Without document source</div>
            <ul className="space-y-2">
              {built.orphanClaims.map((c) => (
                <li key={c.id}>
                  <ClaimRow
                    claim={c}
                    selectedId={selectedId}
                    hoveredId={hoveredId}
                    highlightedIds={highlightedIds}
                    onSelect={onSelect}
                    onHover={onHover}
                  />
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

function SortableDocCard(props: {
  item: BundleItem;
  index: number;
  selectedId: string | null;
  hoveredId: string | null;
  highlightedIds: Set<string>;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: props.item.doc.id });

  const style: React.CSSProperties = {
    transform: CSS.Translate.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <li ref={setNodeRef} style={style}>
      <DocCardInner
        {...props}
        dragHandleProps={{ ...attributes, ...listeners }}
      />
    </li>
  );
}

function DocCardInner({
  item,
  index,
  selectedId,
  hoveredId,
  highlightedIds,
  onSelect,
  onHover,
  dragging,
  dragHandleProps,
}: {
  item: BundleItem;
  index: number;
  selectedId: string | null;
  hoveredId: string | null;
  highlightedIds: Set<string>;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
  dragging?: boolean;
  dragHandleProps?: Record<string, unknown>;
}) {
  const isSelected = selectedId === item.doc.id;
  const isHover = hoveredId === item.doc.id;
  const isLinked = highlightedIds.has(item.doc.id);
  const dim =
    (selectedId || hoveredId) &&
    !isSelected &&
    !isHover &&
    !isLinked &&
    !item.claims.some((c) => highlightedIds.has(c.id) || selectedId === c.id);

  const typeLabel = TYPE_LABEL[item.doc.doc_type] ?? item.doc.doc_type;

  return (
    <div
      data-bundle-id={item.doc.id}
      className="rounded-sm border bg-panel"
      style={{
        borderColor: isSelected || isLinked ? COLORS.ink : COLORS.hair,
        background: COLORS.panel,
        opacity: dim ? 0.4 : 1,
        boxShadow: dragging
          ? "0 12px 28px rgba(20,17,13,0.18)"
          : "0 1px 0 rgba(20,17,13,0.03)",
        transition: "opacity 150ms, border-color 120ms",
      }}
      onMouseEnter={() => onHover(item.doc.id)}
      onMouseLeave={() => onHover(null)}
    >
      <div className="flex items-start gap-2 border-b px-3 py-2.5" style={{ borderColor: COLORS.hair }}>
        <button
          type="button"
          className="mt-0.5 cursor-grab touch-none rounded-sm px-1 py-0.5 text-ink-dim hover:bg-panel2 active:cursor-grabbing"
          aria-label="Drag to reorder"
          {...dragHandleProps}
        >
          <svg width="10" height="14" viewBox="0 0 10 14" fill="currentColor" aria-hidden>
            <circle cx="2" cy="2" r="1.2" />
            <circle cx="8" cy="2" r="1.2" />
            <circle cx="2" cy="7" r="1.2" />
            <circle cx="8" cy="7" r="1.2" />
            <circle cx="2" cy="12" r="1.2" />
            <circle cx="8" cy="12" r="1.2" />
          </svg>
        </button>
        <button
          type="button"
          onClick={() => onSelect(item.doc.id)}
          className="flex-1 text-left focus:outline-none"
        >
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-ink-dim">
              {String(index + 1).padStart(2, "0")} · {typeLabel}
            </span>
            <span
              className="rounded-sm border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-widest"
              style={{
                borderColor: COLORS.hair,
                color: COLORS.inkDim,
              }}
            >
              {item.doc.party}
            </span>
          </div>
          <div className="mt-1 font-display text-[14px] leading-snug text-ink">
            {item.doc.title}
          </div>
        </button>
        <span className="font-mono text-[9px] uppercase tracking-widest text-ink-dim">
          doc {item.doc.label}
        </span>
      </div>

      {item.claims.length > 0 ? (
        <ul className="divide-y" style={{ borderColor: COLORS.hair }}>
          {item.claims.map((c) => (
            <li key={c.id} className="border-t" style={{ borderColor: COLORS.hair }}>
              <ClaimRow
                claim={c}
                selectedId={selectedId}
                hoveredId={hoveredId}
                highlightedIds={highlightedIds}
                onSelect={onSelect}
                onHover={onHover}
                inset
              />
            </li>
          ))}
        </ul>
      ) : (
        <div className="px-3 py-2 font-mono text-[10px] italic text-ink-dim">
          No quote-grounded claims drawn from this document.
        </div>
      )}
    </div>
  );
}

function ClaimRow({
  claim,
  selectedId,
  hoveredId,
  highlightedIds,
  onSelect,
  onHover,
  inset,
}: {
  claim: ClaimNode;
  selectedId: string | null;
  hoveredId: string | null;
  highlightedIds: Set<string>;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
  inset?: boolean;
}) {
  const isSelected = selectedId === claim.id;
  const isHover = hoveredId === claim.id;
  const isLinked = highlightedIds.has(claim.id);
  const dim = (selectedId || hoveredId) && !isSelected && !isHover && !isLinked;

  const c =
    claim.polarity === "legal_overlay" ? COLORS.legal : verdictColor(claim.verdict);

  return (
    <button
      type="button"
      onClick={() => onSelect(claim.id)}
      onMouseEnter={() => onHover(claim.id)}
      onMouseLeave={() => onHover(null)}
      className={`block w-full text-left transition focus:outline-none ${
        inset ? "px-3 py-2.5" : "rounded-sm border p-3"
      }`}
      style={{
        background: isSelected
          ? COLORS.panel2
          : isLinked
            ? `${c}10`
            : "transparent",
        borderColor: inset ? undefined : COLORS.hair,
        borderLeft: `3px solid ${c}`,
        opacity: dim ? 0.4 : 1,
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-ink-dim">
          {claim.issue}
          {claim.anchor && <span className="ml-2 text-ink-dim/70">¶ {claim.anchor}</span>}
        </span>
        <span className="flex items-center gap-1">
          {claim.load_bearing && (
            <span
              className="rounded-sm border px-1 py-px font-mono text-[9px] uppercase tracking-widest"
              style={{ borderColor: COLORS.brass, color: COLORS.brass }}
              title="Load-bearing — removing this revives a pleading"
            >
              load-bearing
            </span>
          )}
          <span
            className="verdict-pill"
            style={{ borderColor: c, color: c, background: `${c}12` }}
          >
            {claim.polarity === "legal_overlay" ? "legal" : claim.verdict}
          </span>
        </span>
      </div>
      <p className="mt-1.5 font-display text-[13px] leading-snug text-ink">
        {claim.fulltext}
      </p>
      {claim.quote && (
        <p
          className="mt-1.5 border-l-2 pl-2 font-display text-[12px] italic leading-snug text-ink-dim"
          style={{ borderColor: COLORS.hair }}
        >
          “{truncate(claim.quote, 200)}”
        </p>
      )}
    </button>
  );
}

function truncate(s: string, n: number) {
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}
