import ReactMarkdown from "react-markdown";

type MarkdownProps = {
  content?: string;
};

export function Markdown({ content }: MarkdownProps) {
  if (!content) return null;
  return (
    <div className="markdown-content">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  );
}
