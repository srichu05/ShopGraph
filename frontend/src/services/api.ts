/**
 * ShopGraph API Client
 * Connects to FastAPI backend with graceful fallback to curated Musical Instruments demo data
 * only when the live backend is unreachable.
 */

import {
  ProductDetail,
  ProductSummary,
  ReviewIntelligenceReport,
  RecommendationResponse,
  ComparisonResponse,
  QueryResponse,
  HealthStatus,
  RetrievalStrategy,
  EvidenceItem,
} from '../types';
import {
  MOCK_PRODUCTS,
  MOCK_REVIEW_INTELLIGENCE,
  MOCK_QUERY_RESPONSE,
  MOCK_RECOMMENDATION_RESPONSE,
  MOCK_COMPARISON_RESPONSE,
} from './mockData';

// Vite environment variable configuration
const BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL !== undefined
    ? import.meta.env.VITE_API_BASE_URL
    : 'http://127.0.0.1:8000';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const errorBody = await res.text().catch(() => '');
    throw new Error(`API error ${res.status}: ${errorBody || res.statusText}`);
  }

  return res.json();
}

export interface SearchResultPayload {
  products: ProductSummary[];
  total_found: number;
  evidence?: EvidenceItem[];
  cypher_query?: string;
  isDemoFallback?: boolean;
}

export const api = {
  getBaseUrl(): string {
    return BASE_URL;
  },

  /**
   * Health & database status check
   */
  async getHealth(): Promise<HealthStatus> {
    try {
      return await fetchJson<HealthStatus>(`${BASE_URL}/health`);
    } catch {
      return {
        status: 'offline',
        version: '1.0.0-offline',
        services: {
          neo4j: {
            status: 'unavailable',
          },
        },
        dataset_summary: {
          products: MOCK_PRODUCTS.length,
          reviews: 14280,
          brands: 12,
          categories: 6,
        },
      };
    }
  },

  /**
   * Product search with facet filtering
   */
  async searchProducts(params: {
    query?: string;
    category?: string;
    brand?: string;
    min_price?: number;
    max_price?: number;
    min_rating?: number;
    limit?: number;
  }): Promise<SearchResultPayload> {
    try {
      const res = await fetchJson<{
        query: string;
        products: ProductSummary[];
        total_found: number;
        evidence: EvidenceItem[];
        cypher_query?: string;
      }>(`${BASE_URL}/api/search`, {
        method: 'POST',
        body: JSON.stringify({
          query: params.query?.trim() ? params.query : '*',
          category: params.category || undefined,
          brand: params.brand || undefined,
          min_price: params.min_price !== undefined ? params.min_price : undefined,
          max_price: params.max_price !== undefined ? params.max_price : undefined,
          min_rating: params.min_rating !== undefined ? params.min_rating : undefined,
          limit: params.limit || 20,
        }),
      });

      return {
        products: res.products,
        total_found: res.total_found,
        evidence: res.evidence,
        cypher_query: res.cypher_query,
        isDemoFallback: false,
      };
    } catch (err) {
      console.warn('Backend search unreachable, using demo catalog fallback:', err);
      let filtered = [...MOCK_PRODUCTS];

      if (params.query && params.query !== '*') {
        const q = params.query.toLowerCase();
        filtered = filtered.filter(
          (p) =>
            p.title.toLowerCase().includes(q) ||
            p.brand_name?.toLowerCase().includes(q) ||
            p.features.some((f) => f.toLowerCase().includes(q))
        );
      }
      if (params.category) {
        filtered = filtered.filter(
          (p) =>
            p.category_id === params.category ||
            p.category?.name.toLowerCase().includes(params.category!.toLowerCase())
        );
      }
      if (params.brand) {
        filtered = filtered.filter(
          (p) => p.brand_name?.toLowerCase() === params.brand!.toLowerCase()
        );
      }
      if (params.min_price !== undefined) {
        filtered = filtered.filter((p) => (p.price ?? 0) >= params.min_price!);
      }
      if (params.max_price !== undefined) {
        filtered = filtered.filter((p) => (p.price ?? 99999) <= params.max_price!);
      }
      if (params.min_rating !== undefined) {
        filtered = filtered.filter((p) => (p.average_rating ?? 0) >= params.min_rating!);
      }

      return {
        products: filtered.slice(0, params.limit || 20),
        total_found: filtered.length,
        cypher_query:
          'MATCH (p:Product)-[:BELONGS_TO]->(c:Category)\nWHERE p.rating >= $min_rating\nRETURN p LIMIT 20;',
        isDemoFallback: true,
      };
    }
  },

  /**
   * Get single product detail
   */
  async getProduct(productId: string): Promise<ProductDetail> {
    try {
      return await fetchJson<ProductDetail>(`${BASE_URL}/api/products/${productId}`);
    } catch (err) {
      console.warn(`Backend product ${productId} unreachable, using demo catalog:`, err);
      const match = MOCK_PRODUCTS.find((p) => p.id === productId);
      if (match) return match;
      return MOCK_PRODUCTS[0];
    }
  },

  /**
   * Get product review intelligence report
   */
  async getProductReviews(productId: string): Promise<ReviewIntelligenceReport> {
    try {
      return await fetchJson<ReviewIntelligenceReport>(
        `${BASE_URL}/api/products/${productId}/reviews`
      );
    } catch (err) {
      console.warn(`Backend review intelligence for ${productId} unreachable, using demo fallback:`, err);
      return (
        MOCK_REVIEW_INTELLIGENCE[productId] || {
          product_id: productId,
          distribution: {
            total_reviews: 420,
            average_rating: 4.6,
            verified_count: 390,
            unverified_count: 30,
            star_counts: { 5: 310, 4: 70, 3: 25, 2: 10, 1: 5 },
          },
          aspects: [
            {
              aspect: 'Tone & Sound Definition',
              sentiment: 'positive',
              mention_count: 140,
              sample_quotes: ['Clear and responsive tone across all dynamic ranges.'],
            },
            {
              aspect: 'Build Quality',
              sentiment: 'positive',
              mention_count: 95,
              sample_quotes: ['Solid construction, heavy-duty components.'],
            },
          ],
          top_positive_snippets: ['Clear and responsive tone across all dynamic ranges.'],
          top_negative_snippets: ['Instruction manual could be more comprehensive.'],
          summary:
            'Reliable musical gear favored by studio recording artists and performing musicians.',
        }
      );
    }
  },

  /**
   * Natural language Graph-RAG query ("Ask ShopGraph")
   */
  async askShopGraph(
    query: string,
    strategyOverride?: RetrievalStrategy
  ): Promise<QueryResponse & { isDemoFallback?: boolean }> {
    try {
      const res = await fetchJson<QueryResponse>(`${BASE_URL}/api/query`, {
        method: 'POST',
        body: JSON.stringify({
          query,
          strategy_override: strategyOverride,
          limit: 6,
        }),
      });
      return { ...res, isDemoFallback: false };
    } catch (err) {
      console.warn('Backend query unreachable, using mock Graph-RAG answer:', err);
      return {
        ...MOCK_QUERY_RESPONSE,
        query,
        isDemoFallback: true,
      };
    }
  },

  /**
   * Multi-factor explainable recommendations
   */
  async getRecommendations(params: {
    productId?: string;
    categoryId?: string;
    query?: string;
    maxPrice?: number;
    minRating?: number;
    limit?: number;
  }): Promise<RecommendationResponse & { isDemoFallback?: boolean }> {
    try {
      const res = await fetchJson<RecommendationResponse>(`${BASE_URL}/api/recommend`, {
        method: 'POST',
        body: JSON.stringify({
          product_id: params.productId,
          category_id: params.categoryId,
          query: params.query,
          max_price: params.maxPrice,
          min_rating: params.minRating,
          limit: params.limit || 5,
        }),
      });
      return { ...res, isDemoFallback: false };
    } catch (err) {
      console.warn('Backend recommendations unreachable, using mock:', err);
      return { ...MOCK_RECOMMENDATION_RESPONSE, isDemoFallback: true };
    }
  },

  /**
   * Side-by-side product comparison
   */
  async compareProducts(productIds: string[]): Promise<ComparisonResponse & { isDemoFallback?: boolean }> {
    try {
      const res = await fetchJson<ComparisonResponse>(`${BASE_URL}/api/compare`, {
        method: 'POST',
        body: JSON.stringify({
          product_ids: productIds,
        }),
      });
      return { ...res, isDemoFallback: false };
    } catch (err) {
      console.warn('Backend comparison unreachable, using mock:', err);
      return { ...MOCK_COMPARISON_RESPONSE, isDemoFallback: true };
    }
  },
};
