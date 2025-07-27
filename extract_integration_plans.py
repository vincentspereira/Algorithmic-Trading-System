import docx
import re

def extract_sections(doc_path):
    """
    Reads a .docx file and extracts content under specific headings for 
    Phase 1, 2, and 3 Integration Plans.
    """
    try:
        document = docx.Document(doc_path)
        
        # More flexible regex patterns to find the headings, ignoring minor variations in formatting
        phase_patterns = {
            "Phase 1": re.compile(r"Integration\s+Plan\s*&\s*Actions\s+for\s+Phase\s+1", re.IGNORECASE),
            "Phase 2": re.compile(r"Integration\s+Plan\s*&\s*Actions\s+for\s+Phase\s+2", re.IGNORECASE),
            "Phase 3": re.compile(r"Integration\s+Plan\s*&\s*Actions\s+for\s+Phase\s+3", re.IGNORECASE),
            "Phase 4": re.compile(r"Integration\s+Plan\s*&\s*Actions\s+for\s+Phase\s+4", re.IGNORECASE)
        }
        
        extracted_content = { "Phase 1": "", "Phase 2": "", "Phase 3": "", "Phase 4": "" }
        current_phase = None

        for para in document.paragraphs:
            # Check if the paragraph text matches any of the phase headings
            is_heading = False
            for phase, pattern in phase_patterns.items():
                if pattern.search(para.text):
                    current_phase = phase
                    is_heading = True
                    break # Found a heading, no need to check other patterns for this paragraph
            
            # Stop capturing when a new major heading is found
            # Stop capturing if a new phase's integration plan begins or if we hit the end of the phase goals.
            if not is_heading and current_phase:
                # Check for the next phase's integration plan
                next_phase_found = False
                for phase, pattern in phase_patterns.items():
                    if pattern.search(para.text):
                        next_phase_found = True
                        break
                # Check for "End of Phase" goals, which signals the end of the section
                if next_phase_found or "End of Phase" in para.text:
                    current_phase = None
                    continue
                
            # If we are inside one of the target sections, capture the content
            if current_phase and not is_heading:
                if para.text.strip():
                    # Handle lists by adding a bullet point
                    if para.style.name.startswith('List'):
                        extracted_content[current_phase] += f"- {para.text}\n"
                    else:
                        extracted_content[current_phase] += f"{para.text}\n\n"

        # Format the output as Markdown
        markdown_output = ""
        for phase, content in extracted_content.items():
            if content:
                markdown_output += f"## {phase}: Integration Plan & Actions\n\n{content.strip()}\n\n"
        
        return markdown_output.strip()

    except FileNotFoundError:
        return f"Error: Document not found at '{doc_path}'"
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    doc_path = "docs/01. Features, Phases & Integration Strategy - Algorithmic Trading System.docx"
    markdown_content = extract_sections(doc_path)
    print(markdown_content)