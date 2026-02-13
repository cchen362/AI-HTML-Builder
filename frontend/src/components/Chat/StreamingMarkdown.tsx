import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import CopyButton from '../CodeViewer/CopyButton';
import './StreamingMarkdown.css';

interface StreamingMarkdownProps {
  content: string;
  isStreaming?: boolean;
}

export default function StreamingMarkdown({ content, isStreaming = false }: StreamingMarkdownProps) {
  return (
    <div className={`markdown-content ${isStreaming ? 'streaming' : ''}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          code(props) {
            const { children, className, ...rest } = props;
            const match = /language-(\w+)/.exec(className || '');
            const isBlock = Boolean(match) || (typeof children === 'string' && children.includes('\n'));

            if (isBlock) {
              return (
                <div className="code-block-wrapper">
                  <div className="code-block-header">
                    <span className="code-block-lang">{match ? match[1] : 'code'}</span>
                    <CopyButton text={String(children).replace(/\n$/, '')} label="Copy" />
                  </div>
                  <code className={className} {...rest}>
                    {children}
                  </code>
                </div>
              );
            }

            return (
              <code className={className} {...rest}>
                {children}
              </code>
            );
          },
          a(props) {
            const { children, href, ...rest } = props;
            return (
              <a href={href} target="_blank" rel="noopener noreferrer" {...rest}>
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
      {isStreaming && <span className="streaming-cursor" />}
    </div>
  );
}
