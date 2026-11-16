from pathlib import Path
import re
from typing import Optional

# Maximum attachment size is 20 MB per PRP-003 REQ-09
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024
MAX_FILES_PER_RFQ = 2
MAX_FILES_PER_SUPPORT = 2

ALLOWED_EXTENSIONS = {
    # Visual previews supported (REQ-09)
    '.pdf': 'application/pdf',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.webp': 'image/webp',
    # Engineering CAD / Blueprints (downloadable, REQ-09)
    '.step': 'application/step',
    '.stp': 'application/step',
    '.iges': 'model/iges',
    '.igs': 'model/iges',
    '.stl': 'model/stl',
    '.dwg': 'image/vnd.dwg',
    '.dxf': 'image/vnd.dxf',
}

SUPPORT_ALLOWED_EXTENSIONS = {
    '.pdf': 'application/pdf',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
}

PREVIEWABLE_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.webp'}


def sanitize_filename(filename: str) -> str:
    """Sanitizes an incoming user filename to remove path traversal and risky characters."""
    base = Path(filename).name.strip()
    # Replace dangerous characters with underscore
    clean = re.sub(r'[\0/\\:\*\?"<>\|]', '_', base)
    if not clean or clean in ('.', '..'):
        clean = 'attachment'
    return clean[:255]


def is_previewable(filename: str) -> bool:
    """Checks whether the file extension supports in-browser image/PDF preview."""
    ext = Path(filename).suffix.lower()
    return ext in PREVIEWABLE_EXTENSIONS


def validate_file_content(content: bytes, ext: str) -> None:
    """
    Performs server-side content verification (REQ-09 / AC-03-07):
    - Rejects empty files (0 bytes)
    - Rejects files exceeding 20 MB
    - Rejects executable / script payloads masquerading as CAD/drawings
    - Verifies content magic signatures against claimed extension
    """
    if not content or len(content) == 0:
        raise ValueError('Empty files cannot be uploaded.')

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise ValueError('File size exceeds the maximum permitted limit of 20 MB.')

    # Prohibit dangerous binary executables and scripts
    if content.startswith(b'MZ'):
        raise ValueError('Windows executable binaries (.exe/.dll) are prohibited.')
    if content.startswith(b'\x7fELF'):
        raise ValueError('Linux executable binaries are prohibited.')
    if content.startswith(b'\xca\xfe\xba\xbe'):
        raise ValueError('Compiled binary files are prohibited.')
    if content.startswith(b'#!'):
        raise ValueError('Script files are prohibited.')

    # Signature verification per claimed format
    if ext == '.png':
        if not content.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('File signature does not match valid PNG image format.')
    elif ext in ('.jpg', '.jpeg'):
        if not content.startswith(b'\xff\xd8\xff'):
            raise ValueError('File signature does not match valid JPEG image format.')
    elif ext == '.pdf':
        if not content.startswith(b'%PDF-'):
            raise ValueError('File signature does not match valid PDF document format.')
    elif ext == '.webp':
        if len(content) < 12 or not (content.startswith(b'RIFF') and content[8:12] == b'WEBP'):
            raise ValueError('File signature does not match valid WEBP image format.')
    elif ext in ('.step', '.stp'):
        # ISO-10303-21 CAD text header inspection
        header_sample = content[:2048].decode('utf-8', errors='ignore').strip()
        if 'ISO-10303-21' not in header_sample:
            raise ValueError('File content does not match valid STEP CAD (ISO-10303-21) structure.')
    elif ext in ('.iges', '.igs'):
        # IGES fixed-column or section card inspection
        sample = content[:2048].decode('ascii', errors='ignore')
        if not any(marker in sample for marker in ('S', 'G', 'D', 'P', 'T')):
            raise ValueError('File content does not match valid IGES CAD structure.')
    elif ext == '.stl':
        # ASCII STL starts with 'solid' or binary STL has an 80-byte header + triangle count
        if not (content.lower().startswith(b'solid') or len(content) >= 84):
            raise ValueError('File content does not match valid STL CAD structure.')
    elif ext == '.dwg':
        # Standard AutoCAD DWG header begins with AC10xx
        if not content.startswith(b'AC10'):
            raise ValueError('File content does not match valid AutoCAD DWG header (AC10xx).')
    elif ext == '.dxf':
        sample = content[:2048].decode('utf-8', errors='ignore')
        if 'SECTION' not in sample and 'HEADER' not in sample:
            raise ValueError('File content does not match valid DXF structure.')


def validate_support_file_content(content: bytes, filename: str) -> tuple[str, str]:
    """
    Validates file for Support Tickets (PRP-009 / REQ-30 / AC-09-02):
    - Rejects files outside JPG, PNG, PDF
    - Enforces 20 MB size limit
    - Sanitizes filename
    - Verifies file signatures
    """
    clean_name = sanitize_filename(filename)
    ext = Path(clean_name).suffix.lower()

    if ext not in SUPPORT_ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file format '{ext}'. Support attachments only permit JPG, PNG, and PDF files."
        )

    validate_file_content(content, ext)
    content_type = SUPPORT_ALLOWED_EXTENSIONS[ext]
    return clean_name, content_type
