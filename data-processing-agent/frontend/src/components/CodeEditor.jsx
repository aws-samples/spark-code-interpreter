import React from 'react';
import { Box } from '@cloudscape-design/components';
import Editor from '@monaco-editor/react';

const CodeEditor = ({ code, onChange, language = 'python' }) => {
  return (
    <Box>
      <Editor
        height="500px"
        language={language}
        value={code}
        onChange={(value) => onChange(value || '')}
        theme="vs-dark"
        options={{
          minimap: { enabled: true },
          fontSize: 14,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 4,
          wordWrap: 'on'
        }}
      />
    </Box>
  );
};

export default CodeEditor;
