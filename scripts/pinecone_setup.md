# Pinecone Setup Instructions

## 1. Create Index

In the Pinecone console (https://app.pinecone.io/), create a new index with these settings:

- **Index Name**: `co-teacher-memory`
- **Dimensions**: `1536` (for RPRTHPB-text-embedding-3-small)
- **Metric**: `cosine`
- **Cloud**: AWS
- **Region**: `us-east-1` (or your preferred region)

## 2. Namespaces

The index will use the following namespaces to organize different types of data:

| Namespace | Purpose |
|-----------|---------|
| `student-profiles` | Student profile vectors (triggers, methods, learning styles) |
| `teaching-methods` | RAG knowledge base (evidence-based teaching strategies) |
| `interventions` | Historical intervention outcomes |

## 3. Metadata Schema

### student-profiles namespace
```json
{
    "student_id": "string",
    "name": "string",
    "grade": "string",
    "disability_type": "string",
    "learning_style": "string",
    "triggers": ["string"],
    "successful_methods": ["string"],
    "failed_methods": ["string"],
    "last_updated": "ISO timestamp"
}
```

### teaching-methods namespace
```json
{
    "method_id": "string",
    "method_name": "string",
    "category": "string (behavior|academic|social|sensory)",
    "applicable_disabilities": ["string"],
    "grade_range": "string (K-2|3-5|6-8|9-12|all)",
    "resource_requirements": "string (none|low|medium|high)",
    "evidence_level": "string (research-based|promising|emerging)",
    "time_to_implement": "string (immediate|short-term|long-term)"
}
```

### interventions namespace
```json
{
    "intervention_id": "string",
    "student_id": "string",
    "method_used": "string",
    "context": "string",
    "outcome": "string (successful|partial|unsuccessful)",
    "teacher_notes": "string",
    "date": "ISO date"
}
```

## 4. Get API Key

1. Go to API Keys in Pinecone console
2. Copy your API key
3. Add to `.env` file:
   ```
   PINECONE_API_KEY=your_api_key_here
   PINECONE_INDEX_NAME=co-teacher-memory
   PINECONE_ENVIRONMENT=us-east-1
   ```

## 5. Verify Setup

Run this Python code to verify:

```python
from pinecone import Pinecone

pc = Pinecone(api_key="your_api_key")
index = pc.Index("co-teacher-memory")
print(index.describe_index_stats())
```

Expected output:
```
{'dimension': 1536, 'index_fullness': 0.0, 'namespaces': {}, 'total_vector_count': 0}
```
