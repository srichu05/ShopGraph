import React from 'react';
import { GitGraph, ShieldCheck, Cpu, ArrowRight } from 'lucide-react';

export const HowItWorks: React.FC = () => {
  const steps = [
    {
      num: '01',
      title: 'Knowledge Graph Topology',
      badge: 'Neo4j Graph Database',
      desc: 'Instead of flat text embeddings, ShopGraph structures products, brands, hierarchical categories, and verified reviewers into an interconnected graph with explicit constraints.',
      icon: GitGraph,
      color: 'text-primary',
      bg: 'bg-primary/10',
    },
    {
      num: '02',
      title: 'Hybrid Graph-RAG Retrieval',
      badge: 'Cypher + Vector ANN',
      desc: 'Natural language queries are parsed into structured constraints. Safe read-only Cypher filters hard boundaries (price ceilings, categories) while embeddings rank semantic suitability.',
      icon: Cpu,
      color: 'text-secondary',
      bg: 'bg-secondary/10',
    },
    {
      num: '03',
      title: 'Faithful Grounding & Transparency',
      badge: 'Zero Hallucination',
      desc: 'The LLM synthesizes natural responses strictly referencing retrieved graph facts. Every claim is cited with numerical footnotes and backed by a 6-factor explainability breakdown.',
      icon: ShieldCheck,
      color: 'text-amber-600',
      bg: 'bg-amber-500/10',
    },
  ];

  return (
    <section id="how-it-works" className="py-20 bg-muted/20 border-b border-border/60">
      <div className="container mx-auto px-4 sm:px-6">
        <div className="max-w-2xl mx-auto text-center mb-16">
          <span className="text-xs font-bold uppercase tracking-wider text-primary bg-primary/10 px-2.5 py-0.5 rounded-full mb-3 inline-block">
            System Architecture
          </span>
          <h2 className="font-serif text-3xl sm:text-4xl font-bold text-foreground mb-4">
            How Explainable Graph-RAG Works
          </h2>
          <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
            Standard RAG blindly retrieves unstructured chunks. ShopGraph grounds every answer in
            verifiable relational paths and Bayesian review intelligence.
          </p>
        </div>

        {/* 3 Steps Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {steps.map((step) => {
            const Icon = step.icon;
            return (
              <div
                key={step.num}
                className="bg-card rounded-2xl border border-border/80 p-8 flex flex-col justify-between hover:shadow-lg hover:border-primary/40 transition-all duration-300 relative group"
              >
                <div>
                  <div className="flex items-center justify-between mb-6">
                    <span className="font-serif text-3xl font-bold text-foreground/20 group-hover:text-primary/40 transition-colors">
                      {step.num}
                    </span>
                    <div className={`p-3 rounded-xl ${step.bg} ${step.color}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                  </div>

                  <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-2">
                    {step.badge}
                  </span>
                  <h3 className="font-serif text-xl font-bold text-foreground mb-3">
                    {step.title}
                  </h3>
                  <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                    {step.desc}
                  </p>
                </div>

                <div className="mt-6 pt-4 border-t border-border/50 flex items-center text-xs font-semibold text-primary">
                  <span>Explore in Engine</span>
                  <ArrowRight className="w-3.5 h-3.5 ml-1 transform group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
