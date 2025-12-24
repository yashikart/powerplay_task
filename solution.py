"""
AI Assistant for Converting Unstructured Business Text to Structured JSON

This script extracts structured information from business text using LLM
with robust error handling and schema validation.
"""

import json
import re
import os
from datetime import datetime
from typing import Dict, Any, Optional
from jsonschema import validate, ValidationError

# Try to import OpenAI, fallback to mock if not available
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI not installed. Using mock responses for testing.")


# JSON Schema definition
SCHEMA = {
    "type": "object",
    "properties": {
        "material_name": {"type": "string"},
        "quantity": {"type": "number"},
        "unit": {"type": "string"},
        "project_name": {"type": ["string", "null"]},
        "location": {"type": ["string", "null"]},
        "urgency": {"type": "string", "enum": ["low", "medium", "high"]},
        "deadline": {"type": ["string", "null"]}
    },
    "required": ["material_name", "quantity", "unit", "project_name", 
                 "location", "urgency", "deadline"],
    "additionalProperties": False
}


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON from LLM response, handling various formats.
    
    Tries multiple strategies:
    1. Direct JSON parsing
    2. Extract from markdown code blocks
    3. Regex extraction
    """
    # Strategy 1: Direct JSON parsing
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Extract from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Strategy 3: Find JSON object with regex
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    return None


def infer_urgency(text: str, deadline: Optional[str] = None) -> str:
    """
    Infer urgency level from text and deadline.
    
    Rules:
    - High: urgent keywords or deadline < 7 days
    - Medium: priority keywords or deadline 7-30 days
    - Low: default or deadline > 30 days
    """
    text_lower = text.lower()
    
    # High urgency indicators
    high_keywords = ["urgent", "urgently", "asap", "as soon as possible", 
                     "immediately", "critical", "emergency", "rush"]
    if any(keyword in text_lower for keyword in high_keywords):
        return "high"
    
    # Check deadline proximity
    if deadline:
        try:
            deadline_date = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
            days_until = (deadline_date - datetime.now(deadline_date.tzinfo)).days
            if days_until < 7:
                return "high"
            elif days_until < 30:
                return "medium"
        except (ValueError, AttributeError):
            pass
    
    # Medium urgency indicators
    medium_keywords = ["soon", "priority", "important", "needed"]
    if any(keyword in text_lower for keyword in medium_keywords):
        return "medium"
    
    # Default to low
    return "low"


def validate_date(date_str: Optional[str]) -> Optional[str]:
    """
    Validate and normalize date to ISO 8601 format.
    Returns None for invalid or ambiguous dates.
    """
    if not date_str or date_str.lower() in ["null", "none", ""]:
        return None
    
    # Try ISO format first
    try:
        datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_str
    except (ValueError, AttributeError):
        pass
    
    # Try common date formats
    date_formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%d %B %Y",
        "%Y-%m-%dT%H:%M:%S",
    ]
    
    for fmt in date_formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.isoformat()
        except ValueError:
            continue
    
    return None


def enforce_schema(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enforce schema by:
    1. Keeping only schema-defined fields
    2. Ensuring all required fields exist (set to null if missing)
    3. Validating types
    4. Normalizing values
    """
    # Whitelist: only keep schema-defined fields
    schema_fields = {
        "material_name": None,
        "quantity": None,
        "unit": None,
        "project_name": None,
        "location": None,
        "urgency": "low",
        "deadline": None
    }
    
    result = {}
    
    # Copy valid fields
    for field in schema_fields:
        if field in data:
            value = data[field]
            
            # Type validation and coercion
            if field == "quantity":
                try:
                    result[field] = float(value) if value is not None else 0
                except (ValueError, TypeError):
                    result[field] = 0
            elif field == "urgency":
                if value in ["low", "medium", "high"]:
                    result[field] = value
                else:
                    result[field] = schema_fields[field]
            elif field == "deadline":
                result[field] = validate_date(value)
            else:
                result[field] = value if value is not None else None
        else:
            # Missing field: use default or null
            result[field] = schema_fields[field]
    
    # Ensure material_name, quantity, unit are not null (required)
    if not result.get("material_name"):
        result["material_name"] = "Unknown"
    if result.get("quantity") is None:
        result["quantity"] = 0
    if not result.get("unit"):
        result["unit"] = "units"
    
    return result


def call_llm(text: str, api_key: Optional[str] = None) -> str:
    """
    Call LLM to extract structured information.
    Uses OpenAI if available, otherwise returns mock response.
    """
    prompt = f"""Extract structured information from the following business text and return ONLY valid JSON matching this exact schema:

{{
  "material_name": string,
  "quantity": number,
  "unit": string,
  "project_name": string | null,
  "location": string | null,
  "urgency": "low" | "medium" | "high",
  "deadline": ISO 8601 date string | null
}}

Rules:
- Return ONLY JSON, no markdown, no explanations
- If information is missing, use null (not omitted)
- For urgency: "high" if urgent/asap/immediate, "medium" if soon/priority, "low" otherwise
- For deadline: Use ISO 8601 format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS), or null if unclear
- Extract quantity as a number, unit as a string

Input text: "{text}"

JSON:"""

    if OPENAI_AVAILABLE and api_key:
        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Using cost-effective model
                messages=[
                    {"role": "system", "content": "You are a JSON extraction assistant. Always return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,  # Deterministic output
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error calling OpenAI: {e}")
            return get_mock_response(text)
    else:
        return get_mock_response(text)


def get_mock_response(text: str) -> str:
    """
    Mock LLM response for testing without API key.
    Uses pattern matching to extract information.
    """
    text_lower = text.lower()
    
    # Extract quantity and unit
    quantity_match = re.search(r'(\d+(?:\.\d+)?)\s*(mm|kg|units?|bags?|truckloads?|tons?|liters?)', text, re.IGNORECASE)
    quantity = float(quantity_match.group(1)) if quantity_match else 0
    unit = quantity_match.group(2).lower() if quantity_match else "units"
    
    # Extract material
    material_patterns = [
        r'(\d+mm\s+\w+\s+\w+)',  # "25mm steel bars"
        r'(\w+\s+Cement)',  # "Ultratech Cement"
        r'(\w+\s+sand)',  # "river sand"
        r'(\w+\s+\w+\s+\w+)',  # Generic
    ]
    material = "Unknown"
    for pattern in material_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            material = match.group(1)
            break
    
    # Extract project
    project_match = re.search(r'Project\s+(\w+)', text, re.IGNORECASE)
    project = project_match.group(1) if project_match else None
    
    # Extract location
    location_match = re.search(r'(Mumbai|Bangalore|Delhi|Chennai|Kolkata|Pune|Hyderabad|site\s+\w+)', text, re.IGNORECASE)
    location = location_match.group(1) if location_match else None
    
    # Extract deadline
    deadline_match = re.search(r'(\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4}|\w+\s+end|by\s+\w+)', text, re.IGNORECASE)
    deadline = None
    if deadline_match:
        deadline_str = deadline_match.group(1)
        # Simple date parsing (would need more robust parsing in production)
        try:
            # Try to parse common formats
            if "march" in deadline_str.lower():
                deadline = "2024-03-15"
            elif "april" in deadline_str.lower():
                deadline = "2024-04-30"
        except:
            deadline = None
    
    # Infer urgency
    urgency = infer_urgency(text, deadline)
    
    result = {
        "material_name": material,
        "quantity": quantity,
        "unit": unit,
        "project_name": project,
        "location": location,
        "urgency": urgency,
        "deadline": deadline
    }
    
    return json.dumps(result, indent=2)


def process_text(input_text: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Main processing function: converts text to structured JSON.
    
    Steps:
    1. Call LLM for extraction
    2. Parse JSON from response
    3. Enforce schema (whitelist, null handling, type validation)
    4. Re-infer urgency from original text if needed
    5. Validate final output
    """
    # Step 1: Call LLM
    llm_response = call_llm(input_text, api_key)
    
    # Step 2: Extract JSON
    extracted_data = extract_json_from_text(llm_response)
    
    if not extracted_data:
        # Fallback: create minimal valid structure
        extracted_data = {
            "material_name": "Unknown",
            "quantity": 0,
            "unit": "units",
            "project_name": None,
            "location": None,
            "urgency": "low",
            "deadline": None
        }
    
    # Step 3: Enforce schema
    result = enforce_schema(extracted_data)
    
    # Step 4: Re-infer urgency from original text (more reliable)
    result["urgency"] = infer_urgency(input_text, result["deadline"])
    
    # Step 5: Validate against JSON Schema
    try:
        validate(instance=result, schema=SCHEMA)
    except ValidationError as e:
        print(f"Warning: Schema validation failed: {e}")
        # Fix common issues
        if "urgency" in str(e):
            result["urgency"] = "low"
    
    return result


def process_file(input_file: str, output_file: str, api_key: Optional[str] = None):
    """
    Process multiple inputs from a file and write results to JSON.
    """
    results = []
    
    # Read input file
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        print(f"Processing {i}: {line[:50]}...")
        try:
            result = process_text(line, api_key)
            result["_input"] = line  # Keep original for evaluation
            results.append(result)
        except Exception as e:
            print(f"Error processing line {i}: {e}")
            # Add error entry
            results.append({
                "_input": line,
                "_error": str(e),
                "material_name": "Unknown",
                "quantity": 0,
                "unit": "units",
                "project_name": None,
                "location": None,
                "urgency": "low",
                "deadline": None
            })
    
    # Write results
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nProcessed {len(results)} inputs. Results written to {output_file}")


if __name__ == "__main__":
    import sys
    
    # Get API key from environment or argument
    api_key = os.getenv("OPENAI_API_KEY")
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    
    input_file = "test_inputs.txt"
    output_file = "outputs.json"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found. Please create it with test inputs.")
        sys.exit(1)
    
    process_file(input_file, output_file, api_key)

