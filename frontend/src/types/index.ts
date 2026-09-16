/**
 * ShopGraph TypeScript Type Definitions
 * Exact mirrors of Phase 3 FastAPI Pydantic schemas.
 */

export interface BrandRef {
  id: string;
  name: string;
}

export interface CategoryRef {
  id: string;
  name: string;
  level: number;
  parent_id?: string | null;
}

export interface ProductSummary {
  id: string;
  title: string;
  average_rating?: number | null;
  rating_count: number;
  price?: number | null;
  price_currency?: string | null;
  brand_name?: string | null;
  category_id?: string | null;
  image_url?: string | null;
}

export interface ProductDetail extends ProductSummary {
  brand?: BrandRef | null;
  category?: CategoryRef | null;
  main_category?: string | null;
  features: string[];
  description: string[];
  details: Record<string, any>;
  raw_price?: string | null;
}

export interface ProductFilter {
  category_id?: string | null;
  brand_id?: string | null;
  brand_name?: string | null;
  min_price?: number | null;
  max_price?: number | null;
  min_rating?: number | null;
  min_reviews?: number | null;
  search_term?: string | null;
  limit?: number;
}

export type EvidenceType =
  | 'OBSERVED_GRAPH_FACT'
  | 'VECTOR_SIMILARITY'
  | 'REVIEW_EVIDENCE'
  | 'RECOMMENDATION_INFERENCE';

export interface EvidenceItem {
  id: string;
  evidence_type: EvidenceType;
  source: string;
  product_id?: string | null;
  value: any;
  description: string;
  confidence: number;
  metadata?: Record<string, any>;
}

export interface RatingDistribution {
  total_reviews: number;
  average_rating: number;
  verified_count: number;
  unverified_count: number;
  star_counts: Record<number, number>;
}

export interface AspectSentiment {
  aspect: string;
  sentiment: 'positive' | 'neutral' | 'negative' | string;
  mention_count: number;
  sample_quotes: string[];
}

export interface ReviewIntelligenceReport {
  product_id: string;
  distribution: RatingDistribution;
  aspects: AspectSentiment[];
  top_positive_snippets: string[];
  top_negative_snippets: string[];
  summary?: string | null;
}

export interface FactorContribution {
  factor_name: string;
  weight: number;
  score: number;
  weighted_score: number;
  evidence_type: EvidenceType;
  explanation: string;
}

export interface GraphPathStep {
  start_node: string;
  start_label: string;
  relationship: string;
  end_node: string;
  end_label: string;
}

export interface ExplanationReport {
  product_id: string;
  product_title: string;
  summary_reason: string;
  factors: FactorContribution[];
  graph_paths: GraphPathStep[][];
  review_evidence_quotes: string[];
  observed_facts: string[];
  inferred_aspects: string[];
  limitations: string[];
}

export interface RecommendedProduct {
  product: ProductSummary;
  composite_score: number;
  explanation: ExplanationReport;
}

export interface RecommendationResponse {
  query?: string | null;
  target_product_id?: string | null;
  recommendations: RecommendedProduct[];
  total_found: number;
  weights_applied: Record<string, number>;
  evidence_items: EvidenceItem[];
}

export type QueryIntent =
  | 'product_search'
  | 'recommendation'
  | 'comparison'
  | 'review_intelligence'
  | 'product_explanation'
  | 'category_exploration'
  | 'similarity_search'
  | 'graph_relationship_exploration';

export type RetrievalStrategy = 'GRAPH_ONLY' | 'VECTOR_ONLY' | 'HYBRID';

export interface QueryResponse {
  query: string;
  intent: QueryIntent;
  strategy_used: RetrievalStrategy;
  answer: string;
  products: ProductSummary[];
  evidence: EvidenceItem[];
  cypher_executed?: string | null;
  explanation?: string | null;
  limitations: string[];
  latency_breakdown_ms: Record<string, number>;
}

export interface ProductComparisonItem {
  product: ProductDetail;
  review_intelligence?: ReviewIntelligenceReport | null;
  strengths: string[];
  tradeoffs: string[];
}

export interface ComparisonResponse {
  products: ProductComparisonItem[];
  matrix: Record<string, Record<string, any>>;
  llm_synthesis?: string | null;
  evidence_items: EvidenceItem[];
  limitations: string[];
}

export interface ReviewItem {
  id: string;
  user_id: string;
  product_id: string;
  variant_asin?: string | null;
  rating: number;
  title?: string | null;
  text?: string | null;
  timestamp: number;
  verified_purchase: boolean;
  helpful_votes: number;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'offline' | string;
  app_name?: string;
  version: string;
  environment?: string;
  services?: {
    neo4j?: {
      status: 'connected' | 'unavailable' | string;
      uri?: string;
    };
    llm?: {
      provider: string;
      model: string;
      configured: boolean;
    };
    embeddings?: {
      provider: string;
      model: string;
      dimension: number;
    };
  };
  database?: string;
  dataset_summary?: {
    products: number;
    reviews: number;
    brands: number;
    categories: number;
  };
}
