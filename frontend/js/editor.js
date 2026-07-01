// Monaco Editor Initialization and Helper API

let editorInstance = null;

function initializeMonacoEditor(initialCode) {
    return new Promise((resolve, reject) => {
        try {
            // Configure Monaco Loader path
            require.config({
                paths: {
                    vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs'
                }
            });

            // Load and instantiate
            require(['vs/editor/editor.main'], function() {
                const editorContainer = document.getElementById('editor');
                if (!editorContainer) {
                    reject(new Error("Editor target container not found in DOM"));
                    return;
                }

                editorInstance = monaco.editor.create(editorContainer, {
                    value: initialCode,
                    language: 'python',
                    theme: 'vs-dark',
                    automaticLayout: true,
                    fontSize: 14,
                    fontFamily: "'Fira Code', var(--font-mono)",
                    fontLigatures: true,
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    padding: { top: 16, bottom: 16 },
                    renderLineHighlight: 'all',
                    cursorBlinking: 'smooth',
                    cursorSmoothCaretAnimation: 'on'
                });

                resolve(editorInstance);
            });
        } catch (err) {
            reject(err);
        }
    });
}

function getEditorCode() {
    return editorInstance ? editorInstance.getValue() : '';
}

function setEditorCode(code) {
    if (editorInstance) {
        editorInstance.setValue(code);
    }
}
