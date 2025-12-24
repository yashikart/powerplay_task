"""
Script to convert markdown files to PDF.
Requires: pip install markdown pdfkit
Or use: pandoc design_explanation.md -o design_explanation.pdf
"""

import subprocess
import sys
import os

def convert_with_pandoc(md_file, pdf_file):
    """Convert markdown to PDF using pandoc."""
    try:
        subprocess.run(['pandoc', md_file, '-o', pdf_file], check=True)
        print(f"✓ Converted {md_file} to {pdf_file}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def convert_with_markdown_pdf(md_file, pdf_file):
    """Convert markdown to PDF using markdown-pdf."""
    try:
        subprocess.run(['markdown-pdf', '-o', pdf_file, md_file], check=True)
        print(f"✓ Converted {md_file} to {pdf_file}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

if __name__ == "__main__":
    conversions = [
        ("design_explanation.md", "design_explanation.pdf"),
        ("evaluation_notes.md", "evaluation_notes.pdf"),
        ("reflection.md", "reflection.pdf")
    ]
    
    print("Converting markdown files to PDF...")
    print("Note: Requires pandoc (https://pandoc.org/installing.html)")
    print("      Or markdown-pdf (npm install -g markdown-pdf)\n")
    
    for md_file, pdf_file in conversions:
        if not os.path.exists(md_file):
            print(f"✗ {md_file} not found, skipping")
            continue
        
        success = False
        if not success:
            success = convert_with_pandoc(md_file, pdf_file)
        if not success:
            success = convert_with_markdown_pdf(md_file, pdf_file)
        
        if not success:
            print(f"✗ Could not convert {md_file}")
            print(f"  Please install pandoc or markdown-pdf, or convert manually")
            print(f"  Alternative: Use online converter or VS Code markdown-pdf extension")

