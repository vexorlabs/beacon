import Editor from "@monaco-editor/react";

interface PromptEditorProps {
  initialValue: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
}

export default function PromptEditor({
  initialValue,
  onChange,
  readOnly = false,
}: PromptEditorProps) {
  return (
    <Editor
      height="200px"
      defaultLanguage="json"
      defaultValue={initialValue}
      onChange={(value) => onChange(value ?? "")}
      theme="vs-dark"
      options={{
        minimap: { enabled: false },
        lineNumbers: "on",
        wordWrap: "on",
        scrollBeyondLastLine: false,
        fontSize: 12,
        readOnly,
        tabSize: 2,
      }}
    />
  );
}
