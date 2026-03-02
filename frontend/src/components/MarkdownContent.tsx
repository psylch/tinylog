import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface MarkdownContentProps {
  content: string;
  className?: string;
}

export default function MarkdownContent({ content, className }: MarkdownContentProps) {
  return (
    <div className={`markdown-content ${className ?? ''}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className: codeClassName, children, ...props }) {
            const match = /language-(\w+)/.exec(codeClassName || '');
            const inline = !match && !String(children).includes('\n');
            if (inline) {
              return <code className={codeClassName} {...props}>{children}</code>;
            }
            const theme = document.documentElement.dataset.theme === 'light' ? oneLight : oneDark;
            return (
              <SyntaxHighlighter
                style={theme}
                language={match?.[1] || 'text'}
                PreTag="div"
                customStyle={{
                  margin: 0,
                  borderRadius: '0.375rem',
                  fontSize: '0.75rem',
                  lineHeight: 1.6,
                }}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            );
          },
          a({ children, href, ...props }) {
            return (
              <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
                {children}
              </a>
            );
          },
          img({ src, alt, ...props }) {
            return <img src={src} alt={alt ?? ''} {...props} />;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
