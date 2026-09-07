import "./markdown.css";
import { useState } from "react";
import { Copy, Check, Download } from "lucide-react";
import rehypeExternalLinks from "rehype-external-links";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

// ============================================================================
// Ce fichier regroupe tout ce qui concerne le rendu markdown partagé entre
// AIMessage, HumanMessage et les blocs "Réflexion" (ai_human_messages.tsx) :
//   - `markdownComponents` : à passer à ReactMarkdown via `components={...}`
//   - `rehypePlugins`      : à passer à ReactMarkdown via `rehypePlugins={...}`
// Import minimal côté consommateur :
//   import { markdownComponents, rehypePlugins } from "./markdown_renderer";
//   <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={rehypePlugins} components={markdownComponents}>
// ============================================================================

// ----------------------------------------------------------------------------
// Extraction du texte brut d'un noeud hast (arbre passé par react-markdown
// via la prop `node`). Sert à reconstruire les données d'un <table> pour
// pouvoir les copier / télécharger, indépendamment du rendu React.
// ----------------------------------------------------------------------------

function hastText(node: any): string {
    if (!node) return "";
    if (node.type === "text") return node.value || "";
    if (Array.isArray(node.children)) return node.children.map(hastText).join("");
    return "";
}

function extractTableRows(tableNode: any): string[][] {
    const rows: string[][] = [];
    const sections = (tableNode?.children || []).filter(
        (c: any) => c.type === "element" && (c.tagName === "thead" || c.tagName === "tbody")
    );
    for (const section of sections) {
        for (const tr of section.children || []) {
            if (tr.type !== "element" || tr.tagName !== "tr") continue;
            const cells = (tr.children || []).filter(
                (c: any) => c.type === "element" && (c.tagName === "th" || c.tagName === "td")
            );
            rows.push(cells.map((c: any) => hastText(c).trim()));
        }
    }
    return rows;
}

function rowsToMarkdown(rows: string[][]): string {
    if (!rows.length) return "";
    const esc = (s: string) => s.replace(/\|/g, "\\|");
    const [header, ...body] = rows;
    const lines = [
        `| ${header.map(esc).join(" | ")} |`,
        `| ${header.map(() => "---").join(" | ")} |`,
        ...body.map((r) => `| ${r.map(esc).join(" | ")} |`),
    ];
    return lines.join("\n");
}

function rowsToCSV(rows: string[][]): string {
    const esc = (s: string) => (/[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s);
    return rows.map((r) => r.map(esc).join(",")).join("\n");
}

// extension de fichier à utiliser pour le téléchargement d'un bloc de code,
// selon le langage détecté par la fence markdown (```python, ```bash, ...)
const LANG_TO_EXT: Record<string, string> = {
    python: "py",
    javascript: "js",
    typescript: "ts",
    tsx: "tsx",
    jsx: "jsx",
    bash: "sh",
    shell: "sh",
    sh: "sh",
    json: "json",
    yaml: "yaml",
    yml: "yml",
    sql: "sql",
    html: "html",
    css: "css",
    dockerfile: "Dockerfile",
    go: "go",
    rust: "rs",
    java: "java",
    c: "c",
    cpp: "cpp",
    text: "txt",
};

// ============================================================================
// MARKDOWN — bloc de code avec header (langage + copier + télécharger)
// ============================================================================

function CodeBlock({ className, children }: any) {
    const [copied, setCopied] = useState(false);
    const match = /language-(\w+)/.exec(className || "");
    const lang = match?.[1]?.toLowerCase() || "text";
    const code = String(children).replace(/\n$/, "");

    // pas de fence de langage => code inline, style discret dans le texte
    if (!match) {
        return <code className="inline-code">{children}</code>;
    }

    const handleCopy = async (e: React.MouseEvent) => {
        e.stopPropagation();
        try {
            await navigator.clipboard.writeText(code);
            setCopied(true);
            setTimeout(() => setCopied(false), 1200);
        } catch {
            // pas critique si le clipboard n'est pas dispo
        }
    };

    const handleDownload = (e: React.MouseEvent) => {
        e.stopPropagation();
        const ext = LANG_TO_EXT[lang] || "txt";
        const blob = new Blob([code], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `snippet.${ext}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="code-block-wrapper">
            <div className="code-block-header">
                <span className="code-block-lang">{lang}</span>
                <div className="code-block-actions">
                    <button onClick={handleCopy} title="Copier le code">
                        {copied ? <Check size={12} /> : <Copy size={12} />}
                    </button>
                    <button onClick={handleDownload} title="Télécharger le fichier">
                        <Download size={12} />
                    </button>
                </div>
            </div>
            <SyntaxHighlighter
                language={lang}
                style={oneDark}
                customStyle={{ margin: 0, background: "transparent", fontSize: "12.5px" }}
            >
                {code}
            </SyntaxHighlighter>
        </div>
    );
}

// ============================================================================
// MARKDOWN — tableau avec header (copier en Markdown / télécharger en CSV)
// ============================================================================

function MarkdownTable({ node, children }: any) {
    const [copied, setCopied] = useState(false);
    const rows = node ? extractTableRows(node) : [];

    const handleCopy = async (e: React.MouseEvent) => {
        e.stopPropagation();
        try {
            await navigator.clipboard.writeText(rowsToMarkdown(rows));
            setCopied(true);
            setTimeout(() => setCopied(false), 1200);
        } catch {
            // pas critique si le clipboard n'est pas dispo
        }
    };

    const handleDownload = (e: React.MouseEvent) => {
        e.stopPropagation();
        const blob = new Blob([rowsToCSV(rows)], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "tableau.csv";
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="md-table-wrapper">
            {rows.length > 0 && (
                <div className="md-table-header">
                    <span className="md-table-label">tableau</span>
                    <div className="md-table-actions">
                        <button onClick={handleCopy} title="Copier en Markdown">
                            {copied ? <Check size={12} /> : <Copy size={12} />}
                        </button>
                        <button onClick={handleDownload} title="Télécharger en CSV">
                            <Download size={12} />
                        </button>
                    </div>
                </div>
            )}
            <div className="md-table-scroll">
                <table className="md-table">{children}</table>
            </div>
        </div>
    );
}

// ============================================================================
// EXPORTS — à consommer depuis ai_human_messages.tsx (ou tout autre
// composant qui affiche du markdown généré par Coralie ou l'utilisateur).
// ============================================================================

export const markdownComponents = {
    code: CodeBlock,
    table: MarkdownTable,
    thead: ({ children }: any) => <thead className="md-thead">{children}</thead>,
    th: ({ children }: any) => <th className="md-th">{children}</th>,
    td: ({ children }: any) => <td className="md-td">{children}</td>,
    a: ({ href, children }: any) => (
        <a href={href} className="md-link">
            {children}
        </a>
    ),
};

export const rehypePlugins = [
    [rehypeExternalLinks, { target: "_blank", rel: ["noopener", "noreferrer"] }] as any,
];