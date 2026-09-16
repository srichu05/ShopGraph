import React, { useState } from 'react';
import { ChevronDown, HelpCircle } from 'lucide-react';

interface FAQItem {
  question: string;
  answer: string;
}

export const FAQAccordion: React.FC = () => {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  const faqs: FAQItem[] = [
    {
      question: 'How does Graph-RAG differ from basic vector search?',
      answer:
        'Vector search retrieves documents based only on semantic surface similarity, which often hallucinates or ignores hard constraints (like exact prices, brands, or categories). Graph-RAG combines Cypher graph queries with vector ANN search: Cypher enforces deterministic relational filters and multi-hop relationships (e.g. co-purchases), while vector embeddings rank semantic nuances.',
    },
    {
      question: 'What is Bayesian rating shrinkage and why is it used?',
      answer:
        'A product with a single 5.0-star review is not better than a product with 4.8 stars across 2,840 verified purchases. ShopGraph applies Bayesian shrinkage to adjust raw ratings toward the category prior mean, heavily penalizing low-sample noise and ensuring trustworthy rankings.',
    },
    {
      question: 'How does ShopGraph prevent LLM hallucinations?',
      answer:
        'ShopGraph uses strict evidence fusion: the LLM is provided only retrieved graph facts, verified review snippets, and deterministic Cypher results. Every factual assertion in the generated answer includes a traceable superscript citation [1], [2] pointing to an inspected evidence item.',
    },
    {
      question: 'Why are some product prices marked as "Unlisted"?',
      answer:
        'In e-commerce datasets (like Amazon 2023), third-party seller listings or discontinued variants frequently lack verified prices. Instead of fabricating an arbitrary price, ShopGraph preserves strict integrity by marking missing prices as NULL/Unlisted, and flags this boundary in the limitations alert.',
    },
    {
      question: 'How does multi-hop co-purchase traversal work?',
      answer:
        'ShopGraph tracks verified reviewer purchase graphs. When user U reviews both Product A and Product B with verified purchase flags, a weighted co-purchase edge is established. This enables multi-hop traversal to discover realistic equipment chains (e.g., matching a high-impedance mic with a compatible USB audio interface).',
    },
  ];

  return (
    <section id="faq" className="py-20 bg-background">
      <div className="container mx-auto px-4 sm:px-6 max-w-4xl">
        <div className="text-center mb-12">
          <div className="inline-flex items-center space-x-1.5 text-xs font-semibold text-primary mb-2">
            <HelpCircle className="w-3.5 h-3.5" />
            <span>Frequently Asked Questions</span>
          </div>
          <h2 className="font-serif text-3xl font-bold text-foreground">
            Architecture & Reasoning FAQs
          </h2>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1">
            Understanding the algorithmic foundations of ShopGraph.
          </p>
        </div>

        <div className="space-y-3">
          {faqs.map((faq, index) => {
            const isOpen = openIndex === index;
            return (
              <div
                key={index}
                className="bg-card border border-border/80 rounded-xl overflow-hidden transition-colors"
              >
                <button
                  onClick={() => setOpenIndex(isOpen ? null : index)}
                  className="w-full px-5 py-4 flex items-center justify-between text-left text-sm sm:text-base font-semibold text-foreground hover:bg-muted/30 transition-colors"
                >
                  <span className="font-serif text-base">{faq.question}</span>
                  <ChevronDown
                    className={`w-4 h-4 text-muted-foreground shrink-0 transition-transform duration-200 ${
                      isOpen ? 'transform rotate-180 text-primary' : ''
                    }`}
                  />
                </button>

                {isOpen && (
                  <div className="px-5 pb-4 pt-1 text-xs sm:text-sm text-muted-foreground leading-relaxed border-t border-border/40 bg-muted/10">
                    {faq.answer}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
