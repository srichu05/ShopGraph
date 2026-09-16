import React, { useMemo } from 'react';
import { Info } from 'lucide-react';
import { ProductSummary } from '../types';

interface GroundedAnswerRendererProps {
  content: string;
  products?: ProductSummary[];
  onSelectProduct?: (product: ProductSummary) => void;
}

interface InlineToken {
  type: 'text' | 'bold' | 'code' | 'italic';
  content: string;
}

type MarkdownBlock =
  | { type: 'heading'; level: number; text: string }
  | { type: 'numbered-item'; number: string; titleLine: string; subItems: string[] }
  | { type: 'bullet-list'; items: string[] }
  | { type: 'paragraph'; text: string }
  | { type: 'note'; text: string };

function parseInlineTokens(text: string): InlineToken[] {
  const tokens: InlineToken[] = [];
  const pattern = /(\*\*[^*]+?\*\*|`[^`]+?`|\*[^*]+?\*)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      tokens.push({
        type: 'text',
        content: text.slice(lastIndex, match.index),
      });
    }

    const raw = match[0];
    if (raw.startsWith('**') && raw.endsWith('**')) {
      tokens.push({
        type: 'bold',
        content: raw.slice(2, -2),
      });
    } else if (raw.startsWith('`') && raw.endsWith('`')) {
      tokens.push({
        type: 'code',
        content: raw.slice(1, -1),
      });
    } else if (raw.startsWith('*') && raw.endsWith('*')) {
      tokens.push({
        type: 'italic',
        content: raw.slice(1, -1),
      });
    }

    lastIndex = match.index + raw.length;
  }

  if (lastIndex < text.length) {
    tokens.push({
      type: 'text',
      content: text.slice(lastIndex),
    });
  }

  return tokens;
}

function findMatchingProduct(
  text: string,
  lineContext: string,
  products: ProductSummary[]
): ProductSummary | null {
  if (!products || products.length === 0) return null;

  // 1. Check if the line context contains a specific known ASIN
  const asinMatches = lineContext.matchAll(/\b([A-Z0-9]{10})\b/g);
  for (const m of asinMatches) {
    const asin = m[1];
    const match = products.find((p) => p.id === asin);
    if (match) return match;
  }

  const cleanText = text.trim();
  if (cleanText.length < 3) return null;

  // 2. Exact ASIN match in the bold text itself
  const directId = products.find((p) => p.id.toUpperCase() === cleanText.toUpperCase());
  if (directId) return directId;

  // 3. Exact title match (case-insensitive)
  const normText = cleanText.toLowerCase();
  const exact = products.find((p) => p.title.trim().toLowerCase() === normText);
  if (exact) return exact;

  // 4. Prefix or substring match (must be descriptive, at least 10 chars)
  if (cleanText.length >= 10) {
    const prefixMatch = products.find((p) => {
      const normTitle = p.title.trim().toLowerCase();
      return normTitle.startsWith(normText) || normText.startsWith(normTitle);
    });
    if (prefixMatch) return prefixMatch;

    // Word token overlap match (for titles with slightly differing model suffix or punctuation)
    const textWords = normText.replace(/[^a-z0-9 ]/g, ' ').split(/\s+/).filter((w) => w.length > 2);
    if (textWords.length >= 3) {
      for (const p of products) {
        const normTitle = p.title.trim().toLowerCase();
        const matchCount = textWords.filter((w) => normTitle.includes(w)).length;
        if (matchCount >= 3 && matchCount >= textWords.length * 0.7) {
          return p;
        }
      }
    }
  }

  return null;
}

function parseMarkdownBlocks(text: string): MarkdownBlock[] {
  const lines = text.split('\n');
  const blocks: MarkdownBlock[] = [];
  let i = 0;

  while (i < lines.length) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    if (!trimmed) {
      i++;
      continue;
    }

    // 1. Heading: # Heading
    const headingMatch = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      blocks.push({
        type: 'heading',
        level: headingMatch[1].length,
        text: headingMatch[2],
      });
      i++;
      continue;
    }

    // 2. Note / Disclaimer: *Note: ...*
    if (
      (trimmed.startsWith('*Note:') || trimmed.startsWith('_Note:') || trimmed.startsWith('*Disclaimer:')) &&
      (trimmed.endsWith('*') || trimmed.endsWith('_'))
    ) {
      const noteContent = trimmed.slice(1, -1).trim();
      blocks.push({
        type: 'note',
        text: noteContent,
      });
      i++;
      continue;
    }

    // 3. Numbered Item: 1. ...
    const numberedMatch = trimmed.match(/^(\d+)\.\s+(.+)$/);
    if (numberedMatch) {
      const num = numberedMatch[1];
      const titleLine = numberedMatch[2];
      const subItems: string[] = [];
      i++;

      // Collect sub-bullets belonging to this numbered item
      while (i < lines.length) {
        const nextRaw = lines[i];
        const nextTrimmed = nextRaw.trim();
        if (!nextTrimmed) {
          // Look ahead to check if the next line is a continuation sub-bullet
          if (i + 1 < lines.length && lines[i + 1].trim().match(/^[-*•]\s+/)) {
            i++;
            continue;
          }
          break;
        }

        const subMatch = nextTrimmed.match(/^[-*•]\s+(.+)$/);
        // Indented sub-bullets or bullet items under the numbered entry
        if (subMatch && (nextRaw.startsWith(' ') || nextRaw.startsWith('\t') || subItems.length > 0 || nextTrimmed.startsWith('- Price:') || nextTrimmed.startsWith('- Category:'))) {
          subItems.push(subMatch[1]);
          i++;
        } else {
          break;
        }
      }

      blocks.push({
        type: 'numbered-item',
        number: num,
        titleLine,
        subItems,
      });
      continue;
    }

    // 4. Standalone Bullet Item: - Item or * Item
    const bulletMatch = trimmed.match(/^[-*•]\s+(.+)$/);
    if (bulletMatch) {
      const items: string[] = [bulletMatch[1]];
      i++;
      while (i < lines.length) {
        const nextTrimmed = lines[i].trim();
        const nextBullet = nextTrimmed.match(/^[-*•]\s+(.+)$/);
        if (nextBullet) {
          items.push(nextBullet[1]);
          i++;
        } else if (!nextTrimmed) {
          break;
        } else {
          break;
        }
      }
      blocks.push({
        type: 'bullet-list',
        items,
      });
      continue;
    }

    // 5. Regular paragraph
    let paraText = trimmed;
    i++;
    while (i < lines.length) {
      const nextTrimmed = lines[i].trim();
      if (!nextTrimmed || nextTrimmed.match(/^(\d+\.|[-*•]|#{1,4}|\*(Note:|Disclaimer:))/)) {
        break;
      }
      paraText += ' ' + nextTrimmed;
      i++;
    }
    blocks.push({
      type: 'paragraph',
      text: paraText,
    });
  }

  return blocks;
}

export const GroundedAnswerRenderer: React.FC<GroundedAnswerRendererProps> = ({
  content,
  products = [],
  onSelectProduct,
}) => {
  const blocks = useMemo(() => parseMarkdownBlocks(content), [content]);

  const renderInline = (text: string, contextLine: string) => {
    const tokens = parseInlineTokens(text);

    return tokens.map((token, idx) => {
      if (token.type === 'bold') {
        const matchedProduct = findMatchingProduct(token.content, contextLine, products);

        if (matchedProduct && onSelectProduct) {
          return (
            <button
              key={idx}
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onSelectProduct(matchedProduct);
              }}
              className="font-bold text-primary hover:text-primary/80 underline decoration-primary/50 hover:decoration-primary transition-colors cursor-pointer text-left inline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:ring-offset-1 rounded-sm"
              title={`View ${matchedProduct.title} in Knowledge Graph`}
              aria-label={`Open product details for ${matchedProduct.title}`}
            >
              {token.content}
            </button>
          );
        }

        return (
          <strong key={idx} className="font-bold text-foreground">
            {token.content}
          </strong>
        );
      }

      if (token.type === 'code') {
        return (
          <code
            key={idx}
            className="px-1.5 py-0.5 mx-0.5 rounded bg-muted/80 font-mono text-xs font-medium text-foreground/90 border border-border/50"
          >
            {token.content}
          </code>
        );
      }

      if (token.type === 'italic') {
        return (
          <em key={idx} className="italic text-foreground/90">
            {token.content}
          </em>
        );
      }

      return <React.Fragment key={idx}>{token.content}</React.Fragment>;
    });
  };

  return (
    <div className="space-y-4 text-foreground">
      {blocks.map((block, bIdx) => {
        if (block.type === 'heading') {
          return (
            <h4
              key={bIdx}
              className="font-serif text-base sm:text-lg font-bold text-foreground mt-4 mb-2 first:mt-0"
            >
              {renderInline(block.text, block.text)}
            </h4>
          );
        }

        if (block.type === 'numbered-item') {
          return (
            <div
              key={bIdx}
              className="p-3.5 sm:p-4 rounded-xl bg-muted/30 border border-border/70 hover:border-primary/40 transition-colors space-y-2.5"
            >
              <div className="flex items-start space-x-3">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-primary/10 text-primary text-xs font-bold shrink-0 mt-0.5 select-none">
                  {block.number}
                </span>
                <div className="text-sm sm:text-base leading-relaxed text-foreground flex-1">
                  {renderInline(block.titleLine, block.titleLine)}
                </div>
              </div>

              {block.subItems.length > 0 && (
                <div className="ml-9 space-y-1 text-xs sm:text-sm text-muted-foreground border-l-2 border-primary/25 pl-3 pt-0.5">
                  {block.subItems.map((sub, sIdx) => (
                    <div key={sIdx} className="leading-relaxed flex items-center space-x-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-primary/50 shrink-0" />
                      <div>{renderInline(sub, sub)}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        }

        if (block.type === 'bullet-list') {
          return (
            <ul key={bIdx} className="space-y-1.5 pl-2 text-sm sm:text-base text-foreground">
              {block.items.map((item, idx) => (
                <li key={idx} className="flex items-start space-x-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary/60 shrink-0 mt-2" />
                  <span className="leading-relaxed">{renderInline(item, item)}</span>
                </li>
              ))}
            </ul>
          );
        }

        if (block.type === 'note') {
          return (
            <div
              key={bIdx}
              className="border-t border-border/60 pt-3 mt-4 text-xs text-muted-foreground italic flex items-center space-x-2"
            >
              <Info className="w-3.5 h-3.5 text-primary/70 shrink-0" />
              <span>{renderInline(block.text, block.text)}</span>
            </div>
          );
        }

        return (
          <p key={bIdx} className="text-sm sm:text-base text-foreground leading-relaxed">
            {renderInline(block.text, block.text)}
          </p>
        );
      })}
    </div>
  );
};
