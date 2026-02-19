# Database Setup Guide - Co-Teacher Project

This guide walks you through setting up Supabase and Pinecone for the Proactive Co-Teacher project.

---

## Part 1: Supabase Setup (Primary Database)

### Step 1: Create Supabase Project

1. **Go to:** https://supabase.com/dashboard
2. **Click:** "New Project"
3. **Fill in:**
   - **Project Name:** `co-teacher` (or your preferred name)
   - **Database Password:** Create a strong password (save it securely!)
   - **Region:** Choose closest to you (e.g., `us-east-1`)
   - **Pricing Plan:** Free tier is fine for development
4. **Click:** "Create new project"
5. **Wait:** ~2 minutes for project to initialize

### Step 2: Get Supabase API Credentials

Once your project is ready:

1. **Go to:** Project Settings (gear icon in left sidebar)
2. **Click:** "API" in the settings menu
3. **Copy these values:**
   ```
   Project URL: https://[your-project-ref].supabase.co
   anon public key: eyJ... (long string starting with eyJ)
   ```
4. **Save for later** - you'll need these in your `.env` file

### Step 3: Create Database Schema

1. **Go to:** SQL Editor (left sidebar)
2. **Click:** "+ New query"
3. **Open:** `c:\code\co_teacher\scripts\supabase_schema.sql` in a text editor
4. **Copy entire contents** and paste into Supabase SQL Editor
5. **Click:** "Run" (or press Ctrl+Enter)
6. **Verify:** You should see "Success. No rows returned" message

**Tables created:**
- ✅ conversations
- ✅ conversation_messages
- ✅ daily_context
- ✅ alerts_sent
- ✅ pending_feedback
- ✅ response_cache
- ✅ budget_tracking
- ✅ events
- ✅ schedule_templates

### Step 4: Add Students Table (Optional - for extended features)

The project can store student data in Pinecone only, but for better querying, you can add a students table:

1. **In SQL Editor**, run this additional query:
   ```sql
   CREATE TABLE IF NOT EXISTS students_table (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       student_id VARCHAR(100) UNIQUE NOT NULL,
       name VARCHAR(255) NOT NULL,
       grade VARCHAR(10),
       age INTEGER,
       disability_type VARCHAR(100),
       learning_style VARCHAR(50),
       triggers TEXT[],
       successful_methods TEXT[],
       failed_methods TEXT[],
       iep_goals TEXT[],
       accommodations TEXT[],
       notes TEXT,
       created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
       updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
   );
   
   CREATE INDEX IF NOT EXISTS idx_students_student_id ON students_table(student_id);
   CREATE INDEX IF NOT EXISTS idx_students_name ON students_table(name);
   ```

### Step 5: Seed Initial Data (Optional)

If you want to populate schedule templates:

1. **Open:** `c:\code\co_teacher\scripts\seed_schedule_templates.sql`
2. **Copy contents** and paste in SQL Editor
3. **Click:** "Run"

### Step 6: Verify Setup

1. **Go to:** Table Editor (left sidebar)
2. **Verify:** You should see all tables listed:
   - conversations
   - conversation_messages
   - daily_context
   - alerts_sent
   - pending_feedback
   - response_cache
   - budget_tracking
   - events
   - schedule_templates
   - students_table (if you added it)

---

## Part 2: Pinecone Setup (Vector Database)

### Step 1: Create Pinecone Index

1. **Go to:** https://app.pinecone.io/
2. **Click:** "Create Index" (or "Indexes" → "Create Index")
3. **Fill in:**
   - **Index Name:** `co-teacher-memory`
   - **Dimensions:** `1536`
   - **Metric:** `cosine`
   - **Cloud Provider:** AWS (recommended)
   - **Region:** `us-east-1` (or closest to your Supabase region)
4. **Click:** "Create Index"
5. **Wait:** ~1-2 minutes for index creation

**Why 1536 dimensions?** This matches the OpenAI text-embedding-3-small model (used by RPRTHPB-text-embedding-3-small on LLMod.ai)

### Step 2: Get Pinecone API Key

1. **Click:** "API Keys" in left sidebar
2. **Copy:** Your API key (starts with `pc-...` or similar)
3. **Environment:** Should show your region (e.g., `us-east-1`)
4. **Save for later**

**Security Note:** Don't share this key! It has full access to your index.

### Step 3: Verify Index Configuration

1. **Go to:** Indexes → `co-teacher-memory`
2. **Verify settings:**
   - Dimensions: 1536 ✓
   - Metric: cosine ✓
   - Status: Ready ✓

---

## Part 3: Configure Environment Variables

### Step 1: Create `.env` File

In your project root (`c:\code\co_teacher\`), create a file named `.env`:

```bash
# Create .env file (PowerShell)
New-Item -Path .env -ItemType File -Force
```

### Step 2: Add Credentials

Open `.env` in your editor and add:

```env
# LLMod.ai API (you should already have this)
LLMOD_API_KEY=your_llmod_api_key_here
LLMOD_BASE_URL=https://api.llmod.ai/v1
LLMOD_CHAT_MODEL=RPRTHPB-gpt-5-mini
LLMOD_EMBEDDING_MODEL=RPRTHPB-text-embedding-3-small

# Supabase (from Step 1.2)
SUPABASE_URL=https://[your-project-ref].supabase.co
SUPABASE_KEY=eyJ[your-anon-key]

# Pinecone (from Step 2.2)
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=co-teacher-memory
PINECONE_ENVIRONMENT=us-east-1

# Budget Settings
BUDGET_LIMIT=13.00
BUDGET_WARNING_THRESHOLD=10.00

# Debug (optional)
DEBUG=false
```

**Replace:**
- `your_llmod_api_key_here` → Your LLMod.ai API key
- `[your-project-ref]` → Your Supabase project URL
- `eyJ[your-anon-key]` → Your Supabase anon key
- `your_pinecone_api_key_here` → Your Pinecone API key
- `us-east-1` → Your Pinecone region (if different)

### Step 3: Verify Configuration

Test that your environment variables are loaded:

```powershell
# In PowerShell
python -c "from app.config import get_settings; s = get_settings(); print(f'Supabase: {s.supabase_url[:30]}... OK' if s.supabase_url else 'Missing SUPABASE_URL'); print(f'Pinecone: OK' if s.pinecone_api_key else 'Missing PINECONE_API_KEY')"
```

You should see:
```
Supabase: https://xxx.supabase.co... OK
Pinecone: OK
```

---

## Part 4: Seed Databases with Project Data

Now that both databases are configured, let's populate them with your project's seed data.

### Step 1: Install Python Dependencies

Make sure you have all required packages:

```powershell
pip install -r requirements.txt
```

### Step 2: Verify Data Files

Check that these files exist:
```powershell
# Check seed data files
Test-Path data\seed_students.json
Test-Path data\teaching_methods.json
```

Both should return `True`.

### Step 3: Seed Pinecone (Students + Teaching Methods)

Run the Pinecone seeding script:

```powershell
python -m scripts.seed_pinecone
```

**Expected output:**
```
Found X students to seed
  Seeding Alex Johnson (STU001)...
    ✓ Alex Johnson added
  Seeding Jordan Smith (STU002)...
    ✓ Jordan Smith added
  ...

Found XX teaching methods to seed
  Seeding Visual Schedules...
    ✓ Visual Schedules added
  ...

✓ Pinecone seeding complete!
```

**What this does:**
1. Loads `data/seed_students.json` (student profiles)
2. Loads `data/teaching_methods.json` (teaching strategies)
3. Generates embeddings using LLMod.ai
4. Uploads to Pinecone namespaces:
   - `student-profiles` → Student data
   - `teaching-methods` → RAG knowledge base

**Time:** ~2-5 minutes (depends on number of students/methods)

**Cost:** ~$0.01-0.05 (embeddings are very cheap)

### Step 4: Seed Supabase (Optional - Students Table)

If you created the students_table in Supabase, you can sync it:

```powershell
python -m scripts.sync_students
```

This copies student data from your JSON file to Supabase for easier querying.

### Step 5: Verify Data in Pinecone

Check that data was uploaded:

```powershell
python -c "from pinecone import Pinecone; pc = Pinecone(api_key='YOUR_KEY'); idx = pc.Index('co-teacher-memory'); print(idx.describe_index_stats())"
```

**Replace `YOUR_KEY`** with your actual Pinecone API key.

**Expected output:**
```json
{
  "dimension": 1536,
  "index_fullness": 0.001,
  "namespaces": {
    "student-profiles": {"vector_count": 5},
    "teaching-methods": {"vector_count": 30}
  },
  "total_vector_count": 35
}
```

The counts will vary based on your seed data.

### Step 6: Verify Data in Supabase

1. **Go to:** Supabase Dashboard → Table Editor
2. **Click:** `students_table` (if you created it)
3. **Verify:** You should see student records
4. **Click:** Other tables to verify they were created (they'll be empty initially)

---

## Part 5: Test Database Connections

### Test Script

Create a test to verify everything works:

```powershell
# Create test file
@"
import asyncio
from app.memory.memory_manager import get_memory_manager
from app.core.llm_client import get_llm_client

async def test_connections():
    print('Testing database connections...\n')
    
    # Test LLM Client
    print('1. Testing LLMod.ai...')
    llm = get_llm_client()
    result = await llm.complete([{'role': 'user', 'content': 'Say hello'}])
    print(f'   ✓ LLMod.ai working: {result[\"content\"][:30]}...\n')
    
    # Test Memory Manager
    print('2. Testing Supabase...')
    memory = get_memory_manager()
    convo_id = await memory.supabase.create_conversation('test-session', 'test-teacher')
    print(f'   ✓ Supabase working: Created conversation {convo_id}\n')
    
    # Test Pinecone
    print('3. Testing Pinecone...')
    student = await memory.pinecone.get_student_profile('STU001')
    if student:
        print(f'   ✓ Pinecone working: Found student {student.get(\"name\")}\n')
    else:
        print('   ⚠ Pinecone connected but no student found (did you run seed script?)\n')
    
    print('✓ All database connections successful!')

if __name__ == '__main__':
    asyncio.run(test_connections())
"@ | Out-File -FilePath test_db_connections.py -Encoding UTF8

# Run test
python test_db_connections.py
```

**Expected output:**
```
Testing database connections...

1. Testing LLMod.ai...
   ✓ LLMod.ai working: Hello! How can I help you...

2. Testing Supabase...
   ✓ Supabase working: Created conversation abc-123...

3. Testing Pinecone...
   ✓ Pinecone working: Found student Alex Johnson

✓ All database connections successful!
```

---

## Part 6: Update Render Configuration

For your Render deployment, you'll need to add these environment variables in the Render dashboard.

### Step 1: Go to Render Dashboard

1. **Navigate to:** https://dashboard.render.com/
2. **Select:** Your `co-teacher` service (or create it if not yet deployed)
3. **Go to:** Environment tab

### Step 2: Add Environment Variables

Click "Add Environment Variable" and add each of these:

| Key | Value | Notes |
|-----|-------|-------|
| `LLMOD_API_KEY` | (your key) | From LLMod.ai dashboard |
| `SUPABASE_URL` | https://[ref].supabase.co | From Supabase settings |
| `SUPABASE_KEY` | eyJ... | Anon public key from Supabase |
| `PINECONE_API_KEY` | pc-... | From Pinecone API Keys |
| `PINECONE_INDEX_NAME` | co-teacher-memory | Must match your index name |
| `PINECONE_ENVIRONMENT` | us-east-1 | Your Pinecone region |
| `BUDGET_LIMIT` | 13.00 | Course project budget |
| `BUDGET_WARNING_THRESHOLD` | 10.00 | Warning at $10 |

**Note:** Your `render.yaml` already has these configured, but values marked as `sync: false` must be manually set in the Render dashboard.

### Step 3: Deploy

After adding environment variables:

1. **Click:** "Manual Deploy" → "Deploy latest commit"
2. **Wait:** ~5-10 minutes for build and deployment
3. **Verify:** Health check passes at `https://[your-app].onrender.com/health`

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'supabase'"

**Fix:**
```powershell
pip install supabase-py
```

### Issue: "ModuleNotFoundError: No module named 'pinecone'"

**Fix:**
```powershell
pip install pinecone-client
```

### Issue: "PINECONE_API_KEY not found"

**Fix:** Make sure your `.env` file is in the project root and doesn't have typos.

### Issue: Pinecone seed script fails with "Dimension mismatch"

**Fix:** Your index must have **1536 dimensions**. Delete the index and recreate it with the correct dimensions.

### Issue: Supabase connection fails

**Fix:**
1. Check your `SUPABASE_URL` is correct (no trailing slash)
2. Verify you're using the **anon public key**, not the service role key
3. Make sure your Supabase project is **active** (not paused)

### Issue: Seed script runs but no data in Pinecone

**Fix:**
1. Check that `data/seed_students.json` exists and has valid JSON
2. Verify your LLMOD_API_KEY is valid (embeddings need to work)
3. Check Pinecone dashboard to see if vectors were added

---

## Next Steps

After completing this setup:

1. ✅ **Test the API:** Run `python -m uvicorn app.main:app --reload` and test endpoints
2. ✅ **Open Frontend:** Visit http://localhost:8000 and try asking about students
3. ✅ **Check Budget:** Visit http://localhost:8000/api/execute/budget to see costs
4. ✅ **Deploy to Render:** Push to GitHub and deploy

---

## Summary Checklist

Use this checklist to track your progress:

### Supabase Setup
- [ ] Created Supabase project
- [ ] Copied URL and API key
- [ ] Ran `supabase_schema.sql` to create tables
- [ ] Verified tables exist in Table Editor
- [ ] Added credentials to `.env` file

### Pinecone Setup
- [ ] Created Pinecone index (name: `co-teacher-memory`, dims: 1536)
- [ ] Copied API key and region
- [ ] Added credentials to `.env` file
- [ ] Ran `scripts/seed_pinecone.py` successfully
- [ ] Verified vectors exist in Pinecone dashboard

### Local Testing
- [ ] `.env` file configured with all credentials
- [ ] Tested database connections with test script
- [ ] Ran local server and tested API endpoints
- [ ] Tested frontend with real queries

### Render Deployment
- [ ] Added environment variables in Render dashboard
- [ ] Deployed successfully
- [ ] Verified health check endpoint works
- [ ] Tested deployed API endpoints

---

**Need Help?** Check the project's README or create an issue in your GitHub repo.

**Estimated Setup Time:** 30-45 minutes (including database seeding)

**Estimated Cost:** $0.01-0.10 for initial seeding (embeddings)
