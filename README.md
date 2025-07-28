# Adobe-1A
project using docker file where we extract a structured outline of the document

This project is designed to extract structured outlines (H1, H2, H3 headings) and the main title from PDF documents. It prioritizes internal PDF Table of Contents (TOC) for accuracy and falls back to heuristic-based text analysis when no TOC is available, making it versatile for various PDF structures. The output is a JSON file containing the extracted outline.

1. Approach
The solution employs a two-pronged approach for outline extraction:
i)Internal TOC Extraction (Priority): The primary method involves attempting to read the PDF's built-in Table of Contents (TOC) or bookmarks. If a TOC is present, it directly extracts the hierarchical structure, text, and associated page numbers, mapping TOC levels to H1, H2, or H3. This method is generally the most reliable for well-structured PDFs.
ii)Heuristic-Based Analysis (Fallback): If no internal TOC is found, the system falls back to a heuristic approach. This involves:
 ->Text Extraction: All text content is extracted page by page.

 ->Font Feature Analysis: The tool analyzes font properties (size, boldness) across the document to dynamically determine   thresholds for what constitutes a heading (H1, H2, H3) versus body text. This makes the detection adaptive.

 ->Layout and Content Heuristics: It identifies lines that are likely headings based on their font size relative to the body text, bolding, title-casing, all-caps, and common structural patterns (e.g., Roman numerals, numerical prefixes). It also includes filtering for common noise like page numbers or footers.

 ->Post-processing and Deduplication: Extracted heading candidates are sorted by page and vertical position, and a deduplication step is applied to refine the final outline.

The process_pdfs.py script orchestrates this by iterating through all PDF files in the designated input directory, applying the extraction logic, and saving the results as individual JSON files in the output directory.

2. Any Models or Libraries Used
The core library used in this project is:

->PyMuPDF (imported as fitz): This powerful library is used for robust PDF parsing, text extraction (including font and style information), and reading internal Table of Contents (TOC) data. It's essential for both the TOC-based and heuristic-based outline extraction methods.

In addition to PyMuPDF, standard Python libraries are utilized:

->json: For reading and writing structured data (input configuration and output JSON).

->pathlib.Path: For object-oriented filesystem paths, making file operations cleaner.

->re: For regular expression-based text cleaning and pattern matching to identify potential headings and filter noise.

->os: For operating system interactions, such as creating directories.

->collections.Counter: Used in the heuristic approach to help determine common font sizes.


3. How to Build and Run Your Solution (Documentation Purpose Only)
This section outlines the steps to build the Docker image and demonstrates how the container is designed to be run. Please note that for submission, your solution is expected to run using the "Expected Execution" setup as specified in the challenge guidelines.

i)Prerequisites:
  Ensure you have Docker installed on your system.

ii)Clone the Repository:
  First, obtain the project files by cloning this Git repository to your local machine:
    git clone <https://github.com/ChippaRevanth/Adobe-1A.git>

iii)Build the Docker Image:
  Navigate to the root directory of the cloned repository (where the Dockerfile is located). Build the Docker image using the   following command:

    docker build -t pdf-outline-extractor

iv)Prepare Input Data:
  Create a local directory on your machine (e.g., my_pdf_inputs). Place all the PDF files you wish to process into this         directory. The container will expect these files to be mounted into /app/input.

v)Run the Docker Container:
  To execute the PDF outline extraction, run the Docker container by mounting your input and an output directory. The           container expects PDF inputs in /app/input and will write the resulting JSON files to /app/output.

    docker run --rm \
      -v /path/to/your/local_input_folder:/app/input \
      -v /path/to/your/local_output_folder:/app/output \
      pdf-outline-extractor

  ->Replace /path/to/your/local_input_folder with the absolute path to your local directory containing the PDF inputs.

  ->Replace /path/to/your/local_output_folder with the absolute path to a local directory where you want the output JSON files to be saved.

  ->pdf-outline-extractor should be the image tag you used during the build step.

  ->The --rm flag ensures the container is automatically removed after its execution.

Upon completion, a JSON file (e.g., your_document_name.json) containing the extracted title and outline will be found in your specified output folder for each processed PDF.
