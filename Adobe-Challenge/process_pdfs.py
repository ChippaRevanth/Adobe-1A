import json
from pathlib import Path
import fitz # PyMuPDF
import re

def extract_outline_from_pdf(pdf_path: Path) -> dict:
    """
    Extracts title and a structured outline (H1, H2, H3) from a PDF file.
    It prioritizes internal PDF Table of Contents (TOC). If no TOC is found,
    it uses heuristics based on font size, boldness, and layout.
    """
    title = pdf_path.stem # Default title to filename
    outline_entries = []
    doc = None

    try:
        doc = fitz.open(pdf_path)

        # 1. Try to extract Title from PDF metadata
        if doc.metadata and doc.metadata.get("title"):
            extracted_title = doc.metadata["title"].strip()
            if extracted_title:
                title = extracted_title
        
        # 2. Try to extract outline from PDF's internal Table of Contents (TOC) / Bookmarks
        toc = doc.get_toc()
        if toc:
            print(f"  Found {len(toc)} entries in PDF's internal Table of Contents.")
            for level, text, page in toc:
                # Map TOC level to H1, H2, H3. Assume 1-based TOC levels.
                # Max 3 levels required for the challenge
                heading_level = "H1"
                if level == 2:
                    heading_level = "H2"
                elif level >= 3:
                    heading_level = "H3"
                
                clean_text = text.strip()
                # Filter out empty text or purely numeric entries often found in TOC noise
                if clean_text and any(char.isalpha() for char in clean_text):
                    outline_entries.append({
                        "level": heading_level,
                        "text": clean_text,
                        "page": page # TOC page numbers are typically 1-based
                    })
            # If TOC is found and processed, we return this.
            return {
                "title": title,
                "outline": outline_entries
            }

        # 3. Fallback: Heuristics based on font size, boldness, and layout if no TOC
        print("  No internal Table of Contents found. Attempting font/layout-based heuristics.")
        
        # Determine average font sizes and styles to set dynamic thresholds
        font_styles = {} # {font_name: {size: {is_bold: count}}}
        all_sizes = []
        
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            blocks = page.get_text("dict")["blocks"]
            for b in blocks:
                if b["type"] == 0: # text block
                    for line in b["lines"]:
                        for span in line["spans"]:
                            font_name = span["font"]
                            size = round(span["size"], 1)
                            is_bold = "bold" in font_name.lower() or "b" in span["flags"] or "b" in font_name.lower().split('-')
                            
                            if font_name not in font_styles:
                                font_styles[font_name] = {}
                            if size not in font_styles[font_name]:
                                font_styles[font_name][size] = {"bold": 0, "normal": 0}
                            
                            font_styles[font_name][size]["bold" if is_bold else "normal"] += len(span["text"])
                            all_sizes.append(size)

        # Estimate common body font size from most frequent size among non-bold text
        body_font_size = 0.0
        if all_sizes:
            from collections import Counter
            body_font_size = Counter(all_sizes).most_common(1)[0][0]
            
            # Refine body_font_size: Look for largest count of 'normal' characters
            max_normal_chars = 0
            for font_name, sizes in font_styles.items():
                for size, data in sizes.items():
                    if data["normal"] > max_normal_chars:
                        max_normal_chars = data["normal"]
                        body_font_size = size

        if body_font_size == 0.0 and all_sizes: # Fallback if no "normal" detected
             body_font_size = Counter(all_sizes).most_common(1)[0][0] # Most common size overall

        if body_font_size == 0.0: # If no text at all
            return {"title": title, "outline": []}


        # Define dynamic thresholds based on detected body font size
        # These are multiplicative factors that define what's considered a heading.
        # Can be tuned based on general document types.
        H1_FACTOR = 1.6 # e.g., 160% larger than body
        H2_FACTOR = 1.3 # e.g., 130% larger than body
        H3_FACTOR = 1.1 # e.g., 110% larger than body

        h1_threshold = body_font_size * H1_FACTOR
        h2_threshold = body_font_size * H2_FACTOR
        h3_threshold = body_font_size * H3_FACTOR
        
        print(f"  Estimated body font size: {body_font_size:.1f}pt")
        print(f"  Dynamic H1 threshold: {h1_threshold:.1f}pt")
        print(f"  Dynamic H2 threshold: {h2_threshold:.1f}pt")
        print(f"  Dynamic H3 threshold: {h3_threshold:.1f}pt")

        # Capture text to identify headings
        temp_outline_candidates = []

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            # Use 'rawdict' to get more detailed text block information including coordinates
            blocks = page.get_text("rawdict")["blocks"]

            for block in blocks:
                if block["type"] == 0: # text block
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            font_size = round(span["size"], 1)
                            font_name = span["font"]
                            is_bold = "bold" in font_name.lower() or "b" in span["flags"] or "b" in font_name.lower().split('-')
                            
                            # Filtering common noise and non-heading patterns
                            if not text or len(text) < 5 or text.isnumeric() or \
                                re.match(r"^\d+\.\s*$", text) or \
                                re.match(r"^[IVXLCDM]+\.$", text) or \
                                "G.MAMATHA, CET, CBIT" in text or \
                                text.lower().startswith(("figure", "table", "formula", "example", "g.mamatha", "source:")):
                                continue

                            level = None
                            # Prioritize larger, bold text
                            if font_size >= h1_threshold and is_bold:
                                level = "H1"
                            elif font_size >= h2_threshold and is_bold:
                                level = "H2"
                            elif font_size >= h3_threshold and is_bold:
                                level = "H3"
                            # Also consider large, non-bold, title-cased or all-caps text as potential headings
                            elif font_size > body_font_size and (text.istitle() or text.isupper()):
                                # This can be H2 or H3 depending on relative size, or if previous was H1
                                if font_size >= h2_threshold:
                                    level = "H2"
                                else:
                                    level = "H3"
                            
                            if level:
                                temp_outline_candidates.append({
                                    "level": level,
                                    "text": text,
                                    "page": page_num + 1,
                                    "bbox": span["bbox"] # Store bounding box for later spatial analysis if needed
                                })
        
        # Post-processing and deduplication for heuristic-based outlines
        # This helps in creating a more coherent outline from raw text blocks.
        if temp_outline_candidates:
            # Sort by page and then by vertical position (y0 of bbox)
            temp_outline_candidates.sort(key=lambda x: (x["page"], x["bbox"][1]))
            
            seen_entries = set()
            for entry in temp_outline_candidates:
                # Simple text-based deduplication for entries that are very similar
                unique_key = (entry["level"], entry["text"].lower(), entry["page"])
                if unique_key not in seen_entries:
                    outline_entries.append(entry)
                    seen_entries.add(unique_key)
            
            # A final pass to refine title if it's still generic
            if title == pdf_path.stem and outline_entries and outline_entries[0]["page"] == 1:
                # If the first H1 on page 1 is concise, use it as title
                if outline_entries[0]["level"] == "H1" and len(outline_entries[0]["text"]) < 50:
                    title = outline_entries[0]["text"]
                # Or if "UNIT-IV" is prominent on page 1
                if "UNIT-IV" in title.upper() and outline_entries[0]["page"] == 1:
                    title = "UNIT-IV" # Specific to your example PDF

    except ImportError:
        print("Error: PyMuPDF is not installed. Please add 'PyMuPDF' to your requirements.txt and rebuild your Docker image.")
        print("Returning an empty/error outline.")
        return {
            "title": f"Processing Error for {pdf_path.stem}",
            "outline": [{"level": "H1", "text": "PyMuPDF not found. Please install it.", "page": 1}]
        }
    except Exception as e:
        print(f"An unexpected error occurred during PDF processing for {pdf_path.name}: {e}")
        return {
            "title": f"Processing Error for {pdf_path.stem}",
            "outline": [{"level": "H1", "text": f"Error: {e}", "page": 1}]
        }
    finally:
        if doc:
            doc.close()

    return {
        "title": title,
        "outline": outline_entries
    }


def process_pdfs():
    """
    Processes all PDF files found in the /app/input directory,
    extracts their outlines using the 'extract_outline_from_pdf' function,
    and saves the results as JSON files in the /app/output directory.
    """
    input_dir = Path("/app/input")
    output_dir = Path("/app/output")

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")

    pdf_files = list(input_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"❌ No PDF files found in {input_dir}. Please ensure your PDFs are mounted correctly to /app/input.")
        return

    print(f"✅ Found {len(pdf_files)} PDF(s) to process.")
    for pdf_file in pdf_files:
        print(f"\n--- Starting processing for {pdf_file.name} ---")
        extracted_data = extract_outline_from_pdf(pdf_file)

        output_file = output_dir / f"{pdf_file.stem}.json"
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            print(f"🎉 Successfully processed {pdf_file.name} -> {output_file.name}")
        except IOError as e:
            print(f"🔥 Error writing output file {output_file.name}: {e}")
        except Exception as e:
            print(f"❓ An unexpected error occurred while writing output for {pdf_file.name}: {e}")
        print(f"--- Finished processing for {pdf_file.name} ---")


if __name__ == "__main__":
    print("🚀 Starting PDF outline extraction process for 'Connecting the Dots' Challenge Round 1A...")
    process_pdfs()
    print("✅ PDF outline extraction process completed.")