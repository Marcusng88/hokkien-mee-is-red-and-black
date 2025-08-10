import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
  content: string;
  className?: string;
  isUserMessage?: boolean;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  className,
  isUserMessage = false,
}) => {
  return (
    <div className={cn("markdown-content", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        rehypePlugins={[rehypeHighlight, rehypeRaw]}
        components={{
          // Headings
          h1: ({ children }) => (
            <h1 className={cn(
              "text-lg font-bold mb-2 mt-4 first:mt-0",
              isUserMessage ? "text-white" : "text-gray-900"
            )}>
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className={cn(
              "text-base font-semibold mb-2 mt-3 first:mt-0",
              isUserMessage ? "text-white" : "text-gray-900"
            )}>
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className={cn(
              "text-sm font-semibold mb-1 mt-2 first:mt-0",
              isUserMessage ? "text-white" : "text-gray-900"
            )}>
              {children}
            </h3>
          ),
          
          // Paragraphs
          p: ({ children }) => (
            <p className={cn(
              "mb-2 last:mb-0 leading-relaxed",
              isUserMessage ? "text-white" : "text-gray-900"
            )}>
              {children}
            </p>
          ),
          
          // Lists
          ul: ({ children }) => (
            <ul className={cn(
              "list-disc list-inside mb-2 space-y-1",
              isUserMessage ? "text-white" : "text-gray-900"
            )}>
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className={cn(
              "list-decimal list-inside mb-2 space-y-1",
              isUserMessage ? "text-white" : "text-gray-900"
            )}>
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className={cn(
              "leading-relaxed",
              isUserMessage ? "text-white" : "text-gray-900"
            )}>
              {children}
            </li>
          ),
          
          // Emphasis
          strong: ({ children }) => (
            <strong className={cn(
              "font-bold",
              isUserMessage ? "text-white" : "text-gray-900"
            )}>
              {children}
            </strong>
          ),
          em: ({ children }) => (
            <em className={cn(
              "italic",
              isUserMessage ? "text-white" : "text-gray-900"
            )}>
              {children}
            </em>
          ),
          
          // Code
          code: ({ children, className }) => {
            const isInline = !className;
            return isInline ? (
              <code className={cn(
                "px-1 py-0.5 rounded text-xs font-mono",
                isUserMessage 
                  ? "bg-white/20 text-white" 
                  : "bg-gray-200 text-gray-800"
              )}>
                {children}
              </code>
            ) : (
              <code className={cn(
                "block p-2 rounded text-xs font-mono overflow-x-auto",
                isUserMessage 
                  ? "bg-white/10 text-white" 
                  : "bg-gray-100 text-gray-800"
              )}>
                {children}
              </code>
            );
          },
          
          // Code blocks
          pre: ({ children }) => (
            <pre className={cn(
              "p-3 rounded-md text-xs font-mono overflow-x-auto mb-2",
              isUserMessage 
                ? "bg-white/10 text-white" 
                : "bg-gray-100 text-gray-800"
            )}>
              {children}
            </pre>
          ),
          
          // Links
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                "underline hover:no-underline",
                isUserMessage 
                  ? "text-blue-200 hover:text-white" 
                  : "text-blue-600 hover:text-blue-800"
              )}
            >
              {children}
            </a>
          ),
          
          // Blockquotes
          blockquote: ({ children }) => (
            <blockquote className={cn(
              "border-l-4 pl-3 py-1 mb-2 italic",
              isUserMessage 
                ? "border-white/30 text-white/90" 
                : "border-gray-300 text-gray-700"
            )}>
              {children}
            </blockquote>
          ),
          
          // Tables
          table: ({ children }) => (
            <div className="overflow-x-auto mb-2">
              <table className={cn(
                "min-w-full border-collapse text-xs",
                isUserMessage ? "text-white" : "text-gray-900"
              )}>
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className={cn(
              "border px-2 py-1 font-semibold text-left",
              isUserMessage 
                ? "border-white/30 bg-white/10" 
                : "border-gray-300 bg-gray-50"
            )}>
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className={cn(
              "border px-2 py-1",
              isUserMessage 
                ? "border-white/30" 
                : "border-gray-300"
            )}>
              {children}
            </td>
          ),
          
          // Horizontal rule
          hr: () => (
            <hr className={cn(
              "my-3 border-t",
              isUserMessage 
                ? "border-white/30" 
                : "border-gray-300"
            )} />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
