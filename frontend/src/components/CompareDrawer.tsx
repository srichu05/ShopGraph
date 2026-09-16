import React, { useState } from 'react';
import { Scale, X, ArrowRight, CheckCircle2, AlertCircle, Sparkles } from 'lucide-react';
import { ProductDetail, ComparisonResponse } from '../types';
import { api } from '../services/api';

interface CompareDrawerProps {
  comparedProducts: ProductDetail[];
  onRemoveProduct: (productId: string) => void;
  onClearAll: () => void;
}

export const CompareDrawer: React.FC<CompareDrawerProps> = ({
  comparedProducts,
  onRemoveProduct,
  onClearAll,
}) => {
  const [isOpenModal, setIsOpenModal] = useState(false);
  const [comparisonData, setComparisonData] = useState<ComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);

  if (comparedProducts.length === 0) return null;

  const handleOpenComparison = async () => {
    setIsOpenModal(true);
    setLoading(true);
    try {
      const res = await api.compareProducts(comparedProducts.map((p) => p.id));
      setComparisonData(res);
    } catch (err) {
      console.error('Error fetching comparison:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating Bottom Dock */}
      <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 w-full max-w-2xl px-4 animate-in slide-in-from-bottom duration-300">
        <div className="bg-card/95 backdrop-blur-md rounded-2xl border border-border/80 shadow-2xl p-3 sm:p-4 flex items-center justify-between">
          <div className="flex items-center space-x-3 overflow-x-auto py-1">
            <div className="flex items-center space-x-1.5 text-xs font-bold text-foreground shrink-0 pl-1">
              <Scale className="w-4 h-4 text-primary" />
              <span>Compare ({comparedProducts.length}/4):</span>
            </div>

            <div className="flex items-center space-x-2">
              {comparedProducts.map((prod) => (
                <div
                  key={prod.id}
                  className="relative group shrink-0 w-12 h-12 rounded-lg bg-muted border border-border/80 overflow-hidden"
                >
                  <img
                    src={prod.image_url || ''}
                    alt={prod.title}
                    className="w-full h-full object-cover"
                  />
                  <button
                    onClick={() => onRemoveProduct(prod.id)}
                    className="absolute inset-0 bg-black/60 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Remove item"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center space-x-2 shrink-0 ml-3">
            <button
              onClick={onClearAll}
              className="text-xs text-muted-foreground hover:text-foreground px-2 py-1 transition-colors"
            >
              Clear
            </button>
            <button
              onClick={handleOpenComparison}
              disabled={comparedProducts.length < 2}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-primary text-primary-foreground text-xs sm:text-sm font-semibold rounded-xl hover:opacity-95 disabled:opacity-40 transition-all shadow-sm"
            >
              <span>Compare Now</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Full Screen Comparison Modal */}
      {isOpenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div
            className="bg-card w-full max-w-5xl max-h-[92vh] rounded-2xl border border-border shadow-2xl overflow-hidden flex flex-col animate-in zoom-in-95 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-muted/40">
              <div className="flex items-center space-x-2.5">
                <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
                  <Scale className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="font-serif text-lg font-bold text-foreground leading-none">
                    Side-by-Side Product Comparison
                  </h3>
                  <span className="text-[10px] text-muted-foreground">
                    Grounded specification matrix with multi-factor trade-off synthesis
                  </span>
                </div>
              </div>

              <button
                onClick={() => setIsOpenModal(false)}
                className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 overflow-y-auto space-y-6 flex-1">
              {loading ? (
                <div className="py-16 text-center space-y-3">
                  <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
                  <p className="font-serif text-base font-medium text-foreground">
                    Evaluating trade-offs & comparing specs...
                  </p>
                </div>
              ) : comparisonData ? (
                <div className="space-y-6">
                  {/* Grounded LLM Trade-off Analysis */}
                  {comparisonData.llm_synthesis && (
                    <div className="bg-primary/5 border border-primary/20 rounded-xl p-5 space-y-2">
                      <div className="flex items-center space-x-2 text-xs font-bold text-primary uppercase tracking-wider">
                        <Sparkles className="w-4 h-4" />
                        <span>Synthesized Trade-Off Analysis</span>
                      </div>
                      <div className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">
                        {comparisonData.llm_synthesis}
                      </div>
                    </div>
                  )}

                  {/* Comparison Product Cards Top */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {comparisonData.products.map((item) => (
                      <div
                        key={item.product.id}
                        className="bg-muted/30 border border-border/80 rounded-xl p-4 space-y-3"
                      >
                        <div className="flex items-start space-x-3">
                          <img
                            src={item.product.image_url || ''}
                            alt={item.product.title}
                            className="w-16 h-16 rounded-lg object-cover bg-muted shrink-0"
                          />
                          <div>
                            <span className="text-[10px] font-bold uppercase text-primary">
                              {item.product.brand_name}
                            </span>
                            <h4 className="font-serif text-sm font-bold text-foreground line-clamp-2">
                              {item.product.title}
                            </h4>
                            <div className="text-base font-bold text-foreground mt-1">
                              {item.product.price !== null && item.product.price !== undefined
                                ? `$${item.product.price.toFixed(2)}`
                                : 'Price unavailable'}
                            </div>
                          </div>
                        </div>

                        {/* Strengths */}
                        {item.strengths.length > 0 && (
                          <div className="space-y-1">
                            <span className="text-[10px] font-bold uppercase text-secondary block">
                              Grounded Strengths
                            </span>
                            <ul className="text-xs space-y-0.5 text-muted-foreground">
                              {item.strengths.map((s, i) => (
                                <li key={i} className="flex items-start space-x-1.5">
                                  <CheckCircle2 className="w-3 h-3 text-secondary shrink-0 mt-0.5" />
                                  <span>{s}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Tradeoffs */}
                        {item.tradeoffs.length > 0 && (
                          <div className="space-y-1">
                            <span className="text-[10px] font-bold uppercase text-amber-700 block">
                              Considerations & Trade-Offs
                            </span>
                            <ul className="text-xs space-y-0.5 text-muted-foreground">
                              {item.tradeoffs.map((t, i) => (
                                <li key={i} className="flex items-start space-x-1.5">
                                  <AlertCircle className="w-3 h-3 text-amber-600 shrink-0 mt-0.5" />
                                  <span>{t}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Specification Matrix Table */}
                  {comparisonData.matrix && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                        Feature & Attribute Matrix
                      </h4>
                      <div className="border border-border/80 rounded-xl overflow-x-auto bg-card">
                        <table className="w-full text-xs text-left">
                          <thead className="bg-muted/50 border-b border-border text-foreground font-semibold">
                            <tr>
                              <th className="p-3">Attribute</th>
                              {comparisonData.products.map((p) => (
                                <th key={p.product.id} className="p-3">
                                  {p.product.title.slice(0, 28)}...
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border/60">
                            {Object.entries(comparisonData.matrix).map(([attr, vals]) => (
                              <tr key={attr} className="hover:bg-muted/20">
                                <td className="p-3 font-medium text-foreground bg-muted/20 w-44 capitalize">
                                  {attr}
                                </td>
                                {comparisonData.products.map((p) => {
                                  const rawVal = vals[p.product.id];
                                  const displayVal =
                                    attr.toLowerCase() === 'price' && (rawVal === 'NULL' || rawVal === '$NULL' || !rawVal)
                                      ? 'Price unavailable'
                                      : rawVal ?? '—';
                                  return (
                                    <td key={p.product.id} className="p-3 text-muted-foreground">
                                      {displayVal}
                                    </td>
                                  );
                                })}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </>
  );
};
