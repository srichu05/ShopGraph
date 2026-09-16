import React, { useState } from 'react';
import {
  X,
  Sparkles,
  Send,
  Code2,
  Clock,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Copy,
  Check,
  HelpCircle,
} from 'lucide-react';
import { QueryResponse, RetrievalStrategy } from '../types';
import { api } from '../services/api';
import { ProductCard } from './ProductCard';
import { GroundedAnswerRenderer } from './GroundedAnswerRenderer';

interface AskShopGraphProps {
  isOpen: boolean;
  onClose: () => void;
  initialQuery?: string;
  onSelectProduct: (product: any) => void;
  onToggleCompare: (product: any) => void;
  comparedIds: string[];
}

export const AskShopGraph: React.FC<AskShopGraphProps> = ({
  isOpen,
  onClose,
  initialQuery = '',
  onSelectProduct,
  onToggleCompare,
  comparedIds,
}) => {
  const [query, setQuery] = useState(initialQuery);
  const [strategy, setStrategy] = useState<RetrievalStrategy>('HYBRID');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<(QueryResponse & { isDemoFallback?: boolean }) | null>(null);
  const [showCypher, setShowCypher] = useState(false);
  const [showEvidence, setShowEvidence] = useState(false);
  const [copiedCypher, setCopiedCypher] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  React.useEffect(() => {
    if (initialQuery && isOpen) {
      setQuery(initialQuery);
      handleExecute(initialQuery);
    }
  }, [initialQuery, isOpen]);

  if (!isOpen) return null;

  const handleExecute = async (qText?: string) => {
    const activeQ = qText || query;
    if (!activeQ.trim()) return;

    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.askShopGraph(activeQ, strategy);
      setResponse(res);
    } catch (err: any) {
      console.error('Query error:', err);
      setErrorMsg(err?.message || 'Failed to retrieve response from ShopGraph engine.');
    } finally {
      setLoading(false);
    }
  };

  const copyCypher = () => {
    if (!response?.cypher_executed) return;
    navigator.clipboard.writeText(response.cypher_executed);
    setCopiedCypher(true);
    setTimeout(() => setCopiedCypher(false), 2000);
  };

  const suggestions = [
    'electric guitar with dual humbuckers',
    'dynamic vocal microphone for podcasting under 300',
    'drum set with good build quality',
    'audio interface for home recording',
    'guitar cable with durable construction',
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="bg-card w-full max-w-4xl max-h-[92vh] rounded-2xl border border-border shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-muted/40">
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-serif text-lg font-bold text-foreground leading-none">
                Ask ShopGraph Intelligence Console
              </h3>
              <span className="text-[10px] text-muted-foreground">
                Grounded Hybrid Retrieval with Cypher & Vector Fusion
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Query Input Section */}
        <div className="p-6 border-b border-border bg-card space-y-3">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleExecute();
            }}
            className="flex items-center gap-2"
          >
            <div className="relative flex-1">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Ask about musical gear, acoustics, pairings, or review intelligence..."
                className="w-full bg-muted/50 border border-border rounded-xl px-4 py-2.5 text-sm sm:text-base outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 text-foreground placeholder:text-muted-foreground"
              />
            </div>

            {/* Retrieval Strategy Selector */}
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value as RetrievalStrategy)}
              className="hidden sm:block text-xs bg-muted/70 border border-border rounded-xl px-3 py-2.5 outline-none font-medium text-foreground"
            >
              <option value="HYBRID">Hybrid (Graph + Semantic)</option>
              <option value="GRAPH_ONLY">Graph Only (Cypher)</option>
              <option value="VECTOR_ONLY">Vector Only (BGE ANN)</option>
            </select>

            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="flex items-center space-x-1.5 px-4 py-2.5 bg-primary text-primary-foreground text-sm font-semibold rounded-xl hover:opacity-90 disabled:opacity-50 transition-all shadow-sm"
            >
              <Send className="w-4 h-4" />
              <span className="hidden sm:inline">Ask AI</span>
            </button>
          </form>

          {/* Suggestion Chips */}
          <div className="flex flex-wrap gap-1.5">
            {suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => {
                  setQuery(s);
                  handleExecute(s);
                }}
                className="text-[11px] px-2.5 py-1 rounded-full bg-muted hover:bg-muted/80 text-muted-foreground hover:text-foreground border border-border/60 transition-colors"
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        {/* Scrollable Results Area */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {loading ? (
            <div className="py-16 text-center space-y-3">
              <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="font-serif text-base font-medium text-foreground">
                Synthesizing grounded answer...
              </p>
              <p className="text-xs text-muted-foreground">
                Running query understanding, Cypher graph filtering, BGE vector retrieval, and grounded synthesis.
              </p>
              <p className="text-[11px] text-primary italic">
                (Initializing semantic retrieval engine if cold-starting...)
              </p>
            </div>
          ) : errorMsg ? (
            <div className="bg-destructive/10 border border-destructive/20 rounded-xl p-5 text-xs text-destructive space-y-2">
              <strong className="block font-bold">Query Execution Error</strong>
              <p>{errorMsg}</p>
            </div>
          ) : response ? (
            <div className="space-y-6">
              {/* Intent & Strategy Pills */}
              <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-border/60 text-xs">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-primary bg-primary/10 px-2.5 py-0.5 rounded-full">
                    Intent: {response.intent}
                  </span>
                  <span className="text-[11px] font-medium text-muted-foreground bg-muted px-2 py-0.5 rounded">
                    Strategy:{' '}
                    {response.strategy_used === 'HYBRID'
                      ? 'Graph + Semantic Retrieval'
                      : response.strategy_used === 'GRAPH_ONLY'
                      ? 'Graph Structured Retrieval (Cypher)'
                      : 'Semantic Vector Retrieval (BGE)'}
                  </span>
                  {response.isDemoFallback && (
                    <span className="text-[10px] font-semibold bg-accent/30 text-amber-800 px-2 py-0.5 rounded">
                      Demo Fallback
                    </span>
                  )}
                </div>

                {/* Micro-latency Breakdown */}
                {response.latency_breakdown_ms && (
                  <div className="flex items-center space-x-2 text-[11px] text-muted-foreground font-mono bg-muted/60 px-2.5 py-1 rounded-md">
                    <Clock className="w-3.5 h-3.5 text-primary" />
                    <span>Total: {response.latency_breakdown_ms.total ?? response.latency_breakdown_ms.total_ms ?? 0}ms</span>
                  </div>
                )}
              </div>

              {/* Grounded Natural Language Answer */}
              <div className="bg-card border border-border/80 rounded-xl p-5 shadow-sm space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center space-x-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-primary" />
                  <span>Grounded Synthesized Answer</span>
                </h4>
                <GroundedAnswerRenderer
                  content={response.answer}
                  products={response.products}
                  onSelectProduct={onSelectProduct}
                />
              </div>

              {/* Why this answer? (Progressive Disclosure) */}
              {response.explanation && (
                <div className="bg-muted/30 border border-border/60 rounded-xl p-4 space-y-1.5">
                  <div className="flex items-center space-x-1.5 text-xs font-semibold text-foreground">
                    <HelpCircle className="w-3.5 h-3.5 text-primary" />
                    <span>Why this answer?</span>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {response.explanation}
                  </p>
                </div>
              )}

              {/* Safe Read-Only Cypher Query Drawer */}
              {response.cypher_executed && (
                <div className="border border-border/80 rounded-xl overflow-hidden bg-card">
                  <button
                    onClick={() => setShowCypher(!showCypher)}
                    className="w-full px-4 py-3 bg-muted/40 hover:bg-muted/70 flex items-center justify-between text-xs font-semibold text-foreground transition-colors"
                  >
                    <div className="flex items-center space-x-2">
                      <Code2 className="w-4 h-4 text-primary" />
                      <span>Safe Read-Only Cypher Query Executed</span>
                    </div>
                    {showCypher ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>

                  {showCypher && (
                    <div className="p-4 bg-muted/20 border-t border-border/60 relative">
                      <button
                        onClick={copyCypher}
                        className="absolute top-3 right-3 p-1.5 rounded bg-card border border-border text-xs text-muted-foreground hover:text-foreground flex items-center space-x-1"
                        title="Copy Cypher"
                      >
                        {copiedCypher ? (
                          <Check className="w-3.5 h-3.5 text-secondary" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                        <span>{copiedCypher ? 'Copied' : 'Copy'}</span>
                      </button>
                      <pre className="font-mono text-xs text-foreground/90 overflow-x-auto p-2 bg-muted/60 rounded-lg whitespace-pre-wrap">
                        {response.cypher_executed}
                      </pre>
                    </div>
                  )}
                </div>
              )}

              {/* Traceable Evidence Drawer */}
              {response.evidence && response.evidence.length > 0 && (
                <div className="border border-border/80 rounded-xl overflow-hidden bg-card">
                  <button
                    onClick={() => setShowEvidence(!showEvidence)}
                    className="w-full px-4 py-3 bg-muted/40 hover:bg-muted/70 flex items-center justify-between text-xs font-semibold text-foreground transition-colors"
                  >
                    <div className="flex items-center space-x-2">
                      <CheckCircle2 className="w-4 h-4 text-secondary" />
                      <span>Traceable Provenance ({response.evidence.length} Evidence Items)</span>
                    </div>
                    {showEvidence ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  </button>

                  {showEvidence && (
                    <div className="p-4 space-y-2.5 bg-muted/20 border-t border-border/60">
                      {response.evidence.map((ev) => (
                        <div
                          key={ev.id}
                          className="bg-card p-3 rounded-lg border border-border/80 text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-[11px] font-bold text-foreground">
                              {ev.source}
                            </span>
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded font-mono ${
                                ev.evidence_type === 'OBSERVED_GRAPH_FACT'
                                  ? 'bg-secondary/15 text-secondary'
                                  : ev.evidence_type === 'REVIEW_EVIDENCE'
                                  ? 'bg-amber-500/15 text-amber-800'
                                  : 'bg-primary/15 text-primary'
                              }`}
                            >
                              {ev.evidence_type} • Conf: {(ev.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                          <p className="text-muted-foreground">{ev.description}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Grounded Candidate Products */}
              {response.products && response.products.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Grounded Candidate Products ({response.products.length})
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {response.products.map((prod) => (
                      <ProductCard
                        key={prod.id}
                        product={prod}
                        onSelect={onSelectProduct}
                        onToggleCompare={onToggleCompare}
                        isCompared={comparedIds.includes(prod.id)}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Data boundary limitations */}
              {response.limitations && response.limitations.length > 0 && (
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 text-xs text-amber-900 flex items-start space-x-2.5">
                  <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <strong className="block font-semibold mb-1">
                      Data Boundaries & Caveats:
                    </strong>
                    <ul className="list-disc list-inside space-y-0.5 text-amber-800">
                      {response.limitations.map((lim, idx) => (
                        <li key={idx}>{lim}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="py-12 text-center text-muted-foreground text-xs">
              Type a musical instrument query above or click a suggestion to see grounded Graph-RAG in action.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
