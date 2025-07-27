"use client";

interface CodePreviewProps {
    code: string;
}

const CodePreview = ({ code }: CodePreviewProps) => {
    return (
        <pre style={{ background: '#2d2d2d', color: '#f1f1f1', padding: '10px', borderRadius: '5px' }}>
            <code>
                {code}
            </code>
        </pre>
    );
};

export default CodePreview;