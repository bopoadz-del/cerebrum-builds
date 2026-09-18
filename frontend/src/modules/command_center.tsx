// Command centre: the duty manager's live view of the house.
import { useEffect, useState } from "react";

import { checkArrivals } from "../api";

export default function CommandCenter() {
  const [total, setTotal] = useState(0);
  const [arrived, setArrived] = useState(0);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const board = await checkArrivals();
      if (cancelled) return;
      setTotal(board.total || 0);
      setArrived((board.items || []).filter((row) => row.arrived).length);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <article className="command-center">
      <h2>Command centre</h2>
      <dl>
        <dt>Expected arrivals today</dt>
        <dd>{total}</dd>
        <dt>Already arrived</dt>
        <dd>{arrived}</dd>
        <dt>House size</dt>
        <dd>40 rooms</dd>
      </dl>
      <p>
        Counts come from GET /v1/todays_arrivals_board — the same board the
        front desk writes to, scoped to this tenant.
      </p>
    </article>
  );
}
