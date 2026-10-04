export type Role = 'viewer' | 'ap_clerk' | 'approver' | 'admin';

export interface User {
  id: string;
  email: string;
  name: string;
  role: Role;
  active: boolean;
}

export type InvoiceStatus =
  | 'RECEIVED' | 'EXTRACTING' | 'EXTRACTED' | 'VALIDATING' | 'VALIDATED' | 'MATCHING'
  | 'MATCHED' | 'DISCREPANCY' | 'ON_HOLD' | 'APPROVED' | 'REJECTED' | 'DUPLICATE' | 'FAILED';

export type MatchResult = 'FULL_MATCH' | 'PARTIAL_MATCH' | 'NO_MATCH' | 'PENDING';
export type Severity = 'HIGH' | 'MEDIUM' | 'LOW';

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface InvoiceSummary {
  id: string;
  invoice_number: string | null;
  vendor_name: string | null;
  vendor_id: string | null;
  po_reference: string | null;
  total_amount: number;
  currency: string | null;
  status: InvoiceStatus;
  match_result: MatchResult;
  match_score: number | null;
  confidence_score: number;
  invoice_date: string | null;
  created_at: string | null;
  processing_time: number | null;
  original_filename: string | null;
  source_email: string | null;
  reviewed_by: string | null;
  top_issue: string | null;
  top_issue_code: string | null;
  top_issue_severity: Severity | null;
  issue_count: number;
}

export interface Discrepancy {
  type: string;
  severity: Severity;
  message: string;
  line?: number;
  invoice_value?: number | string;
  po_value?: number | string;
  variance_pct?: number | null;
  duplicate_of?: string;
}

export interface MatchCheck {
  code: string;
  severity: Severity;
  passed: boolean;
  message: string;
  line?: number;
  variance_pct?: number | null;
}

export interface Receipt {
  receipt_id: string;
  quantity: number;
  date: string | null;
}

export interface POLine {
  po_line_id: string;
  line_num: number;
  item_id: string | null;
  item_number: string | null;
  description: string;
  uom: string | null;
  quantity: number;
  unit_price: number;
  line_amount: number;
  delivery_date: string | null;
  received_qty: number;
  receipts: Receipt[];
  invoiced_qty?: number;
}

export interface PurchaseOrder {
  po_number: string;
  po_header_id: string;
  vendor_id: string | null;
  vendor_name: string;
  vendor_tax_id: string | null;
  currency: string;
  status: string;
  order_date: string | null;
  total_amount: number;
  lines: POLine[];
}

export interface GoodsReceipt {
  grn_number: string;
  grn_numbers: string[];
  received_date: string | null;
  lines_received: number;
  lines_total: number;
  status: 'COMPLETE' | 'PARTIAL';
}

export interface MatchLine {
  line: number;
  description: string | null;
  item_code: string | null;
  quantity: number;
  unit_price: number;
  total_price: number | null;
  po_line_id: string | null;
  po_line_num?: number;
  po_description?: string;
  po_item_number?: string | null;
  ordered_qty?: number;
  po_unit_price?: number;
  received_qty?: number;
  billed_before?: number;
  available_qty?: number;
  receipts?: Receipt[];
  price_variance_pct?: number | null;
  checks: string[];
}

export interface MatchSnapshot {
  po: PurchaseOrder | null;
  grn: GoodsReceipt | null;
  lines: MatchLine[];
  expected_net: number;
  tolerance: { qty_pct: number; price_pct: number; price_abs: number; total_abs: number };
  matched_at: string;
}

export interface InvoiceLine {
  id: string;
  line_no: number;
  item_code: string | null;
  description: string | null;
  quantity: number;
  unit_price: number;
  total_price: number;
  uom: string | null;
  matched_po_line_id: string | null;
}

export interface InvoiceDetail extends InvoiceSummary {
  due_date: string | null;
  subtotal: number | null;
  tax_amount: number;
  invoice_type: string;
  vendor_tax_id: string | null;
  validation: { errors?: string[]; warnings?: string[]; vendor_known?: boolean; edited_fields?: Record<string, string> } | null;
  discrepancies: Discrepancy[] | null;
  match_checks: MatchCheck[] | null;
  match_snapshot: MatchSnapshot | null;
  extraction: {
    extraction_method?: string;
    ocr_confidence?: number | null;
    confidence_score?: number;
    model?: string;
    totals_found_in_text?: boolean | null;
  } | null;
  duplicate_of: string | null;
  error: string | null;
  review_note: string | null;
  reviewed_at: string | null;
  line_items: InvoiceLine[];
}

export interface AuditEntry {
  id: string;
  invoice_id: string | null;
  agent: string;
  actor: string | null;
  action: string;
  details: Record<string, unknown> | null;
  timestamp: string | null;
}

export interface CurrencyTotal {
  currency: string;
  amount: number;
  count: number;
}

export interface DashboardStats {
  total_invoices: number;
  matched: number;
  partial_match: number;
  no_match: number;
  pending: number;
  failed: number;
  duplicates: number;
  in_review: number;
  on_hold: number;
  approved: number;
  rejected: number;
  processing: number;
  auto_match_rate: number;
  avg_processing_time: number;
  avg_confidence: number;
  value_by_currency: CurrencyTotal[];
  cleared_by_currency: CurrencyTotal[];
  held_by_currency: CurrencyTotal[];
  issues_by_type: { type: string; count: number }[];
  vendors_to_watch: { vendor: string; open_exceptions: number }[];
  daily: { date: string; received: number; auto_matched: number; exceptions: number }[];
  today: { received: number; auto_matched: number; approved: number; rejected: number; waiting: number };
}

export interface Health {
  status: 'healthy' | 'degraded' | 'unhealthy';
  orchestrator: string;
  vision_ocr: { groq_status: string; model: string; vision_model: string | null; model_available: boolean; error?: string };
  erp: { total_purchase_orders: number; total_vendors: number; total_goods_receipts: number; status: string };
  queue_depth: number;
  timestamp: string;
}

export interface POSummary {
  po_number: string;
  vendor_name: string;
  vendor_id: string | null;
  order_date: string | null;
  total_amount: number;
  currency: string;
  status: string;
  line_count: number;
}

export interface Tolerance {
  qty_pct: number;
  price_pct: number;
  price_abs: number;
  total_abs: number;
  vendor_id?: string | null;
  vendor_name?: string | null;
  updated_by?: string | null;
  updated_at?: string | null;
}

export interface VendorRef {
  supplier_id: string;
  name: string;
  tax_id: string | null;
  currency: string | null;
}

export interface UploadItem {
  invoice_id: string | null;
  filename: string;
  status: string;
  duplicate: boolean;
  error: string | null;
}

export interface WSEvent {
  event: 'status_update' | 'match_complete' | 'processing_error' | 'review_update' | 'pong';
  invoice_id?: string;
  status?: InvoiceStatus;
  invoice_number?: string | null;
  file?: string | null;
  step?: 'received' | 'read' | 'check' | 'lookup' | 'match';
  step_index?: number;
  match_result?: MatchResult;
  score?: number;
  error?: string;
  actor?: string;
}

export interface ErpLayout {
  name: string;
  label: string;
  file: string;
  key: string;
  required: string[];
  optional: string[];
}

export interface ErpStatus {
  source: 'sample' | 'import' | 'empty';
  counts: Record<string, number>;
  layouts: ErpLayout[];
  last_import: { at: string; by: string | null; mode: 'merge' | 'replace'; files: string[]; counts: Record<string, number>; rematched: number } | null;
}

export interface ErpEntityReport {
  name: string;
  label: string;
  filename: string | null;
  rows: number;
  inserts: number;
  updates: number;
  emptied: boolean;
  error_count: number;
  errors: { row: number | null; column: string | null; message: string }[];
}

export interface ErpImportResult {
  mode: 'merge' | 'replace';
  ok: boolean;
  committed: boolean;
  problems: string[];
  warnings: string[];
  entities: ErpEntityReport[];
  counts?: Record<string, number>;
  rematching?: number;
}
