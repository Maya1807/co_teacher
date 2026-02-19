# Database Setup - Quick Checklist

Use this checklist while following the detailed guide in `DATABASE_SETUP_GUIDE.md`

---

## ☑️ Part 1: Supabase (15 minutes)

### Create Project
- [ ] Go to https://supabase.com/dashboard
- [ ] Create new project: `co-teacher`
- [ ] Save database password
- [ ] Wait for project initialization (~2 mins)

### Get Credentials
- [ ] Copy Project URL: `https://[xxx].supabase.co`
- [ ] Copy anon public key: `eyJ...`

### Create Schema
- [ ] Open SQL Editor
- [ ] Copy/paste contents of `scripts/supabase_schema.sql`
- [ ] Run query (should create 9 tables)
- [ ] Verify tables in Table Editor

**Tables to verify:**
- conversations
- conversation_messages  
- daily_context
- alerts_sent
- pending_feedback
- response_cache
- budget_tracking
- events
- schedule_templates

---

## ☑️ Part 2: Pinecone (10 minutes)

### Create Index
- [ ] Go to https://app.pinecone.io/
- [ ] Create index with these **exact** settings:
  - Name: `co-teacher-memory`
  - Dimensions: `1536` ⚠️ Must be exactly 1536!
  - Metric: `cosine`
  - Cloud: AWS
  - Region: `us-east-1` (or closest to you)
- [ ] Wait for index creation (~1-2 mins)

### Get Credentials
- [ ] Go to API Keys
- [ ] Copy API key
- [ ] Note your environment/region

---

## ☑️ Part 3: Configure .env (5 minutes)

### Create .env file
```powershell
# In PowerShell
New-Item -Path .env -ItemType File -Force
```

### Add all credentials
Copy this template and fill in your values:

```env
# LLMod.ai (you should already have this)
LLMOD_API_KEY=___________________
LLMOD_BASE_URL=https://api.llmod.ai/v1
LLMOD_CHAT_MODEL=RPRTHPB-gpt-5-mini
LLMOD_EMBEDDING_MODEL=RPRTHPB-text-embedding-3-small

# Supabase
SUPABASE_URL=___________________
SUPABASE_KEY=___________________

# Pinecone
PINECONE_API_KEY=___________________
PINECONE_INDEX_NAME=co-teacher-memory
PINECONE_ENVIRONMENT=us-east-1

# Budget
BUDGET_LIMIT=13.00
BUDGET_WARNING_THRESHOLD=10.00
```

**Fill in the blanks:**
- [ ] LLMOD_API_KEY
- [ ] SUPABASE_URL  
- [ ] SUPABASE_KEY
- [ ] PINECONE_API_KEY
- [ ] PINECONE_ENVIRONMENT (if not us-east-1)

---

## ☑️ Part 4: Seed Databases (5 minutes)

### Quick Setup (Automated)
```powershell
# Run this script - it will guide you through everything
.\scripts\quick_setup.ps1
```

**OR Manual Steps:**

### Manual Seeding

1. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Seed Pinecone:**
   ```powershell
   python -m scripts.seed_pinecone
   ```
   
   Expected: ~5 students + ~30 teaching methods added
   
   Cost: ~$0.01-0.05

3. **Verify:**
   ```powershell
   python -c "from pinecone import Pinecone; from app.config import get_settings; s = get_settings(); pc = Pinecone(api_key=s.pinecone_api_key); idx = pc.Index(s.pinecone_index_name); print(idx.describe_index_stats())"
   ```

---

## ☑️ Part 5: Test Everything (5 minutes)

### Test Local Server
```powershell
# Start server
uvicorn app.main:app --reload
```

### Test in Browser
- [ ] Visit: http://localhost:8000
- [ ] Should see the Co-Teacher landing page
- [ ] Try query: "Tell me about Alex Johnson"
- [ ] Should get response with Alex's profile
- [ ] Click trace to see steps

### Test API Endpoints
```powershell
# Health check
curl http://localhost:8000/health

# Team info
curl http://localhost:8000/api/team_info

# Agent info  
curl http://localhost:8000/api/agent_info
```

---

## ☑️ Part 6: Render Deployment (10 minutes)

### Add Environment Variables in Render

Go to your Render service → Environment → Add each:

- [ ] LLMOD_API_KEY
- [ ] SUPABASE_URL
- [ ] SUPABASE_KEY
- [ ] PINECONE_API_KEY
- [ ] PINECONE_INDEX_NAME = `co-teacher-memory`
- [ ] PINECONE_ENVIRONMENT = `us-east-1` (or your region)
- [ ] BUDGET_LIMIT = `13.00`
- [ ] BUDGET_WARNING_THRESHOLD = `10.00`

### Deploy
- [ ] Manual Deploy → Deploy latest commit
- [ ] Wait ~5-10 minutes
- [ ] Verify health: `https://[your-app].onrender.com/health`
- [ ] Test API: `https://[your-app].onrender.com/api/team_info`

---

## 🎉 Done!

**Total Time:** ~45 minutes  
**Total Cost:** ~$0.01-0.10 (just for seeding embeddings)

### Final Verification

**Local:**
- [ ] ✓ Server runs without errors
- [ ] ✓ Frontend loads
- [ ] ✓ Can query student info
- [ ] ✓ Budget endpoint works: http://localhost:8000/api/execute/budget

**Deployed:**
- [ ] ✓ Health check returns 200
- [ ] ✓ All 4 required API endpoints work
- [ ] ✓ Frontend loads on Render URL
- [ ] ✓ Can query and get responses

---

## Troubleshooting

**Issue:** `.env` file not loading  
**Fix:** Make sure it's in project root: `c:\code\co_teacher\.env`

**Issue:** Pinecone dimension mismatch  
**Fix:** Index must be 1536 dimensions. Delete and recreate.

**Issue:** No students found after seeding  
**Fix:** Check `data/seed_students.json` exists and is valid JSON.

**Issue:** Supabase "Invalid API key"  
**Fix:** Use **anon public** key, not service_role key.

**Issue:** LLMod budget exceeded during seeding  
**Fix:** Temporarily increase BUDGET_LIMIT in .env to higher value.

---

## Need More Details?

See full guide: `DATABASE_SETUP_GUIDE.md`

## Getting Help

1. Check logs for specific error messages
2. Verify all credentials are correct (no typos!)
3. Make sure Pinecone index has correct dimensions (1536)
4. Ensure Supabase project is active (not paused)
