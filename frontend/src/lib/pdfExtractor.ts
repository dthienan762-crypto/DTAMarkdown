/**
 * DTAMarkdown Studio - Browser-Native PDF Text & Layout Extractor
 * Pure TypeScript / Web-Standards implementation (Zero external dependencies).
 * Extracts digital text, headings, tables, and KaTeX formulas directly from PDF streams
 * using native Web DecompressionStream('deflate').
 */

function decodePdfHexString(hex: string): string {
  const cleanHex = hex.trim();
  if (!cleanHex) return '';

  // 1. UTF-16BE BOM marker
  if (cleanHex.toLowerCase().startsWith('feff')) {
    let result = '';
    for (let i = 4; i < cleanHex.length; i += 4) {
      const charCode = parseInt(cleanHex.substring(i, i + 4), 16);
      if (!isNaN(charCode)) {
        result += String.fromCharCode(charCode);
      }
    }
    return result;
  }

  // 2. Multi-byte UTF-8 bytes
  try {
    const bytes: number[] = [];
    for (let i = 0; i < cleanHex.length; i += 2) {
      bytes.push(parseInt(cleanHex.substring(i, i + 2), 16));
    }
    const decoded = new TextDecoder('utf-8', { fatal: false }).decode(new Uint8Array(bytes));
    if (decoded && !decoded.includes('\uFFFD')) {
      return decoded;
    }
  } catch {
    // fallback to character-by-character
  }

  // 3. Fallback: Standard ASCII / Latin1 character codes
  let result = '';
  for (let i = 0; i < cleanHex.length; i += 2) {
    const code = parseInt(cleanHex.substring(i, i + 2), 16);
    if (!isNaN(code)) {
      result += String.fromCharCode(code);
    }
  }
  return result;
}

function decodePdfLiteralString(str: string): string {
  // Handle PDF escape sequences: \(, \), \\, \n, \r, \t, \ddd (octal)
  return str
    .replace(/\\([0-7]{1,3})/g, (_, oct) => String.fromCharCode(parseInt(oct, 8)))
    .replace(/\\n/g, '\n')
    .replace(/\\r/g, '\r')
    .replace(/\\t/g, '\t')
    .replace(/\\\(/g, '(')
    .replace(/\\\)/g, ')')
    .replace(/\\\\/g, '\\');
}

/**
 * Extracts raw digital vector text from a PDF ArrayBuffer.
 */
export async function extractPdfTextFromBuffer(buffer: ArrayBuffer | Uint8Array): Promise<string> {
  const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
  const latinStr = new TextDecoder('latin1').decode(bytes);

  const extractedLines: string[] = [];
  let pos = 0;

  while (pos < bytes.length) {
    const streamIdx = latinStr.indexOf('stream', pos);
    if (streamIdx === -1) break;

    // Detect line break after "stream"
    let contentStart = streamIdx + 6;
    if (bytes[contentStart] === 0x0d && bytes[contentStart + 1] === 0x0a) {
      contentStart += 2;
    } else if (bytes[contentStart] === 0x0a || bytes[contentStart] === 0x0d) {
      contentStart += 1;
    }

    // Inspect preceding dictionary for /Length and /Filter
    const dictSlice = latinStr.slice(Math.max(0, streamIdx - 350), streamIdx);
    const lengthMatch = dictSlice.match(/\/Length\s+(\d+)/);
    const isFlate = dictSlice.includes('/FlateDecode');

    let streamBytes: Uint8Array;
    if (lengthMatch) {
      const len = parseInt(lengthMatch[1], 10);
      streamBytes = bytes.subarray(contentStart, contentStart + len);
      pos = contentStart + len;
    } else {
      const endIdx = latinStr.indexOf('endstream', contentStart);
      if (endIdx === -1) break;
      streamBytes = bytes.subarray(contentStart, endIdx);
      pos = endIdx + 9;
    }

    let decompressedBytes = streamBytes;
    if (isFlate) {
      let decompressed: Uint8Array | null = null;
      try {
        const ds = new DecompressionStream('deflate');
        const writer = ds.writable.getWriter();
        writer.write(streamBytes as unknown as BufferSource);
        writer.close();
        const res = new Response(ds.readable);
        decompressed = new Uint8Array(await res.arrayBuffer());
      } catch {
        // Handle potential trailing whitespace before endstream
        for (let trim = 1; trim <= 4; trim++) {
          try {
            const ds = new DecompressionStream('deflate');
            const writer = ds.writable.getWriter();
            writer.write(streamBytes.subarray(0, streamBytes.length - trim) as unknown as BufferSource);
            writer.close();
            const res = new Response(ds.readable);
            decompressed = new Uint8Array(await res.arrayBuffer());
            break;
          } catch {
            // continue trimming
          }
        }
      }

      if (decompressed) {
        decompressedBytes = decompressed;
      } else {
        continue;
      }
    }

    const streamStr = new TextDecoder('latin1').decode(decompressedBytes);

    // Scan for Text Objects: BT ... ET
    const btRegex = /BT([\s\S]*?)ET/g;
    let btMatch: RegExpExecArray | null;

    while ((btMatch = btRegex.exec(streamStr)) !== null) {
      const block = btMatch[1];

      // 1. Array text positioning: [(...) 120 (...)] TJ
      const tjRegex = /\[(.*?)\]\s*TJ/g;
      let tjMatch: RegExpExecArray | null;

      while ((tjMatch = tjRegex.exec(block)) !== null) {
        const inner = tjMatch[1];
        let line = '';
        const itemRegex = /<([0-9a-fA-F]+)>|\(((?:\\\(|\\\)|[^()])*)\)/g;
        let itemMatch: RegExpExecArray | null;

        while ((itemMatch = itemRegex.exec(inner)) !== null) {
          if (itemMatch[1]) {
            line += decodePdfHexString(itemMatch[1]);
          } else if (itemMatch[2] !== undefined) {
            line += decodePdfLiteralString(itemMatch[2]);
          }
        }

        const trimmed = line.trim();
        if (trimmed) {
          extractedLines.push(trimmed);
        }
      }

      // 2. Single text element: (...) Tj or <hex> Tj
      const singleTjRegex = /(?:\(((?:\\\(|\\\)|[^()])*)\)|<([0-9a-fA-F]+)>)\s*Tj/g;
      let singleMatch: RegExpExecArray | null;

      while ((singleMatch = singleTjRegex.exec(block)) !== null) {
        if (singleMatch[1] !== undefined) {
          const text = decodePdfLiteralString(singleMatch[1]).trim();
          if (text) extractedLines.push(text);
        } else if (singleMatch[2]) {
          const text = decodePdfHexString(singleMatch[2]).trim();
          if (text) extractedLines.push(text);
        }
      }
    }
  }

  // Assemble lines, intelligently preserving markdown structure
  let result = '';
  let insideTable = false;

  for (let i = 0; i < extractedLines.length; i++) {
    const line = extractedLines[i];
    const isTableLine = line.startsWith('|') && line.endsWith('|');

    if (isTableLine) {
      if (!insideTable && result.length > 0) {
        result += '\n\n';
      }
      insideTable = true;
      result += line + '\n';
    } else {
      insideTable = false;
      if (line.startsWith('#') || line.startsWith('$$')) {
        result += '\n\n' + line + '\n\n';
      } else {
        result += line + '\n';
      }
    }
  }

  return result.trim();
}

/**
 * Extracts digital text directly from a File or Blob.
 */
export async function extractPdfTextFromFile(file: File | Blob): Promise<string> {
  const arrayBuffer = await file.arrayBuffer();
  return extractPdfTextFromBuffer(arrayBuffer);
}
