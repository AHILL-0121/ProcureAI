export interface Invoice {
  id: string;
  invoice_number: string | null;
  vendor_name: string | null;
  vendor_id: string | null;
  invoice_date: string | null;
  due_date: string | null;
  total_amount: number;
  tax_amount: number;
  currency: string;
  po_reference: string | null;
  status: string;
  invoice_type: string;
  match_result: string;
  confidence_score: number;
  discrepancies: Discrepancy[] | null;
  processing_time: number | null;
  created_at: string;
  line_items: LineItem[];
}

export interface LineItem {
  item_code: string | null;
  description: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}

export interface Discrepancy {
  type: string;
  severity: string;
  message: string;
  invoice_value?: number;
  po_value?: number;
  variance_pct?: number;
}

export interface DashboardStats {
  total_invoices: number;
  matched: number;
  partial_match: number;
  no_match: number;
  pending: number;
  failed: number;
  total_value: number;
  avg_processing_time: number;
  avg_confidence: number;
}

export interface MatchDetail {
  invoice_id: string;
  invoice_number: string | null;
  vendor_name: string | null;
  total_amount: number;
  po_reference: string | null;
  match_result: string;
  discrepancies: Discrepancy[] | null;
  po_data: Record<string, any> | null;
  grn_data: Record<string, any> | null;
}

export interface ProcessingResult {
  status: string;
  invoice_id?: string;
  invoice_number?: string;
  vendor_name?: string;
  total_amount?: number;
  po_reference?: string;
  match_result?: string;
  match_score?: number;
  discrepancies: Discrepancy[];
  processing_time?: number;
  error?: string;
}

export interface HealthStatus {
  status: string;
  orchestrator: string;
  vision_ocr: {
    ollama_status: string;
    model: string;
    model_available: boolean;
    available_models?: string[];
    error?: string;
  };
  erp: {
    total_purchase_orders: number;
    total_goods_receipts: number;
    total_po_value: number;
    unique_vendors: number;
    total_po_lines?: number;
  };
  timestamp: string;
}

export interface WSMessage {
  event: string;
  invoice_id?: string;
  status?: string;
  match_result?: string;
  score?: number;
  processing_time?: number;
  error?: string;
  file?: string;
}
