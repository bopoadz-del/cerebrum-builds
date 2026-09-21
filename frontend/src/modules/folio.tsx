/**
 * Folio: operational charges and the operator's own money settings.
 *
 * The brief named no country, currency or tax regime, so this console never
 * invents one: it records the charge against /v1/operations_billing and shows
 * either the computed total in the operator's configured currency, or the named
 * setting that is missing (CURRENCY / TAX_RATE_PERCENT). The arithmetic itself
 * lives in app/formulas.py on the server, not in the browser.
 */
import { useState } from "react";
import { recordFolioCharge } from "../api";

export default function Folio({ token }: { token: string }) {
  const [amount, setAmount] = useState("120.00");
  const [chargeType, setChargeType] = useState("room");
  const [setting, setSetting] = useState("currency");
  const [tax, setTax] = useState("");
  const [folio, setFolio] = useState<Record<string, unknown> | null>(null);
  const [reason, setReason] = useState("");

  async function submit() {
    const result = await recordFolioCharge(token, {
      reference: `folio-${Date.now()}`,
      setting: setting || "currency",
      folio_reference: `FOLIO-${Date.now()}`,
      charge_type: chargeType,
      amount: Number(amount),
      ...(tax ? { tax_rate_percent: Number(tax) } : {}),
    });
    const computed = (result.body && result.body.result && result.body.result.folio) || null;
    setFolio(computed);
    setReason(computed && !computed.computed ? String(computed.reason || "") : "");
  }

  return (
    <section>
      <h3 style={{ fontSize: 14 }}>Folio</h3>
      <input value={amount} onChange={(e) => setAmount(e.target.value)} size={8} />
      <select value={chargeType} onChange={(e) => setChargeType(e.target.value)}>
        <option value="room">room</option>
        <option value="food_and_beverage">food &amp; beverage</option>
        <option value="spa">spa</option>
        <option value="minibar">minibar</option>
      </select>
      <input value={setting} onChange={(e) => setSetting(e.target.value)} placeholder="money setting" size={12} />
      <input value={tax} onChange={(e) => setTax(e.target.value)} placeholder="tax % (optional)" size={12} />
      <button onClick={() => void submit()}>Record charge</button>
      {folio && (
        <p>
          {folio.computed
            ? `${folio.total_amount} ${folio.currency} (tax ${folio.tax})`
            : `no rule computed — ${reason}`}
        </p>
      )}
    </section>
  );
}
