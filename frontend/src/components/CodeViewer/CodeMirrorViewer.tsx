import { useEffect, useRef } from 'react';
import { basicSetup } from 'codemirror';
import { EditorView } from '@codemirror/view';
import { EditorState, Compartment } from '@codemirror/state';
import { html } from '@codemirror/lang-html';
import { oneDark } from '@codemirror/theme-one-dark';

interface CodeMirrorViewerProps {
  code: string;
  onContentChange?: (newCode: string) => void;
  disabled?: boolean;
}

const themeCompartment = new Compartment();
const editableCompartment = new Compartment();
const readOnlyCompartment = new Compartment();

function getThemeExtension() {
  const attr = document.documentElement.getAttribute('data-theme');
  return attr === 'light' ? [] : oneDark;
}

export default function CodeMirrorViewer({ code, onContentChange, disabled = true }: CodeMirrorViewerProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const onContentChangeRef = useRef(onContentChange);

  // Keep callback ref current
  useEffect(() => {
    onContentChangeRef.current = onContentChange;
  }, [onContentChange]);

  // Create editor once on mount
  useEffect(() => {
    if (!editorRef.current) return;

    const state = EditorState.create({
      doc: code,
      extensions: [
        basicSetup,
        html(),
        themeCompartment.of(getThemeExtension()),
        editableCompartment.of(EditorView.editable.of(!disabled)),
        readOnlyCompartment.of(EditorState.readOnly.of(disabled)),
        EditorView.lineWrapping,
        EditorView.updateListener.of((update) => {
          if (update.docChanged && onContentChangeRef.current) {
            onContentChangeRef.current(update.state.doc.toString());
          }
        }),
      ],
    });

    viewRef.current = new EditorView({
      state,
      parent: editorRef.current,
    });

    // Listen for theme attribute changes via MutationObserver
    const observer = new MutationObserver(() => {
      viewRef.current?.dispatch({
        effects: themeCompartment.reconfigure(getThemeExtension()),
      });
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-theme'],
    });

    return () => {
      observer.disconnect();
      viewRef.current?.destroy();
      viewRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update editable/readOnly when disabled prop changes
  useEffect(() => {
    if (!viewRef.current) return;
    viewRef.current.dispatch({
      effects: [
        editableCompartment.reconfigure(EditorView.editable.of(!disabled)),
        readOnlyCompartment.reconfigure(EditorState.readOnly.of(disabled)),
      ],
    });
  }, [disabled]);

  // Update document when code changes externally
  useEffect(() => {
    if (!viewRef.current) return;

    const currentDoc = viewRef.current.state.doc.toString();
    if (currentDoc !== code) {
      viewRef.current.dispatch({
        changes: {
          from: 0,
          to: currentDoc.length,
          insert: code,
        },
      });
    }
  }, [code]);

  return <div ref={editorRef} className="codemirror-container" />;
}
