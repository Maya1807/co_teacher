# Quick Setup Script - Run after configuring .env file

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Co-Teacher Database Setup Quick Start" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Step 1: Check if .env file exists
Write-Host "Step 1: Checking .env file..." -ForegroundColor Yellow
if (Test-Path .env) {
    Write-Host "  ✓ .env file found" -ForegroundColor Green
} else {
    Write-Host "  ✗ .env file not found!" -ForegroundColor Red
    Write-Host "  → Create .env file and add your credentials" -ForegroundColor Yellow
    Write-Host "  → See DATABASE_SETUP_GUIDE.md Part 3 for template`n" -ForegroundColor Yellow
    exit
}

# Step 2: Check required data files
Write-Host "`nStep 2: Checking seed data files..." -ForegroundColor Yellow
$dataFiles = @(
    "data\seed_students.json",
    "data\teaching_methods.json"
)

$allFilesExist = $true
foreach ($file in $dataFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file found" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file missing!" -ForegroundColor Red
        $allFilesExist = $false
    }
}

if (-not $allFilesExist) {
    Write-Host "`n  → Some data files are missing. Cannot proceed.`n" -ForegroundColor Red
    exit
}

# Step 3: Test database connections
Write-Host "`nStep 3: Testing database connections..." -ForegroundColor Yellow
Write-Host "  (This will verify your .env credentials)`n" -ForegroundColor Gray

$testScript = @"
import asyncio
import os
from app.config import get_settings

async def quick_test():
    settings = get_settings()
    
    # Check credentials
    checks = {
        'LLMOD_API_KEY': bool(settings.llmod_api_key),
        'SUPABASE_URL': bool(settings.supabase_url),
        'SUPABASE_KEY': bool(settings.supabase_key),
        'PINECONE_API_KEY': bool(settings.pinecone_api_key),
        'PINECONE_INDEX': bool(settings.pinecone_index_name)
    }
    
    for key, value in checks.items():
        status = '✓' if value else '✗'
        print(f'  {status} {key}: {"OK" if value else "MISSING"}')
    
    if not all(checks.values()):
        print('\n  → Some credentials are missing in .env file')
        return False
    
    # Try connecting
    print('\n  Testing actual connections...')
    try:
        from app.memory.memory_manager import get_memory_manager
        memory = get_memory_manager()
        print('  ✓ Memory manager initialized')
        
        # Test Supabase
        try:
            convo_id = await memory.supabase.create_conversation('setup-test', 'setup-user')
            print(f'  ✓ Supabase: Connected (test conversation created)')
        except Exception as e:
            print(f'  ✗ Supabase: {str(e)[:60]}...')
            return False
        
        # Test Pinecone
        try:
            stats = await memory.pinecone.get_index_stats()
            print(f'  ✓ Pinecone: Connected (index ready)')
        except Exception as e:
            print(f'  ⚠ Pinecone: {str(e)[:60]}... (will work after seeding)')
        
        return True
        
    except Exception as e:
        print(f'  ✗ Connection error: {str(e)}')
        return False

if __name__ == '__main__':
    result = asyncio.run(quick_test())
    if result:
        print('\n  ✓ All credentials configured correctly!')
    else:
        print('\n  → Fix the errors above before proceeding')
"@

$testScript | Out-File -FilePath "temp_test_connections.py" -Encoding UTF8
python temp_test_connections.py
$connectionTestResult = $LASTEXITCODE
Remove-Item "temp_test_connections.py" -ErrorAction SilentlyContinue

if ($connectionTestResult -ne 0) {
    Write-Host "`n  → Fix connection errors before seeding databases`n" -ForegroundColor Red
    exit
}

# Step 4: Seed Pinecone
Write-Host "`nStep 4: Seed Pinecone with student profiles and teaching methods..." -ForegroundColor Yellow
Write-Host "  (This will take 2-5 minutes and cost ~`$0.01-0.05)`n" -ForegroundColor Gray

$response = Read-Host "  Proceed with seeding Pinecone? (y/n)"
if ($response -eq 'y' -or $response -eq 'Y') {
    Write-Host "`n  Starting Pinecone seeding...`n" -ForegroundColor Cyan
    python -m scripts.seed_pinecone
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n  ✓ Pinecone seeding complete!" -ForegroundColor Green
    } else {
        Write-Host "`n  ✗ Pinecone seeding failed. Check errors above." -ForegroundColor Red
        exit
    }
} else {
    Write-Host "  → Skipped Pinecone seeding" -ForegroundColor Yellow
}

# Step 5: Verify setup
Write-Host "`nStep 5: Verifying database setup..." -ForegroundColor Yellow

$verifyScript = @"
import asyncio
from pinecone import Pinecone
from app.config import get_settings

async def verify():
    settings = get_settings()
    
    # Check Pinecone stats
    pc = Pinecone(api_key=settings.pinecone_api_key)
    index = pc.Index(settings.pinecone_index_name)
    stats = index.describe_index_stats()
    
    print('\n  Pinecone Index Stats:')
    print(f'    Total vectors: {stats.get("total_vector_count", 0)}')
    
    namespaces = stats.get('namespaces', {})
    for ns, ns_stats in namespaces.items():
        print(f'    - {ns}: {ns_stats.get("vector_count", 0)} vectors')
    
    if stats.get('total_vector_count', 0) > 0:
        print('\n  ✓ Pinecone has data!')
    else:
        print('\n  ⚠ Pinecone is empty (run seeding script)')

if __name__ == '__main__':
    asyncio.run(verify())
"@

$verifyScript | Out-File -FilePath "temp_verify.py" -Encoding UTF8
python temp_verify.py
Remove-Item "temp_verify.py" -ErrorAction SilentlyContinue

# Final summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Test locally: uvicorn app.main:app --reload" -ForegroundColor White
Write-Host "  2. Visit: http://localhost:8000" -ForegroundColor White
Write-Host "  3. Try asking: 'Tell me about Alex Johnson'" -ForegroundColor White
Write-Host "  4. Deploy to Render with your GitHub repo`n" -ForegroundColor White

Write-Host "For detailed instructions, see:" -ForegroundColor Yellow
Write-Host "  → DATABASE_SETUP_GUIDE.md`n" -ForegroundColor White
