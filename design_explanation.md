# Design Explanation: Structured JSON Extraction from Business Text

## Core Design Philosophy

The system uses a **multi-stage validation pipeline** with explicit schema enforcement, not relying solely on prompt engineering. This ensures reliability even when the LLM makes mistakes.

## LLM Workflow Design

### Stage 1: Structured Prompting
- **Explicit schema definition** in the prompt with examples
- **Field-by-field extraction instructions** with clear null handling rules
- **Output format constraint**: JSON only, no markdown, no explanations
- **Temperature = 0** to minimize randomness

### Stage 2: JSON Parsing & Validation
- Parse LLM output with error handling
- If parsing fails → extract JSON from markdown code blocks or retry with stricter prompt
- Validate against schema using JSON Schema validator
- Reject any extra fields not in schema

### Stage 3: Schema Enforcement
- **Whitelist approach**: Only accept fields defined in schema
- **Type coercion**: Convert strings to numbers where needed
- **Null assignment**: Missing fields → null (explicit, not omitted)
- **Date validation**: ISO 8601 format only, invalid dates → null

### Stage 4: Urgency Inference Logic
- **High**: Keywords like "urgent", "asap", "immediately", "critical", "emergency", time constraints < 7 days
- **Medium**: "soon", "priority", time constraints 7-30 days, or explicit deadlines
- **Low**: Default when no urgency indicators present, or deadlines > 30 days away

## Handling Edge Cases

### Missing Fields
- **Strategy**: Explicit null assignment in prompt
- **Implementation**: Post-processing ensures all schema fields exist, missing ones set to null
- **Rationale**: Consistent schema structure prevents downstream errors

### Misinterpreted Context
- **Strategy**: Multi-pass extraction with field-specific prompts if needed
- **Fallback**: Pattern matching for common entities (dates, quantities, locations)
- **Validation**: Cross-check extracted values against input text

### Extra Fields
- **Strategy**: Schema whitelist - discard any field not in defined schema
- **Implementation**: Filter output dictionary to only include schema fields
- **Rationale**: Prevents schema drift and maintains consistency

### Invalid JSON
- **Strategy**: Multi-layer recovery
  1. Try direct JSON parsing
  2. Extract from markdown code blocks (```json ... ```)
  3. Use regex to find JSON object
  4. If all fail, construct minimal valid JSON with nulls

### Uncertain Deadlines
- **Strategy**: Conservative approach
- **Rules**: 
  - Vague dates ("soon", "later") → null
  - Relative dates without context → null
  - Ambiguous month references → null
  - Only parse explicit dates with clear format

## Key Design Decisions

1. **Explicit over implicit**: Always return all schema fields, even if null
2. **Fail-safe defaults**: When uncertain, use null or "low" urgency
3. **Post-processing validation**: Don't trust LLM output blindly
4. **Deterministic urgency**: Rule-based logic prevents inconsistent classifications
5. **Schema-first**: Structure enforced programmatically, not just by prompt

