import React, { useState } from 'react';
import { Search, Sparkles, GitGraph, ShieldCheck, ArrowRight, Layers, Star } from 'lucide-react';
import { ProductDetail, ProductSummary } from '../types';

interface HeroSectionProps {
  onSearch: (query: string) => void;
  onOpenAskAiWithQuery: (query: string) => void;
  featuredProduct: ProductDetail | ProductSummary;
  onSelectProduct: (product: any) => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({
  onSearch,
  onOpenAskAiWithQuery,
  featuredProduct,
  onSelectProduct,
}) => {
  const [inputQuery, setInputQuery] = useState('');

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim()) return;
    onOpenAskAiWithQuery(inputQuery);
  };

  const sampleQueries = [
    'electric guitar with dual humbuckers',
    'dynamic vocal microphone for podcasting under 300',
    'drum set with good build quality',
    'audio interface for home recording',
    'guitar cable with durable construction',
  ];

  return (
    <section className="relative overflow-hidden pt-8 pb-16 md:py-20 bg-grid-subtle">
      {/* Decorative subtle ambient glows matching template */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-accent/15 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="absolute top-1/3 right-10 w-[400px] h-[300px] bg-primary/10 rounded-full blur-3xl pointer-events-none -z-10" />

      <div className="container mx-auto px-4 sm:px-6">
        {/* Header editorial tag */}
        <div className="flex flex-col items-center text-center max-w-3xl mx-auto mb-10">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-primary/10 text-primary text-xs font-semibold uppercase tracking-wider mb-5 border border-primary/20">
            <GitGraph className="w-3.5 h-3.5" />
            <span>Explainable Graph-RAG Architecture</span>
          </div>

          <h1 className="font-serif text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight text-foreground leading-[1.15] mb-5">
            Musical Gear Discovery Grounded in{' '}
            <span className="italic text-primary font-normal">Knowledge Graphs.</span>
          </h1>

          <p className="text-base sm:text-lg text-muted-foreground max-w-2xl leading-relaxed">
            Stop guessing from generic lists. ShopGraph retrieves verified reviewer facts,
            multi-hop co-purchase graphs, and Bayesian aspect sentiments with complete provenance.
          </p>

          {/* Search Bar Capsule */}
          <form
            onSubmit={handleSearchSubmit}
            className="w-full max-w-2xl mt-8 relative flex items-center"
          >
            <div className="relative w-full shadow-lg rounded-2xl bg-card border border-border/80 focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20 transition-all">
              <div className="flex items-center px-4 py-2">
                <Search className="w-5 h-5 text-muted-foreground mr-3 shrink-0" />
                <input
                  type="text"
                  value={inputQuery}
                  onChange={(e) => setInputQuery(e.target.value)}
                  placeholder="Ask anything (e.g., 'Best dynamic mic for untreated rooms under $450')..."
                  className="w-full bg-transparent border-none outline-none text-foreground placeholder:text-muted-foreground text-sm sm:text-base py-2"
                />
                <button
                  type="submit"
                  className="shrink-0 flex items-center space-x-1.5 px-4 py-2 bg-primary text-primary-foreground font-medium text-sm rounded-xl hover:opacity-95 shadow-sm transition-all"
                >
                  <Sparkles className="w-4 h-4" />
                  <span className="hidden sm:inline">Ask AI</span>
                </button>
              </div>
            </div>
          </form>

          {/* Prompt pills */}
          <div className="flex flex-wrap items-center justify-center gap-2 mt-4 max-w-2xl">
            <span className="text-xs text-muted-foreground font-medium">Try:</span>
            {sampleQueries.map((q, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setInputQuery(q);
                  onOpenAskAiWithQuery(q);
                }}
                className="text-xs px-2.5 py-1 rounded-full bg-muted/80 hover:bg-muted text-muted-foreground hover:text-foreground border border-border/60 transition-colors text-left"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Asymmetric Bento Grid (4 Tiles) */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-5 mt-12 max-w-6xl mx-auto">
          {/* Tile 1: Large Featured Card (7 cols) */}
          <div
            onClick={() => onSelectProduct(featuredProduct)}
            className="md:col-span-7 group cursor-pointer bg-card rounded-2xl border border-border/80 p-6 sm:p-8 flex flex-col justify-between hover:shadow-md hover:border-primary/40 transition-all duration-200 relative overflow-hidden"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <span className="inline-block text-[11px] font-bold uppercase tracking-wider text-primary bg-primary/10 px-2.5 py-0.5 rounded-full mb-2">
                  Featured Node • {featuredProduct.brand_name}
                </span>
                <h3 className="font-serif text-2xl sm:text-3xl font-bold text-foreground group-hover:text-primary transition-colors">
                  {featuredProduct.title}
                </h3>
              </div>
              <div className="shrink-0 text-right">
                <span className="font-serif text-2xl font-bold text-foreground">
                  {featuredProduct.price !== null && featuredProduct.price !== undefined
                    ? `$${featuredProduct.price.toFixed(2)}`
                    : 'Price unavailable'}
                </span>
                <div className="flex items-center space-x-1 text-xs text-amber-600 justify-end mt-0.5">
                  <Star className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />
                  <span className="font-semibold">{featuredProduct.average_rating ? featuredProduct.average_rating.toFixed(1) : 'N/A'}</span>
                  <span className="text-muted-foreground">({featuredProduct.rating_count.toLocaleString()})</span>
                </div>
              </div>
            </div>

            <p className="text-sm text-muted-foreground line-clamp-2 mb-6">
              {('features' in featuredProduct && featuredProduct.features?.[0]) ||
                ('description' in featuredProduct && featuredProduct.description?.[0]) ||
                featuredProduct.title}
            </p>

            <div className="relative rounded-xl overflow-hidden bg-muted/40 aspect-[16/9] mb-4">
              <img
                src={featuredProduct.image_url || ''}
                alt={featuredProduct.title}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
              <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between text-white text-xs">
                <span className="font-medium bg-black/40 backdrop-blur-sm px-2.5 py-1 rounded">
                  Graph Hub: 2,840 Verified Reviews
                </span>
                <span className="flex items-center space-x-1 text-accent font-semibold">
                  <span>Inspect Reasoning</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs text-muted-foreground pt-2 border-t border-border/50">
              <span className="flex items-center space-x-1">
                <ShieldCheck className="w-4 h-4 text-secondary" />
                <span>Zero Hallucination Verified</span>
              </span>
              <span className="font-mono text-[11px]">ID: {featuredProduct.id}</span>
            </div>
          </div>

          {/* Right Column Bento Stack (5 cols) */}
          <div className="md:col-span-5 flex flex-col gap-5">
            {/* Tile 2: Multi-Hop Co-Purchase Traversal */}
            <div className="bg-card rounded-2xl border border-border/80 p-6 flex flex-col justify-between hover:shadow-md transition-all">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-secondary bg-secondary/10 px-2.5 py-0.5 rounded-full">
                    Multi-Hop Cypher Path
                  </span>
                  <Layers className="w-4 h-4 text-muted-foreground" />
                </div>
                <h4 className="font-serif text-lg font-bold text-foreground mb-1">
                  Verified Purchaser Overlap
                </h4>
                <p className="text-xs text-muted-foreground mb-4">
                  Traversing reviewer purchase intersections reveals natural equipment chains.
                </p>

                {/* Micro-path visualization */}
                <div className="bg-muted/50 rounded-xl p-3 text-xs font-mono border border-border/50 space-y-2">
                  <div className="flex items-center space-x-2 text-foreground">
                    <span className="w-2 h-2 rounded-full bg-primary" />
                    <span className="font-semibold">Shure SM7B</span>
                    <span className="text-muted-foreground text-[10px]">(Product Node)</span>
                  </div>
                  <div className="pl-3 border-l-2 border-dashed border-primary/40 text-[11px] text-primary flex items-center space-x-1">
                    <span>&lt;-[:PURCHASED]- (:User) -[:PURCHASED]-&gt;</span>
                  </div>
                  <div className="flex items-center space-x-2 text-foreground">
                    <span className="w-2 h-2 rounded-full bg-secondary" />
                    <span className="font-semibold">Focusrite 2i2</span>
                    <span className="text-muted-foreground text-[10px]">(Connected Hub)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Tile 3: Bayesian Sentiment Shield */}
            <div className="bg-card rounded-2xl border border-border/80 p-6 flex flex-col justify-between hover:shadow-md transition-all">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-amber-700 bg-accent/30 px-2.5 py-0.5 rounded-full">
                    Review Intelligence
                  </span>
                  <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
                </div>
                <h4 className="font-serif text-lg font-bold text-foreground mb-1">
                  Bayesian Aspect Extraction
                </h4>
                <p className="text-xs text-muted-foreground mb-3">
                  Raw Amazon reviews classified into fine-grained acoustic dimensions.
                </p>

                <div className="space-y-2.5">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-medium text-foreground">Off-Axis Rejection</span>
                      <span className="text-secondary font-semibold">96% Positive</span>
                    </div>
                    <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-secondary rounded-full" style={{ width: '96%' }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-medium text-foreground">Vocal Warmth / Presence</span>
                      <span className="text-secondary font-semibold">92% Positive</span>
                    </div>
                    <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-secondary rounded-full" style={{ width: '92%' }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-medium text-foreground">Gain Appetite (Preamps)</span>
                      <span className="text-amber-600 font-semibold">58% Neutral</span>
                    </div>
                    <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
                      <div className="h-full bg-amber-500 rounded-full" style={{ width: '58%' }} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
