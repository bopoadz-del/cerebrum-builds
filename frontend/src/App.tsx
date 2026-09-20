/*
 * Construction Platform — operator console (React source).
 *
 * The image serves the same console from frontend/dist/index.html (built from
 * this file by the Dockerfile's node stage when a toolchain is available) and
 * from app/static/index.html (the prebuilt, dependency-free copy) otherwise.
 * Both drive the live POST/GET routes below; there is no second API.
 *
 * Amounts are in AED. Rates are deployment settings, never assumed: an unset
 * rate is answered as {"ok": false, "setting": "<NAME>"} and shown as such.
 */

import { useCallback, useEffect, useState } from "react";

const PRODUCT_ID = "construction-management";
const TOKEN =
  (typeof window !== "undefined" && (window as any).PLATFORM_TOKEN) ||
  "dev-local-token";

const authHeaders = () => ({
  Authorization: "Bearer " + TOKEN,
  "Content-Type": "application/json",
});

async function call(method: string, path: string, body?: unknown) {
  const resp = await fetch(path, {
    method,
    headers: authHeaders(),
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  let payload: any;
  try {
    payload = await resp.json();
  } catch {
    payload = { ok: false, error: "non-JSON response" };
  }
  return { status: resp.status, body: payload };
}

type MoneySetting = { set: boolean; value: string | null; description: string };

export default function App() {
  const [jobCode, setJobCode] = useState("JOB-1042");
  const [jobName, setJobName] = useState("Al Ain road widening — phase 2");
  const [siteName, setSiteName] = useState("Al Ain sector 4");
  const [progress, setProgress] = useState(35);
  const [snags, setSnags] = useState(4);
  const [valuationNumber, setValuationNumber] = useState("IPC-07");
  const [quantity, setQuantity] = useState(100);
  const [unitRate, setUnitRate] = useState(250);
  const [retentionPercent, setRetentionPercent] = useState<string>("");
  const [vatPercent, setVatPercent] = useState<string>("");
  const [question, setQuestion] = useState("concrete grade");
  const [jobs, setJobs] = useState<any>(null);
  const [valuation, setValuation] = useState<any>(null);
  const [authorityLabel, setAuthorityLabel] = useState("not priced yet");
  const [docAnswer, setDocAnswer] = useState<any>(null);
  const [money, setMoney] = useState<Record<string, MoneySetting>>({});

  const numberOrNull = (raw: string) => (raw.trim() === "" ? null : Number(raw));

  const loadMoney = useCallback(async () => {
    const resp = await call("GET", "/v1/settings/money");
    setMoney(resp.body?.settings?.settings ?? {});
  }, []);

  useEffect(() => {
    loadMoney();
  }, [loadMoney]);

  const saveJob = async () => {
    await call("POST", "/v1/job_and_site_tracking", {
      reference: "JOB-REF-" + Date.now(),
      status: "open",
      job_code: jobCode,
      job_name: jobName,
      site_name: siteName,
      progress_percent: progress,
      snag_open_count: snags,
    });
    setJobs(await call("GET", "/v1/job_and_site_tracking"));
  };

  const priceValuation = async () => {
    const resp = await call("POST", "/v1/formulas/valuation", {
      reference: valuationNumber,
      measured_quantity: quantity,
      unit_rate_aed: unitRate,
      retention_percent: numberOrNull(retentionPercent),
      vat_rate_percent: numberOrNull(vatPercent),
    });
    setValuation(resp);
    const priced = resp.body?.valuation;
    setAuthorityLabel(
      priced
        ? `${priced.authority_label} · ${priced.currency} ${priced.certified_value_aed}`
        : resp.body?.setting
          ? `setting required: ${resp.body.setting}`
          : String(resp.body?.error ?? "refused"),
    );
  };

  const saveValuation = async () => {
    await call("POST", "/v1/commercials_and_valuations", {
      reference: "VAL-REF-" + Date.now(),
      status: "open",
      valuation_number: valuationNumber,
      job_code: jobCode,
      measured_quantity: quantity,
      unit_rate_aed: unitRate,
      gross_value_aed: quantity * unitRate,
      retention_percent: numberOrNull(retentionPercent),
      vat_rate_percent: numberOrNull(vatPercent),
    });
    setValuation(await call("GET", "/v1/commercials_and_valuations"));
  };

  const askDocuments = async () => {
    setDocAnswer(
      await call("GET", "/v1/rag/query?q=" + encodeURIComponent(question)),
    );
  };

  const missing = Object.entries(money)
    .filter(([, meta]) => !meta.set)
    .map(([name]) => name);

  return (
    <main data-product={PRODUCT_ID} style={{ fontFamily: "system-ui", padding: 20 }}>
      <header>
        <h1>Construction Platform</h1>
        <p>civil works · United Arab Emirates · amounts in AED</p>
        <p>
          money settings:{" "}
          {missing.length ? `operator must set ${missing.join(", ")}` : "all rates configured"}
        </p>
      </header>

      <section>
        <h2>Job &amp; site record</h2>
        <label>
          Job code
          <input value={jobCode} onChange={(e) => setJobCode(e.target.value)} />
        </label>
        <label>
          Job name
          <input value={jobName} onChange={(e) => setJobName(e.target.value)} />
        </label>
        <label>
          Site
          <input value={siteName} onChange={(e) => setSiteName(e.target.value)} />
        </label>
        <label>
          Progress %
          <input
            type="number"
            value={progress}
            onChange={(e) => setProgress(Number(e.target.value))}
          />
        </label>
        <label>
          Snags open
          <input
            type="number"
            value={snags}
            onChange={(e) => setSnags(Number(e.target.value))}
          />
        </label>
        <button onClick={saveJob}>Save job record</button>
        <button onClick={async () => setJobs(await call("GET", "/v1/job_and_site_tracking"))}>
          Refresh jobs
        </button>
        <pre>{JSON.stringify(jobs, null, 2)}</pre>
      </section>

      <section>
        <h2>Valuation / interim payment application</h2>
        <label>
          Valuation no.
          <input
            value={valuationNumber}
            onChange={(e) => setValuationNumber(e.target.value)}
          />
        </label>
        <label>
          Measured quantity
          <input type="number" value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} />
        </label>
        <label>
          Unit rate (AED)
          <input type="number" value={unitRate} onChange={(e) => setUnitRate(Number(e.target.value))} />
        </label>
        <label>
          Retention % (blank = deployment setting)
          <input value={retentionPercent} onChange={(e) => setRetentionPercent(e.target.value)} />
        </label>
        <label>
          VAT % (blank = deployment setting)
          <input value={vatPercent} onChange={(e) => setVatPercent(e.target.value)} />
        </label>
        <button onClick={priceValuation}>Price this valuation</button>
        <button onClick={saveValuation}>Save valuation record</button>
        <p>
          Authority: <strong>{authorityLabel}</strong>
        </p>
        <pre>{JSON.stringify(valuation, null, 2)}</pre>
      </section>

      <section>
        <h2>Document Q&amp;A</h2>
        <label>
          Question about BOQs, drawings, method statements or price lists
          <input value={question} onChange={(e) => setQuestion(e.target.value)} />
        </label>
        <button onClick={askDocuments}>Ask the document index</button>
        <pre>{JSON.stringify(docAnswer, null, 2)}</pre>
      </section>

      <section>
        <h2>Money settings</h2>
        <table>
          <tbody>
            {Object.entries(money).map(([name, meta]) => (
              <tr key={name}>
                <td>{name}</td>
                <td>{meta.set ? meta.value : "not set"}</td>
                <td>{meta.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
