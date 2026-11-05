import { useEffect, useRef } from 'react';

export interface UseClipboardPasteOptions {
  onImagePasted: (file: File) => void;
  onTextPasted?: (text: string, isHtml: boolean) => void;
  enabled?: boolean;
}

export function useClipboardPaste({
  onImagePasted,
  onTextPasted,
  enabled = true,
}: UseClipboardPasteOptions) {
  const onImageRef = useRef(onImagePasted);
  const onTextRef = useRef(onTextPasted);
  onImageRef.current = onImagePasted;
  onTextRef.current = onTextPasted;

  useEffect(() => {
    if (!enabled) return;

    const handlePaste = (e: ClipboardEvent) => {
      const clipboardData = e.clipboardData;
      if (!clipboardData) return;

      const items = clipboardData.items;
      if (!items) return;

      // 1. Check for image files in clipboard
      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.type.startsWith('image/')) {
          const file = item.getAsFile();
          if (file) {
            e.preventDefault();
            e.stopPropagation();

            // Create a descriptive file name with timestamp
            const ext = item.type.split('/')[1] || 'png';
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            const namedFile = new File([file], `clipboard-${timestamp}.${ext}`, {
              type: file.type,
            });

            onImageRef.current(namedFile);
            return;
          }
        }
      }

      // 2. Check for HTML tables or rich text when pasted outside standard inputs
      const target = e.target as HTMLElement | null;
      const isInput =
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.closest('.cm-editor') !== null ||
          target.isContentEditable);

      // If user pasted outside the code editor / text inputs, capture rich text or html
      if (!isInput && onTextRef.current) {
        const html = clipboardData.getData('text/html');
        const text = clipboardData.getData('text/plain');

        if (html && (html.includes('<table') || html.includes('<h1') || html.includes('<p'))) {
          e.preventDefault();
          onTextRef.current(html, true);
        } else if (text && text.trim().length > 0) {
          e.preventDefault();
          onTextRef.current(text, false);
        }
      }
    };

    window.addEventListener('paste', handlePaste);
    return () => {
      window.removeEventListener('paste', handlePaste);
    };
  }, [enabled]);
}
