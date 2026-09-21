// One typed client over the platform's own routes. The token is the operator's
// bearer token: tenancy is resolved server-side from it, never from the body.

export type Authority = {
  precedence: string;
  layer: string | null;
  label: string;
  claim_labels?: unknown[];
  divergence?: unknown[];
};

export type CapabilityField = {
  name: string;
  type?: string;
  required?: boolean;
  allowed_values?: unknown[];
};

export type Capability = {
  capability_id: string;
  title: string;
  description: string;
  fields: CapabilityField[];
  fields_required: string[];
};

export type CapabilityRow = Record<string, unknown> & { id?: number };

export type Answer<T> = { status: number; ok: boolean; payload: T & { authority?: Authority; error?: string } };

export class Api {
  constructor(private readonly token: string) {}

  private headers(): Record<string, string> {
    return { Authorization: `Bearer ${this.token}`, "Content-Type": "application/json" };
  }

  private async call<T>(method: string, path: string, body?: unknown): Promise<Answer<T>> {
    const response = await fetch(path, {
      method,
      headers: this.headers(),
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    let payload: unknown = {};
    try {
      payload = await response.json();
    } catch {
      payload = { error: "the platform did not answer JSON" };
    }
    const record = payload as T & { authority?: Authority; error?: string; ok?: boolean };
    return { status: response.status, ok: response.ok && record.ok !== false, payload: record };
  }

  whoami() {
    return this.call<{ tenant: { tenant_id: string; name: string } }>("GET", "/v1/auth/whoami");
  }

  capabilities() {
    return this.call<{ capabilities: Capability[] }>("GET", "/v1/capabilities");
  }

  connectors() {
    return this.call<{ connectors: { connector: string; mode: string; blocks_unavailable: string[] }[] }>(
      "GET",
      "/v1/connectors",
    );
  }

  postRecord(capability: string, record: Record<string, unknown>) {
    return this.call<{ id: number; stored: CapabilityRow; result: unknown }>(
      "POST",
      `/v1/${capability}`,
      record,
    );
  }

  listRecords(capability: string) {
    return this.call<{ items: CapabilityRow[]; count: number }>("GET", `/v1/${capability}`);
  }

  importLeads(text: string, campaign: string, projectTag: string) {
    return this.call<{ accepted: number; refused: unknown[]; queued: CapabilityRow[] }>(
      "POST",
      "/v1/leads/import",
      { text, campaign, project_tag: projectTag, file_name: "console.csv" },
    );
  }

  dialQueue(campaign: string) {
    return this.call<{ cap: { result: number }; queue_depth: number; queued: CapabilityRow[] }>(
      "GET",
      `/v1/dial-queue?campaign=${encodeURIComponent(campaign)}`,
    );
  }

  ingest(text: string, projectTag: string) {
    return this.call<{ document_id: string; chunks: number }>("POST", "/v1/rag/ingest", {
      text,
      project_tag: projectTag,
      title: "console sheet",
      certified: true,
    });
  }

  ground(projectTag: string, question: string) {
    return this.call<{ answer: string | null; withheld: boolean; citations: string[] }>(
      "POST",
      "/v1/rag/ground",
      { project_tag: projectTag, question },
    );
  }

  ask(text: string, projectTag: string, language: string) {
    return this.call<{ say: string; withheld: boolean; outcome: string | null }>(
      "POST",
      "/v1/voice/gather",
      { SpeechResult: text, project_tag: projectTag, language },
    );
  }

  qualify(callSid: string, outcome: string, transcript: string, projectTag: string) {
    return this.call<{ stored: CapabilityRow; result: { next_action?: string } }>(
      "POST",
      "/v1/qualification_and_broker_summary",
      {
        call_sid: callSid,
        outcome,
        transcript,
        project_tag: projectTag,
        language: "en",
        reference: `console-${Date.now()}`,
        status: "open",
      },
    );
  }

  transfer(callSid: string, qualifiedOutcome: string, projectTag: string) {
    return this.call<{ stored: CapabilityRow; result: { decision?: string } }>("POST", "/v1/warm_transfer", {
      call_sid: callSid,
      outcome: "transferred",
      qualified_outcome: qualifiedOutcome,
      project_tag: projectTag,
      reference: `console-${Date.now()}`,
      status: "open",
    });
  }

  dashboard(campaign: string) {
    return this.call<{
      metrics: Record<string, number | Record<string, number>>;
      chart: string;
      conversion: number;
    }>("GET", `/v1/dashboard?campaign=${encodeURIComponent(campaign)}`);
  }

  runFormula(name: string, inputs: Record<string, unknown>) {
    return this.call<{ result: unknown; formula: string }>("POST", `/v1/formulas/${name}`, inputs);
  }

  connectors_() {
    return this.connectors();
  }
}
