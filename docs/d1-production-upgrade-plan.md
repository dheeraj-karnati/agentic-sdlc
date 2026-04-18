Rebuild D1: Ingest as a production-grade, best-in-class
ingestion agent that can compete with Unstructured.io,
LlamaIndex, and any enterprise document processing platform.

The key differentiator: D8X doesn't just parse files — it
UNDERSTANDS them, classifies them, detects relationships
between documents, scores quality, and stores everything
with vector embeddings for downstream semantic search.

=== DEPENDENCIES ===

Add these to pyproject.toml and install with uv:

# Document parsing
unstructured[all-docs]>=0.16.0    # Core document parsing engine
python-docx>=1.0                   # DOCX parsing
openpyxl>=3.1                      # XLSX parsing  
python-pptx>=1.0                   # PPTX parsing
pymupdf>=1.24                      # PDF parsing (fast, accurate)
pytesseract>=0.3                   # OCR for scanned documents
pdf2image>=1.17                    # PDF to image for OCR
beautifulsoup4>=4.12               # HTML parsing
markdown>=3.7                      # Markdown parsing
python-magic>=0.4                  # MIME type detection
chardet>=5.2                       # Character encoding detection

# Code parsing
tree-sitter>=0.23                  # AST parsing for 20+ languages
tree-sitter-python>=0.23
tree-sitter-javascript>=0.23
tree-sitter-typescript>=0.23
tree-sitter-java>=0.23
tree-sitter-go>=0.23
tree-sitter-c-sharp>=0.23
tree-sitter-ruby>=0.23
tree-sitter-rust>=0.23
tree-sitter-sql>=0.23
pygments>=2.18                     # Fallback syntax detection

# Audio/Video
openai-whisper>=20240930           # Speech-to-text (local)
pydub>=0.25                        # Audio format conversion
ffmpeg-python>=0.2                 # Video processing

# Data formats
pandas>=2.2                        # CSV/Excel data analysis
pyyaml>=6.0                        # YAML parsing
toml>=0.10                         # TOML parsing
xmltodict>=0.14                    # XML parsing

# NLP
tiktoken>=0.8                      # Token counting
langdetect>=1.0                    # Language detection
spacy>=3.8                         # NLP (optional, for entity pre-detection)

# Archive handling
py7zr>=0.22                        # 7z archives
rarfile>=4.2                       # RAR archives

# Cloud storage
boto3>=1.35                        # AWS S3
google-cloud-storage>=2.18         # GCS (optional)
azure-storage-blob>=12.23          # Azure Blob (optional)
httpx>=0.27                        # URL fetching

System dependencies (document in README):
- tesseract-ocr (apt install tesseract-ocr)
- ffmpeg (apt install ffmpeg)
- poppler-utils (apt install poppler-utils) for pdf2image
- libmagic (apt install libmagic1)

Install:
uv add unstructured[all-docs] python-docx openpyxl python-pptx \
pymupdf pytesseract pdf2image beautifulsoup4 markdown \
python-magic chardet tree-sitter pygments openai-whisper \
pydub ffmpeg-python pandas pyyaml toml xmltodict tiktoken \
langdetect py7zr rarfile boto3 httpx

Note: Some of these are heavy. If install fails on any,
make them optional with try/except imports and log a warning.

=== ARCHITECTURE ===

src/agents/ingest/
├── __init__.py
├── agent.py                     # IngestWorkflow (LangGraph)
├── skills/
│   ├── __init__.py
│   ├── file_detector.py         # MIME detection + routing
│   ├── pdf_parser.py            # PDF: native + OCR + table extraction
│   ├── document_parser.py       # DOCX, PPTX, RTF, ODT
│   ├── spreadsheet_parser.py    # XLSX, CSV, TSV
│   ├── text_parser.py           # TXT, MD, HTML, XML, YAML, JSON, TOML
│   ├── code_parser.py           # 20+ languages via tree-sitter
│   ├── audio_transcriber.py     # MP3, WAV, M4A, OGG, FLAC, WMA
│   ├── video_processor.py       # MP4, MOV, AVI, WebM, MKV
│   ├── image_analyzer.py        # PNG, JPG, SVG, diagrams, whiteboard
│   ├── archive_extractor.py     # ZIP, TAR, GZ, 7Z, RAR
│   ├── database_parser.py       # SQL files, database dumps
│   ├── email_parser.py          # EML, MSG files
│   ├── cloud_fetcher.py         # S3, GCS, Azure, HTTP/HTTPS URLs
│   ├── content_classifier.py    # Classify document type + domain
│   ├── language_detector.py     # Detect language of content
│   ├── chunker.py               # Smart chunking strategies
│   ├── deduplicator.py          # Detect duplicate/near-duplicate content
│   └── quality_scorer.py        # Per-file quality assessment
├── tasks/
│   ├── __init__.py
│   ├── fetch_sources.py         # Download from URLs/cloud storage
│   ├── extract_content.py       # Route files to correct parsers
│   ├── analyze_content.py       # Classify, detect language, score
│   ├── chunk_and_embed.py       # Smart chunking + vector storage
│   ├── build_inventory.py       # Generate source inventory
│   └── assess_quality.py        # Overall quality assessment
└── models.py                    # All Pydantic I/O models

=== SKILL 1: file_detector.py ===

The gatekeeper — determines exactly what each file is
and where to route it.

class FileDetector:
"""
Detects file type using multiple strategies:
1. File extension
2. MIME type (python-magic)
3. Content inspection (first bytes / magic numbers)

    Returns the most specific classification possible.
    """
    
    ROUTING_MAP = {
        # Documents
        "pdf": "pdf_parser",
        "docx": "document_parser",
        "doc": "document_parser",
        "pptx": "document_parser",
        "ppt": "document_parser",
        "rtf": "document_parser",
        "odt": "document_parser",
        "odp": "document_parser",
        
        # Spreadsheets
        "xlsx": "spreadsheet_parser",
        "xls": "spreadsheet_parser",
        "csv": "spreadsheet_parser",
        "tsv": "spreadsheet_parser",
        
        # Text/Markup
        "txt": "text_parser",
        "md": "text_parser",
        "html": "text_parser",
        "htm": "text_parser",
        "xml": "text_parser",
        "json": "text_parser",
        "yaml": "text_parser",
        "yml": "text_parser",
        "toml": "text_parser",
        "ini": "text_parser",
        "cfg": "text_parser",
        "conf": "text_parser",
        "log": "text_parser",
        "rst": "text_parser",
        
        # Code (20+ languages)
        "py": "code_parser",
        "js": "code_parser",
        "jsx": "code_parser",
        "ts": "code_parser",
        "tsx": "code_parser",
        "java": "code_parser",
        "cs": "code_parser",
        "go": "code_parser",
        "rb": "code_parser",
        "rs": "code_parser",
        "php": "code_parser",
        "swift": "code_parser",
        "kt": "code_parser",
        "scala": "code_parser",
        "c": "code_parser",
        "cpp": "code_parser",
        "h": "code_parser",
        "hpp": "code_parser",
        "r": "code_parser",
        "dart": "code_parser",
        "lua": "code_parser",
        "sh": "code_parser",
        "bash": "code_parser",
        "ps1": "code_parser",
        "vb": "code_parser",
        "vbs": "code_parser",
        "asp": "code_parser",
        "aspx": "code_parser",
        "pl": "code_parser",
        "pm": "code_parser",
        "groovy": "code_parser",
        "proto": "code_parser",
        "graphql": "code_parser",
        "gql": "code_parser",
        "tf": "code_parser",
        "hcl": "code_parser",
        "dockerfile": "code_parser",
        "makefile": "code_parser",
        
        # Database
        "sql": "database_parser",
        "ddl": "database_parser",
        "dml": "database_parser",
        
        # Config/DevOps (parse as code for structure)
        "env": "text_parser",
        "gitignore": "text_parser",
        "dockerignore": "text_parser",
        "editorconfig": "text_parser",
        
        # Package manifests (parse as structured data)
        "lock": "text_parser",
        
        # Audio
        "mp3": "audio_transcriber",
        "wav": "audio_transcriber",
        "m4a": "audio_transcriber",
        "ogg": "audio_transcriber",
        "flac": "audio_transcriber",
        "wma": "audio_transcriber",
        "aac": "audio_transcriber",
        
        # Video
        "mp4": "video_processor",
        "mov": "video_processor",
        "avi": "video_processor",
        "webm": "video_processor",
        "mkv": "video_processor",
        "wmv": "video_processor",
        
        # Images
        "png": "image_analyzer",
        "jpg": "image_analyzer",
        "jpeg": "image_analyzer",
        "gif": "image_analyzer",
        "svg": "image_analyzer",
        "bmp": "image_analyzer",
        "tiff": "image_analyzer",
        "webp": "image_analyzer",
        
        # Archives
        "zip": "archive_extractor",
        "tar": "archive_extractor",
        "gz": "archive_extractor",
        "tgz": "archive_extractor",
        "bz2": "archive_extractor",
        "7z": "archive_extractor",
        "rar": "archive_extractor",
        
        # Email
        "eml": "email_parser",
        "msg": "email_parser",
    }
    
    Input: file_path (str), original_filename (str)
    
    Process:
      1. Get extension from original_filename
      2. Use python-magic to detect MIME type
      3. If extension and MIME disagree, trust MIME type
      4. For extensionless files (Dockerfile, Makefile), 
         check filename directly
      5. For package.json, requirements.txt, Cargo.toml, 
         go.mod — classify as "package_manifest" subcategory
    
    Output: FileDetection with:
      - extension: str
      - mime_type: str
      - parser: str (which skill to use)
      - file_category: str (document/code/audio/video/image/
        archive/spreadsheet/database/email/text/config)
      - confidence: float (how sure we are about the detection)
      - file_size_bytes: int
      - encoding: str (detected character encoding)

=== SKILL 2: pdf_parser.py ===

The most critical parser — PDFs are the #1 enterprise format.
Must handle: native text PDFs, scanned PDFs, mixed PDFs,
PDFs with tables, PDFs with forms, PDFs with images.

class PDFParser:
"""
Three-pass PDF parsing for maximum extraction quality.

    Pass 1: PyMuPDF native text extraction (fast, accurate 
            for digital PDFs)
    Pass 2: If Pass 1 yields < 100 chars per page average, 
            assume scanned → OCR with Tesseract
    Pass 3: Table extraction using PyMuPDF table detection
    """
    
    Input: file_path (str)
    
    Process:
    
      # Pass 1: Native text extraction
      import fitz  # PyMuPDF
      
      doc = fitz.open(file_path)
      pages = []
      
      for page_num, page in enumerate(doc):
          text = page.get_text("text")
          
          # Extract structure
          blocks = page.get_text("dict")["blocks"]
          
          # Identify headings (larger font size)
          headings = []
          body_text = []
          for block in blocks:
              if "lines" in block:
                  for line in block["lines"]:
                      for span in line["spans"]:
                          if span["size"] > 14:  # heading threshold
                              headings.append(span["text"])
                          else:
                              body_text.append(span["text"])
          
          # Extract images from this page
          images = page.get_images()
          
          pages.append({
              "page_number": page_num + 1,
              "text": text,
              "headings": headings,
              "has_images": len(images) > 0,
              "char_count": len(text)
          })
      
      # Pass 2: OCR if needed
      avg_chars = sum(p["char_count"] for p in pages) / max(len(pages), 1)
      
      if avg_chars < 100:
          # Likely scanned document — use OCR
          from pdf2image import convert_from_path
          import pytesseract
          
          images = convert_from_path(file_path, dpi=300)
          for i, img in enumerate(images):
              ocr_text = pytesseract.image_to_string(
                  img, lang='eng',
                  config='--oem 3 --psm 6'  # LSTM engine, block mode
              )
              if i < len(pages):
                  pages[i]["text"] = ocr_text
                  pages[i]["char_count"] = len(ocr_text)
                  pages[i]["ocr_applied"] = True
      
      # Pass 3: Table extraction
      tables = []
      for page_num, page in enumerate(doc):
          page_tables = page.find_tables()
          for table in page_tables:
              table_data = table.extract()
              if table_data and len(table_data) > 1:
                  headers = table_data[0]
                  rows = table_data[1:]
                  tables.append({
                      "page": page_num + 1,
                      "headers": headers,
                      "rows": rows,
                      "row_count": len(rows)
                  })
      
      # Extract form fields if present
      form_fields = []
      for page in doc:
          widgets = page.widgets()
          if widgets:
              for widget in widgets:
                  form_fields.append({
                      "field_name": widget.field_name,
                      "field_type": widget.field_type_string,
                      "field_value": widget.field_value
                  })
      
      # Extract metadata
      metadata = doc.metadata
      
    Output: ParsedPDF with:
      - pages: list[PageContent]
          (page_number, text, headings, ocr_applied)
      - tables: list[ExtractedTable]
          (page, headers, rows, row_count)
      - form_fields: list[FormField]
      - metadata: dict (title, author, subject, creator, 
        created_date, modified_date, page_count)
      - full_text: str (all pages concatenated)
      - total_pages: int
      - total_chars: int
      - has_ocr: bool
      - total_tables: int
      - total_images: int

=== SKILL 3: document_parser.py ===

Handles DOCX, PPTX, RTF, ODT.

class DocumentParser:
"""
Parses Word, PowerPoint, and other document formats
with full structure preservation.
"""

    For DOCX:
      from docx import Document
      
      - Extract paragraphs with style info (Heading 1, 
        Heading 2, Normal, List)
      - Build section hierarchy from heading levels
      - Extract tables with headers and cell formatting
      - Extract images (store separately as artifacts)
      - Extract comments and tracked changes
      - Extract headers/footers
      - Extract document properties (author, title, etc.)
      - Detect lists (bulleted and numbered)
      - Preserve bold/italic/underline for emphasis detection
    
    For PPTX:
      from pptx import Presentation
      
      - Extract text from each slide
      - Preserve slide order and titles
      - Extract speaker notes (often contain important context)
      - Extract tables from slides
      - Detect slide layouts (title, content, comparison)
      - Extract images
    
    For RTF/ODT:
      Use unstructured library as fallback:
      from unstructured.partition.auto import partition
      elements = partition(filename=file_path)
    
    Output: ParsedDocument with:
      - sections: list[Section]
          (heading, level, content, page_number, subsections)
      - tables: list[ExtractedTable]
      - images: list[ImageRef]
      - comments: list[Comment] (author, text, date)
      - metadata: dict
      - full_text: str
      - document_type: str (docx/pptx/rtf/odt)
      - total_sections: int
      - total_words: int

=== SKILL 4: spreadsheet_parser.py ===

class SpreadsheetParser:
"""
Parses Excel and CSV with intelligent data analysis.
Doesn't just read cells — understands the data.
"""

    For XLSX:
      import openpyxl
      import pandas as pd
      
      - Read all sheets
      - Auto-detect header row (first row with all non-empty cells)
      - Detect data types per column (text, number, date, boolean)
      - Calculate basic statistics for numeric columns
      - Detect formulas and their dependencies
      - Extract named ranges
      - Detect pivot tables
      - Extract charts (as descriptions)
      - Handle merged cells
      - Detect empty rows/columns (trim them)
      - Sample data: first 50 rows + last 10 rows for context
    
    For CSV/TSV:
      import pandas as pd
      
      - Auto-detect delimiter (comma, tab, pipe, semicolon)
      - Auto-detect encoding (chardet)
      - Auto-detect header row
      - Handle quoted fields and escape characters
      - Detect data types
      - Basic statistics for numeric columns
    
    Output: ParsedSpreadsheet with:
      - sheets: list[SheetData]
          (name, headers, data_types, row_count, col_count,
           sample_rows, statistics, formulas_detected)
      - total_sheets: int
      - total_rows: int
      - total_columns: int
      - metadata: dict
      - data_summary: str (human-readable description: 
        "3 sheets, 1,234 rows, columns include: employee_id, 
        name, department, salary, hire_date")

=== SKILL 5: code_parser.py ===

class CodeParser:
"""
Deep code analysis using tree-sitter AST parsing.
Extracts structure, not just text.
"""

    LANGUAGE_MAP = {
        "py": "python", "js": "javascript", "jsx": "javascript",
        "ts": "typescript", "tsx": "typescript", "java": "java",
        "cs": "c_sharp", "go": "go", "rb": "ruby", "rs": "rust",
        "php": "php", "swift": "swift", "kt": "kotlin",
        "c": "c", "cpp": "cpp", "h": "c", "hpp": "cpp",
        "scala": "scala", "dart": "dart", "lua": "lua",
        "sh": "bash", "bash": "bash", "sql": "sql",
        "r": "r", "pl": "perl", "groovy": "groovy",
        "vb": "vb", "vbs": "vb",
    }
    
    Process:
      1. Detect language from extension
      2. Parse with tree-sitter to build AST
      3. Walk AST to extract:
    
    For each source file, extract:
    
    - file_path: str
    - language: str
    - line_count: int
    - imports/dependencies: list[str]
      (import statements, require(), use, #include, using)
    
    - classes: list[ClassInfo]
        name, parent_classes, methods, properties, 
        decorators, docstring, line_start, line_end
    
    - functions: list[FunctionInfo]
        name, parameters (name + type if typed), 
        return_type, decorators, docstring, 
        line_start, line_end, complexity_estimate
    
    - api_endpoints: list[EndpointInfo]
        Detect route decorators/handlers:
        @app.get("/api/users"), router.post(), 
        @RequestMapping, [HttpGet], etc.
        Extract: http_method, path, parameters, 
        handler_function
    
    - database_operations: list[DBOperation]
        Detect SQL queries, ORM calls:
        cursor.execute(), Model.query, 
        SELECT/INSERT/UPDATE/DELETE patterns
        Extract: operation_type, table_names, 
        raw_query_if_available
    
    - configuration: dict
        Detect config patterns: environment variables, 
        settings classes, config files
    
    - security_concerns: list[SecurityIssue]
        Detect common vulnerabilities:
        - SQL injection (string concatenation in queries)
        - Hardcoded secrets (passwords, API keys, tokens)
        - Eval/exec usage
        - Unsafe deserialization
        - Missing input validation on endpoints
    
    - technology_stack: list[str]
        Detected from imports and patterns:
        Flask, Django, FastAPI, Express, React, Vue, etc.
    
    If tree-sitter fails for a language, fall back to 
    regex-based extraction:
      - Functions: def/function/func/fn + name
      - Classes: class + name
      - Imports: import/require/use/include + path
      - Routes: common route decorator patterns
    
    Also parse special files:
      package.json → dependencies, scripts, name, version
      requirements.txt / Pipfile / pyproject.toml → Python deps
      Cargo.toml → Rust deps
      go.mod → Go deps
      pom.xml / build.gradle → Java deps
      Gemfile → Ruby deps
      composer.json → PHP deps
      Dockerfile → base image, exposed ports, commands
      docker-compose.yml → services, ports, volumes
      .env.example → expected environment variables
    
    Output: ParsedCodebase with:
      - files: list[ParsedSourceFile]
      - total_files: int
      - total_lines: int
      - languages: dict[str, int] (language → line count)
      - technology_stack: list[str]
      - frameworks_detected: list[str]
      - api_endpoints: list[EndpointInfo] (aggregated)
      - database_tables: list[str] (aggregated from queries)
      - security_concerns: list[SecurityIssue]
      - dependency_graph: dict (file → list of imports)
      - external_dependencies: list[Dependency]
          (name, version, source: npm/pip/cargo/etc.)

=== SKILL 6: audio_transcriber.py ===

class AudioTranscriber:
"""
Speech-to-text using local Whisper model.
Includes speaker diarization and topic segmentation.
"""

    Process:
      import whisper
      from pydub import AudioSegment
      
      1. Convert to WAV if needed (pydub handles all formats)
      2. Load Whisper model:
         - "base" for fast processing (good enough for meeting notes)
         - "medium" for better accuracy (use for critical recordings)
         - "large-v3" for best accuracy (if GPU available)
         Model selection from config: settings.whisper_model
      
      3. Transcribe with timestamps:
         result = model.transcribe(
             audio_path,
             language=language or None,  # auto-detect if not specified
             word_timestamps=True,
             verbose=False
         )
      
      4. Speaker diarization (simplified, without pyannote):
         - Detect speaker changes based on:
           a. Silence gaps > 2 seconds
           b. Significant volume changes
           c. Sentence boundary detection
         - Assign speaker labels (Speaker 1, Speaker 2, etc.)
         - Note: For production, integrate pyannote-audio 
           for real speaker diarization
      
      5. Topic segmentation:
         - Group transcript segments into topics based on:
           a. Long pauses (> 5 seconds)
           b. Topic shift detection (LLM-based if available)
         - Generate topic labels for each segment
      
      6. Post-processing:
         - Remove filler words optionally (um, uh, like, you know)
         - Capitalize sentence starts
         - Add punctuation (Whisper does this automatically)
         - Merge short segments into paragraphs
    
    Output: TranscriptionResult with:
      - full_text: str
      - segments: list[TranscriptionSegment]
          (start_time, end_time, speaker, text, confidence)
      - speakers: list[str] (detected speakers)
      - topics: list[Topic]
          (title, start_time, end_time, summary)
      - language: str (detected)
      - duration_seconds: float
      - word_count: int
      - audio_quality: str (good/fair/poor — based on 
        average confidence score)

    Add to config:
      whisper_model: str = "base"  # base, medium, large-v3

=== SKILL 7: video_processor.py ===

class VideoProcessor:
"""
Extracts audio for transcription + key frames for
visual analysis. Handles screen recordings, demos,
presentations, and meetings.
"""

    Process:
      import ffmpeg
      
      1. Extract audio track:
         ffmpeg.input(video_path)
         .output(audio_path, acodec='pcm_s16le', ar='16000')
         .run()
      
      2. Send audio to AudioTranscriber
      
      3. Extract key frames at scene changes:
         - Use ffmpeg scene detection filter:
           ffmpeg -i video.mp4 -vf "select=gt(scene\,0.3)" 
           -vsync vfn frame_%03d.jpg
         - Limit to max 20 key frames
         - For screen recordings: detect significant visual 
           changes (new page/screen)
      
      4. For each key frame:
         - If image_analyzer is available (and LLM vision 
           model is configured), analyze the frame:
           "Describe what's shown in this screenshot/frame 
           from a software demo"
         - Otherwise: just store the frame with timestamp
      
      5. Merge transcription with frame descriptions:
         Create a timeline linking spoken words to what's 
         visible on screen at that moment
    
    Output: VideoExtractionResult with:
      - transcription: TranscriptionResult
      - key_frames: list[KeyFrame]
          (timestamp, image_path, description)
      - duration_seconds: float
      - resolution: str (e.g., "1920x1080")
      - video_type: str (screen_recording/presentation/
        meeting/general — auto-detected from content)
      - timeline: list[TimelineEntry]
          (timestamp, spoken_text, visible_content)

=== SKILL 8: image_analyzer.py ===

class ImageAnalyzer:
"""
Analyzes images using LLM vision capabilities.
Handles: architecture diagrams, wireframes, whiteboard
photos, screenshots, ER diagrams, flowcharts.
"""

    Process:
      1. Determine image type:
         - Check resolution and aspect ratio
         - If very wide: likely a diagram or screenshot
         - If photo-like: likely whiteboard capture
         - If has sharp lines and text: likely a diagram
      
      2. If LLM vision model available (Claude, GPT-4V):
         Send image with context-specific prompt:
         
         For diagrams: "Describe this technical diagram in 
         detail. Identify all components, connections, labels, 
         and the type of diagram (architecture, ER, flowchart, 
         sequence, class, network)."
         
         For wireframes: "Describe this UI wireframe. List all 
         pages/screens, components, navigation elements, form 
         fields, and user interactions shown."
         
         For whiteboard: "Transcribe and describe everything 
         written/drawn on this whiteboard. Identify text, 
         diagrams, lists, arrows, and relationships."
         
         For screenshots: "Describe this application screenshot. 
         Identify the application type, visible features, data 
         shown, navigation elements, and any error messages."
      
      3. If no vision model available:
         - Run OCR on the image (pytesseract)
         - Detect basic features: has_text, has_lines, 
           dominant_colors, estimated_complexity
         - Return what we can
      
      4. For SVG files:
         - Parse the XML directly
         - Extract text elements
         - Identify shapes and relationships
         - No need for vision model
    
    Output: ImageAnalysis with:
      - description: str (detailed description)
      - extracted_text: str (OCR text)
      - image_type: str (diagram/wireframe/whiteboard/
        screenshot/photo/chart/unknown)
      - identified_elements: list[str]
      - dimensions: (width, height)
      - file_size_bytes: int

=== SKILL 9: archive_extractor.py ===

class ArchiveExtractor:
"""
Recursively extracts archives and processes contents.
Handles nested archives (zip inside zip).
"""

    Process:
      import zipfile, tarfile, py7zr
      
      1. Detect archive type
      2. Extract to temp directory
      3. For each extracted file:
         - Run FileDetector to classify
         - If it's another archive: recurse (max depth: 3)
         - If it's a regular file: add to the processing queue
      4. Track the directory structure for context:
         "src/controllers/UserController.java" tells us about 
         the project structure
      5. Detect project type from structure:
         - Has package.json → Node.js project
         - Has pom.xml → Java/Maven project
         - Has requirements.txt → Python project
         - Has .sln → .NET project
         - Has Cargo.toml → Rust project
      6. Skip binary files, node_modules, .git, __pycache__,
         vendor, build, dist, target directories
      7. Skip files > 10MB (likely compiled/generated)
    
    Output: ArchiveContents with:
      - files: list[ExtractedFile]
          (relative_path, file_type, size)
      - directory_structure: dict (tree representation)
      - detected_project_type: str
      - total_files: int
      - total_size_bytes: int
      - skipped_files: list[str] (and why)

=== SKILL 10: database_parser.py ===

class DatabaseParser:
"""
Parses SQL files to extract schema information,
stored procedures, triggers, views, and data
migration scripts.
"""

    Process:
      1. Detect SQL dialect (MySQL, PostgreSQL, SQL Server, 
         Oracle, SQLite) from syntax patterns
      2. Parse CREATE TABLE statements:
         - Table name
         - Columns with types and constraints
         - Primary keys
         - Foreign keys with referenced tables
         - Indexes
         - Check constraints
         - Default values
      3. Parse CREATE PROCEDURE / FUNCTION:
         - Name, parameters, return type
         - Body text for analysis
         - Detect SQL injection vulnerabilities
      4. Parse CREATE VIEW
      5. Parse CREATE TRIGGER
      6. Parse INSERT statements (sample data)
      7. Parse ALTER TABLE (schema evolution)
      8. Build entity-relationship map from foreign keys
    
    Output: ParsedDatabase with:
      - tables: list[TableDefinition]
          (name, columns, primary_key, foreign_keys, 
           indexes, constraints)
      - relationships: list[Relationship]
          (from_table, from_column, to_table, to_column, 
           relationship_type: one-to-one/one-to-many/many-to-many)
      - stored_procedures: list[ProcedureDefinition]
      - views: list[ViewDefinition]
      - triggers: list[TriggerDefinition]
      - dialect: str
      - total_tables: int
      - security_issues: list[str]
          (SQL injection in procs, plaintext sensitive data, etc.)

=== SKILL 11: email_parser.py ===

class EmailParser:
"""
Parses email files (EML, MSG) to extract
communication threads relevant to requirements.
"""

    Process:
      import email
      from email import policy
      
      1. Parse email headers:
         From, To, CC, Subject, Date
      2. Extract body (prefer plain text, fallback to HTML)
      3. Extract attachments → add to processing queue
      4. For HTML body: extract text using BeautifulSoup
      5. Detect email threads (Re:, Fwd:, quoted text)
      6. Build conversation timeline
    
    Output: ParsedEmail with:
      - subject: str
      - from_address: str
      - to_addresses: list[str]
      - date: datetime
      - body_text: str
      - attachments: list[AttachmentInfo]
      - is_reply: bool
      - thread_subject: str (without Re:/Fwd: prefixes)

=== SKILL 12: cloud_fetcher.py ===

class CloudFetcher:
"""
Downloads files from cloud storage and URLs.
Supports S3, GCS, Azure Blob, HTTP/HTTPS, SharePoint.
"""

    Process:
      1. Detect source type from URL pattern:
         s3://bucket/key → AWS S3
         gs://bucket/key → Google Cloud Storage
         https://*.blob.core.windows.net/* → Azure Blob
         https://*.sharepoint.com/* → SharePoint
         https://* or http://* → Generic HTTP
      
      2. Download based on type:
         S3: boto3.client('s3').download_file()
         GCS: storage.Client().download_blob()
         Azure: BlobServiceClient().download_blob()
         HTTP: httpx.get() with streaming for large files
         SharePoint: Use Graph API with auth token
      
      3. Handle authentication:
         S3: AWS credentials from env or IAM role
         GCS: Service account JSON from env
         Azure: Connection string from env
         SharePoint: OAuth token from env
         HTTP: Basic auth or Bearer token if provided
      
      4. Progress tracking:
         Report download progress for large files
         Support resumable downloads for files > 100MB
      
      5. Save to local temp directory for processing
    
    Output: FetchedFile with:
      - local_path: str
      - original_url: str
      - filename: str
      - file_size_bytes: int
      - content_type: str
      - source_type: str (s3/gcs/azure/http/sharepoint)
      - download_duration_seconds: float

=== SKILL 13: content_classifier.py ===

class ContentClassifier:
"""
Classifies parsed content by document type and domain.
Uses pattern matching first, LLM fallback for ambiguous cases.
"""

    Document types:
      brd — Business Requirements Document
      srs — Software Requirements Specification
      prd — Product Requirements Document
      frd — Functional Requirements Document
      trd — Technical Requirements Document
      meeting_notes — Meeting minutes and notes
      user_manual — End-user documentation
      api_documentation — API reference docs
      technical_spec — Technical specification
      architecture_doc — Architecture decision records
      test_plan — Test plans and strategies
      change_request — Change/feature requests
      email_thread — Email communications
      code_review — Code review comments
      runbook — Operations runbook
      sop — Standard operating procedure
      compliance_doc — Regulatory/compliance document
      database_doc — Database documentation
      release_notes — Release/changelog
      proposal — Vendor/project proposal
      contract — Legal agreements
      unknown — Unclassifiable
    
    Domain detection:
      healthcare — HIPAA, patients, clinical, diagnosis
      finance — SOX, transactions, ledger, accounts
      ecommerce — products, cart, orders, shipping
      government — FedRAMP, clearance, agency
      insurance — claims, policies, underwriting
      education — students, courses, enrollment
      manufacturing — inventory, supply chain, BOM
      generic — no specific domain detected
    
    Process:
      1. Pattern matching on keywords, headings, structure
      2. If ambiguous: use LLM classification
         "Classify this document: [first 2000 chars]
          Document type: one of [list]
          Domain: one of [list]
          Confidence: high/medium/low"
      3. Detect formality level (formal/semi-formal/informal)
      4. Detect completeness (complete/partial/draft)
      5. Detect language
    
    Output: ContentClassification with:
      - document_type: str
      - domain: str
      - formality: str
      - completeness: str
      - language: str
      - confidence: float
      - key_topics: list[str] (top 5 topics detected)
      - estimated_importance: str (critical/high/medium/low)

=== SKILL 14: chunker.py ===

class SmartChunker:
"""
Intelligent text chunking for vector storage.
Not just fixed-size splits — respects document structure.
"""

    Three chunking strategies:
    
    1. SEMANTIC (default for documents):
       - Split on section boundaries (headings)
       - Each section becomes one chunk
       - If section > 2000 tokens: split on paragraphs
       - If paragraph > 2000 tokens: split on sentences
       - Each chunk includes: parent heading as context prefix
       - Overlap: include last sentence of previous chunk 
         as context
    
    2. CODE (for source files):
       - Split on function/class boundaries
       - Each function/class becomes one chunk
       - Include imports and class definition in each chunk 
         for context
       - If function > 2000 tokens: split on logical blocks 
         (try/except, if/else, loops)
    
    3. SLIDING (fallback):
       - Fixed window of 1000 tokens
       - 200 token overlap
       - Used for unstructured text without clear boundaries
    
    All chunks get:
      - chunk_id: str (UUID)
      - text: str
      - token_count: int (using tiktoken cl100k_base)
      - source_file: str
      - source_section: str (heading or function name)
      - chunk_index: int (position in document)
      - total_chunks: int
      - preceding_context: str (last 100 chars of prev chunk)
    
    Output: list[TextChunk]

=== SKILL 15: deduplicator.py ===

class Deduplicator:
"""
Detects duplicate and near-duplicate content across
uploaded files. Prevents storing the same information twice.
"""

    Process:
      1. Exact duplicate detection:
         - Hash each file's content (SHA-256)
         - Flag exact matches
      
      2. Near-duplicate detection:
         - For text content: compute MinHash signatures
         - Compare similarity scores
         - If > 85% similar: flag as near-duplicate
         - Common case: same document saved in PDF and DOCX
      
      3. Subsection overlap:
         - Check if one document's content appears inside 
           another (e.g., appendix included separately)
    
    Output: DeduplicationResult with:
      - duplicates: list[DuplicatePair]
          (file_a, file_b, similarity, duplicate_type: 
           exact/near/overlap)
      - unique_files: list[str]
      - total_duplicate_content_ratio: float

=== SKILL 16: quality_scorer.py ===

class QualityScorer:
"""
Scores each file's quality and the overall collection quality.
"""

    Per-file scoring:
      - Readability: sentence length, vocabulary complexity
      - Completeness: for BRDs — are standard sections present?
      - Formatting: is the document well-structured?
      - Recency: is the document current or outdated?
      - Relevance: does the content appear to be about 
        software/technology?
    
    Collection scoring:
      - Diversity: how many different source types? (0-100)
        1 type = 30, 2 types = 50, 3 types = 70, 
        4+ types = 85, 5+ types with code = 100
      - Completeness: are key artifacts present? (0-100)
        Has requirements doc? +25
        Has technical spec? +20
        Has source code? +20
        Has database schema? +15
        Has meeting notes/communication? +10
        Has test documentation? +10
      - Volume: total content volume relative to 
        project complexity (0-100)
        < 1000 words = 20
        1000-5000 = 40
        5000-20000 = 60
        20000-50000 = 80
        50000+ = 100
      - Consistency: do documents reference each other? 
        Do versions align? (0-100)
      - Actionability: is there enough to start analysis? (0-100)
    
    Warnings generated for:
      - Single file type uploaded
      - No requirements documents detected
      - No source code (if legacy modernization expected)
      - Very low total word count
      - Documents appear outdated (> 2 years old)
      - Duplicate content detected
      - Low readability score on key documents
    
    Suggestions generated:
      Based on what's missing, suggest specific types 
      to add: "Adding a database schema would improve 
      analysis by providing entity relationship context"
    
    Output: QualityAssessment with:
      - overall_score: int (0-100)
      - file_scores: list[FileScore]
          (filename, readability, completeness, formatting, 
           recency, relevance, overall)
      - collection_scores: dict
          (diversity, completeness, volume, consistency, 
           actionability)
      - warnings: list[str]
      - suggestions: list[str]
      - ready_for_analysis: bool (score >= 50)

=== TASKS ===

Task 1: fetch_sources.py
- If any files are URLs or cloud references, download them
- Store all files in the project's storage directory
- Output: list of local file paths ready for processing

Task 2: extract_content.py
- Run FileDetector on each file
- Route to correct parser skill
- If archive: extract and recursively process contents
- Run deduplicator across all content
- Process files in parallel (asyncio.gather) where possible
- Track progress: update agent_run.output_summary after
  each file with task status and metrics
- Output: list of ParsedContent (all types unified)

Task 3: analyze_content.py
- Run ContentClassifier on each parsed content
- Run LanguageDetector
- Detect project type (legacy vs greenfield)
- Group related files (BRD + its appendix spreadsheet)
- Build file relationship map
- Output: AnalyzedContentBundle with classifications

Task 4: chunk_and_embed.py
- Run SmartChunker on each parsed content (using
  appropriate strategy per file type)
- Generate embeddings for each chunk
- Store all chunks in business_context table via
  ContextStore service
- Store file-level summaries as separate context entries
- Output: ChunkingResult with counts

Task 5: build_inventory.py
- Create comprehensive source inventory
- Include: file name, type, category, word count,
  language, key topics, quality score, classification
- Generate human-readable inventory summary
- Output: SourceInventory

Task 6: assess_quality.py
- Run QualityScorer on all content and the collection
- Generate warnings and suggestions
- Determine readiness for Discovery agent
- Output: QualityAssessment

=== WORKFLOW ===

Wire IngestWorkflow (LangGraph StateGraph):

fetch_sources → extract_content → analyze_content →
chunk_and_embed → build_inventory → assess_quality →
create_approval_gate

State tracks:
- files: list of file metadata
- parsed_content: list of parsed results
- classifications: list of classifications
- chunks_stored: int (count of context entries created)
- quality: QualityAssessment
- errors: list of any processing errors
- progress: dict with current task and file being processed

Progress updates:
After each file is processed, update agent_run.output_summary
in the database so the frontend can poll and show real-time
progress. Include:
- tasks: list with current task status
- metrics: files_processed, words_extracted, etc.
- currently_processing: filename being worked on
- errors: any files that failed (with reason)

=== ERROR HANDLING ===

Individual file failures should NOT stop the entire pipeline.
If a PDF fails to parse:
1. Log the error
2. Add to errors list with filename and reason
3. Continue processing remaining files
4. Include in the quality assessment as a warning
5. The user sees "4 of 5 files processed successfully"
   and can decide whether to proceed

=== GRACEFUL DEGRADATION ===

Not all dependencies will be installed in every environment.
Use try/except imports and fallback gracefully:

try:
import whisper
WHISPER_AVAILABLE = True
except ImportError:
WHISPER_AVAILABLE = False

If whisper not available: skip audio files, add warning
"Audio transcription not available — install whisper"

Same pattern for: pytesseract (OCR), tree-sitter (code AST),
ffmpeg (video), py7zr (7z archives)

Core parsing (PDF, DOCX, XLSX, text, code-as-text) must
always work.

=== CONFIGURATION ===

Add to src/config.py:
# Ingest settings
whisper_model: str = "base"
max_file_size_mb: int = 500
max_files_per_project: int = 100
ocr_enabled: bool = True
ocr_language: str = "eng"
chunk_size_tokens: int = 1000
chunk_overlap_tokens: int = 200
enable_code_security_scan: bool = True
parallel_processing: bool = True
max_parallel_files: int = 4
image_analysis_enabled: bool = True
archive_max_depth: int = 3
skip_directories: list = [
"node_modules", ".git", "__pycache__",
"vendor", "build", "dist", "target",
".next", ".nuxt", "venv", ".venv"
]

=== TESTS ===

Create comprehensive tests in tests/agents/ingest/:

test_file_detector.py:
- Test all file extensions map to correct parser
- Test MIME type fallback when extension is wrong
- Test extensionless files (Dockerfile, Makefile)

test_pdf_parser.py:
- Test native text PDF extraction
- Test table extraction from PDF
- Test metadata extraction
- Test OCR fallback (with a scanned PDF fixture)

test_code_parser.py:
- Test Python file: functions, classes, imports
- Test JavaScript file: functions, exports, routes
- Test SQL file: tables, foreign keys, stored procs
- Test security concern detection
- Test package.json dependency extraction

test_spreadsheet_parser.py:
- Test XLSX with multiple sheets
- Test CSV with auto-delimiter detection

test_chunker.py:
- Test semantic chunking respects headings
- Test code chunking respects function boundaries
- Test token counting accuracy
- Test overlap between chunks

test_quality_scorer.py:
- Test single document: low diversity score
- Test diverse collection: high diversity score
- Test warning generation for missing document types

test_workflow.py:
- End-to-end: upload 3 files → run IngestWorkflow →
  verify business_context has correct entries →
  verify quality assessment is generated →
  verify approval gate is created

Use the HealthTrack Pro test documents as fixtures.

Run all tests: uv run pytest tests/agents/ingest/ -v