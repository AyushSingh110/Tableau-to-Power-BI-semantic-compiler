// Mirrors the backend's combined conversion report (build_pbip + packaging).

export interface ConversionReport {
  total_calculations: number;
  measures_converted: number;
  columns_converted: number;
  parameters_converted: number;
  skipped_count: number;
  coverage_pct: number;
  failure_taxonomy: Record<string, number>;
  skipped_measures: { calculation_name: string; reason: string; taxonomy: string }[];
  fact_table_inference?: { table: string; method: string };
}

export interface CombinedReport {
  render_verified: string;
  model: {
    conversion_report: ConversionReport;
    tmdl: {
      tables: number;
      measures: number;
      calculated_columns: number;
      parameters: number;
      relationships: number;
    };
    tmdl_skipped_multiline: { name: string; kind: string; reason: string }[];
  };
  visuals: {
    worksheets_total: number;
    visuals_emitted: number;
    visuals_skipped: number;
    emitted_by_type: Record<string, number>;
    skipped_by_bucket: Record<string, number>;
    coverage_pct_schema_valid: number;
  };
  download: { token: string; filename: string };
  packaging: {
    portable: boolean;
    bundled_csvs: string[];
    data_folder_param: string;
    note: string;
  };
}
