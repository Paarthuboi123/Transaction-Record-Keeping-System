import sys
import zipfile
import xml.etree.ElementTree as ET

def extract_text_from_docx(path):
    with zipfile.ZipFile(path) as z:
        with z.open('word/document.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            # Word XML namespace
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            texts = [t.text for t in root.findall('.//w:t', ns) if t.text]
            # Join paragraphs by detecting w:p elements
            paragraphs = []
            for p in root.findall('.//w:p', ns):
                parts = [t.text for t in p.findall('.//w:t', ns) if t.text]
                if parts:
                    paragraphs.append(''.join(parts))
            if paragraphs:
                return '\n\n'.join(paragraphs)
            return '\n'.join(texts)

def main():
    if len(sys.argv) < 2:
        print('Usage: extract_docx_text.py <file.docx>', file=sys.stderr)
        sys.exit(2)
    path = sys.argv[1]
    try:
        text = extract_text_from_docx(path)
        print(text)
    except Exception as e:
        print('Error extracting text:', e, file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
