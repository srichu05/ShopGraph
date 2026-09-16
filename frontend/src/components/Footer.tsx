import { GitGraph, ExternalLink, Activity } from 'lucide-react';
import { HealthStatus } from '../types';

interface FooterProps {
  health: HealthStatus | null;
}

export const Footer: React.FC<FooterProps> = ({ health }) => {
  const isBackendReachable = health !== null && health.status !== 'offline';
  const isNeo4jLive = isBackendReachable && health?.services?.neo4j?.status === 'connected';

  return (
    <footer className="bg-muted/40 border-t border-border/80 pt-16 pb-12 text-foreground">
      <div className="container mx-auto px-4 sm:px-6">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 pb-12 border-b border-border/60">
          {/* Col 1: Brand & Status (4 cols) */}
          <div className="md:col-span-4 space-y-4">
            <div className="flex items-center space-x-2.5">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground shadow-sm">
                <GitGraph className="w-4 h-4 text-white" />
              </div>
              <span className="font-serif text-xl font-bold tracking-tight text-foreground">
                ShopGraph
              </span>
            </div>

            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed max-w-sm">
              Explainable Graph-RAG E-Commerce Intelligence Platform with faithful multi-hop graph
              retrieval, Bayesian review intelligence, and transparent AI reasoning.
            </p>

            <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-card border border-border text-xs">
              <Activity className="w-3.5 h-3.5 text-muted-foreground" />
              <span>Neo4j Bolt:</span>
              <span
                className={`font-semibold px-1.5 py-0.5 rounded text-[10px] ${
                  isNeo4jLive ? 'bg-secondary/15 text-secondary' : 'bg-accent/30 text-amber-800'
                }`}
              >
                {isNeo4jLive
                  ? `Active (${health?.services?.neo4j?.uri || 'bolt://localhost:7687'})`
                  : 'Demo Catalog Active'}
              </span>
            </div>
          </div>

          {/* Col 2: Taxonomy (2 cols) */}
          <div className="md:col-span-3 space-y-3">
            <h4 className="font-serif text-sm font-bold text-foreground">Musical Taxonomy</h4>
            <ul className="space-y-2 text-xs text-muted-foreground">
              <li>
                <a href="#categories" className="hover:text-foreground transition-colors">
                  Guitars & Basses
                </a>
              </li>
              <li>
                <a href="#categories" className="hover:text-foreground transition-colors">
                  Microphones & Vocals
                </a>
              </li>
              <li>
                <a href="#categories" className="hover:text-foreground transition-colors">
                  USB Audio Interfaces
                </a>
              </li>
              <li>
                <a href="#categories" className="hover:text-foreground transition-colors">
                  Keyboards & Synthesizers
                </a>
              </li>
              <li>
                <a href="#categories" className="hover:text-foreground transition-colors">
                  Drums & Percussion
                </a>
              </li>
            </ul>
          </div>

          {/* Col 3: Engine (2 cols) */}
          <div className="md:col-span-2 space-y-3">
            <h4 className="font-serif text-sm font-bold text-foreground">Graph-RAG Engine</h4>
            <ul className="space-y-2 text-xs text-muted-foreground">
              <li>
                <a href="#how-it-works" className="hover:text-foreground transition-colors">
                  Hybrid Cypher + ANN
                </a>
              </li>
              <li>
                <a href="#how-it-works" className="hover:text-foreground transition-colors">
                  6-Factor Score Radar
                </a>
              </li>
              <li>
                <a href="#how-it-works" className="hover:text-foreground transition-colors">
                  Bayesian Shrinkage
                </a>
              </li>
              <li>
                <a href="#how-it-works" className="hover:text-foreground transition-colors">
                  Zero Hallucination
                </a>
              </li>
            </ul>
          </div>

          {/* Col 4: Links & Docs (3 cols) */}
          <div className="md:col-span-3 space-y-3">
            <h4 className="font-serif text-sm font-bold text-foreground">APIs & Specs</h4>
            <ul className="space-y-2 text-xs text-muted-foreground">
              <li>
                <a
                  href="/docs"
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center space-x-1.5 hover:text-foreground transition-colors"
                >
                  <span>FastAPI Swagger UI</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a
                  href="/redoc"
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center space-x-1.5 hover:text-foreground transition-colors"
                >
                  <span>ReDoc OpenAPI</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </li>
              <li>
                <a
                  href="https://github.com/srichu05/ShopGraph"
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center space-x-1.5 hover:text-foreground transition-colors"
                >
                  <svg className="w-3.5 h-3.5 fill-current" viewBox="0 0 24 24">
                    <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
                  </svg>
                  <span>GitHub Repository</span>
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between text-xs text-muted-foreground gap-4">
          <div>
            &copy; {new Date().getFullYear()} ShopGraph Platform. All rights reserved.
          </div>
          <div className="flex items-center space-x-4">
            <span>Built with React 19, TailwindCSS, Neo4j & FastApi</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
