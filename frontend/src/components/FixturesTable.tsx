import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import { BOOKMAKERS, type Fixture } from "../types";
import { num, pct, ev, time } from "../utils/format";
import { Badge, Empty } from "./Primitives";
const helper = createColumnHelper<Fixture>();
export function FixturesTable({
  rows,
  market,
}: {
  rows: Fixture[];
  market: string;
}) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: "probability", desc: true },
  ]);
  const columns = useMemo(
    () => [
      helper.accessor("kickoff_utc", {
        header: "Hora",
        cell: (c) => (
          <div className="kickoff">
            {time(c.getValue())}
            <small>{c.row.original.status.replace("_", " ")}</small>
          </div>
        ),
      }),
      helper.accessor("country", { header: "País" }),
      helper.accessor("league_name", { header: "Competición" }),
      helper.accessor((f) => `${f.home_team} ${f.away_team}`, {
        id: "match",
        header: "Partido",
        cell: (c) => (
          <Link
            className="match-cell"
            to={`/match/${c.row.original.fixture_id}`}
          >
            <b>{c.row.original.home_team}</b>
            <span>{c.row.original.away_team}</span>
          </Link>
        ),
      }),
      helper.accessor(
        (f) => f.markets[market]?.model_probability ?? undefined,
        {
          id: "probability",
          header: "Prob. elegida",
          sortUndefined: "last",
          cell: (c) => (
            <strong className="probability">{pct(c.getValue())}</strong>
          ),
        },
      ),
      helper.accessor((f) => f.prediction?.goals.expected_total ?? undefined, {
        id: "expected",
        header: "Goles esp.",
        sortUndefined: "last",
        cell: (c) => num(c.getValue()),
      }),
      ...["OVER_1_5_GOALS", "OVER_2_5_GOALS", "OVER_3_5_GOALS", "BTTS_YES"].map(
        (m) =>
          helper.accessor((f) => f.prediction?.goals.probabilities[m], {
            id: m,
            header: m === "BTTS_YES" ? "BTTS" : `O${m.split("_")[1]}.5`,
            sortUndefined: "last",
            cell: (c) => pct(c.getValue()),
          }),
      ),
      helper.accessor(
        (f) => f.prediction?.corners.expected_total ?? undefined,
        {
          id: "expected_corners",
          header: "Córners esp.",
          sortUndefined: "last",
          cell: (c) => num(c.getValue()),
        },
      ),
      ...["OVER_8_5_CORNERS", "OVER_9_5_CORNERS", "OVER_10_5_CORNERS"].map(
        (m) =>
          helper.accessor((f) => f.prediction?.corners.probabilities[m], {
            id: m,
            header: `C O${m.split("_")[1]}.5`,
            sortUndefined: "last",
            cell: (c) => pct(c.getValue()),
          }),
      ),
      ...BOOKMAKERS.map((book) =>
        helper.accessor(
          (f) => f.markets[market]?.quotes[book]?.decimal_odds ?? undefined,
          {
            id: book,
            header: book,
            sortUndefined: "last",
            cell: (c) => {
              const q = c.row.original.markets[market]?.quotes[book];
              return (
                <span
                  className={q?.stale ? "stale-text" : ""}
                  title={
                    q
                      ? `${q.source_label} · ${q.timestamp}${q.is_delayed ? " · Delayed" : ""}`
                      : "No disponible"
                  }
                >
                  {num(c.getValue())}
                  {q?.stale && <small>STALE</small>}
                  {q?.is_manual && <small>MANUAL</small>}
                </span>
              );
            },
          },
        ),
      ),
      helper.accessor((f) => f.markets[market]?.best_odds ?? undefined, {
        id: "best",
        header: "Mejor cuota",
        sortUndefined: "last",
        cell: (c) => (
          <span className="best-cell">
            {num(c.getValue())}
            <small>
              {c.row.original.markets[market]?.best_bookmaker ?? "—"}
            </small>
          </span>
        ),
      }),
      helper.accessor((f) => f.markets[market]?.fair_odds ?? undefined, {
        id: "fair",
        header: "Cuota justa",
        sortUndefined: "last",
        cell: (c) => num(c.getValue()),
      }),
      helper.accessor((f) => f.markets[market]?.best?.edge ?? undefined, {
        id: "edge",
        header: "Edge",
        sortUndefined: "last",
        cell: (c) => pct(c.getValue(), true),
      }),
      helper.accessor((f) => f.markets[market]?.best?.ev ?? undefined, {
        id: "ev",
        header: "EV",
        sortUndefined: "last",
        cell: (c) => ev(c.getValue()),
      }),
      helper.accessor((f) => f.prediction?.confidence[market]?.score, {
        id: "confidence",
        header: "Confianza",
        sortUndefined: "last",
        cell: (c) => (
          <Badge grade={c.row.original.prediction?.confidence[market]} />
        ),
      }),
      helper.accessor(
        (f) =>
          (market.endsWith("CORNERS")
            ? f.prediction?.corner_quality
            : f.prediction?.quality
          )?.score,
        {
          id: "quality",
          header: "Calidad",
          sortUndefined: "last",
          cell: (c) => (
            <Badge
              grade={
                market.endsWith("CORNERS")
                  ? c.row.original.prediction?.corner_quality
                  : c.row.original.prediction?.quality
              }
            />
          ),
        },
      ),
    ],
    [market],
  );
  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });
  if (!rows.length)
    return (
      <Empty
        title="No hay partidos en esta vista"
        text="Prueba otra fecha o amplía los filtros. Los partidos sin datos suficientes aparecen con sus probabilidades vacías."
      />
    );
  return (
    <div className="table-scroll">
      <table className="fixtures-table">
        <thead>
          {table.getHeaderGroups().map((group) => (
            <tr key={group.id}>
              {group.headers.map((header) => (
                <th key={header.id}>
                  <button onClick={header.column.getToggleSortingHandler()}>
                    {flexRender(
                      header.column.columnDef.header,
                      header.getContext(),
                    )}
                    {header.column.getIsSorted() === "desc" ? (
                      <ArrowDown size={11} />
                    ) : header.column.getIsSorted() === "asc" ? (
                      <ArrowUp size={11} />
                    ) : (
                      <ArrowUpDown size={11} />
                    )}
                  </button>
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
