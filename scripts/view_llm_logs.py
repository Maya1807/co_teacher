"""
View LLM call logs from Supabase.

Shows budget tracking (detailed LLM calls) and response cache (what was cached).
"""
import asyncio
from datetime import datetime
from app.config import get_settings
from app.memory.supabase_client import SupabaseClient


async def view_llm_logs():
    """Display recent LLM calls and budget info."""
    client = SupabaseClient()
    settings = get_settings()
    
    print("\n" + "="*80)
    print("LLM CALL LOG - Budget Tracking")
    print("="*80)
    
    try:
        # Get all budget tracking entries
        result = client.client.table("budget_tracking").select(
            "id,model,prompt_tokens,completion_tokens,cost,agent_type,created_at"
        ).order("created_at", desc=True).limit(20).execute()
        
        if result.data:
            print(f"\nTotal entries: {len(result.data)}\n")
            print(f"{'Timestamp':<25} {'Model':<20} {'P-Tokens':<10} {'C-Tokens':<10} {'Cost':<8} {'Agent':<15}")
            print("-" * 100)
            
            total_cost = 0
            for row in result.data:
                timestamp = row.get("created_at", "N/A")
                if timestamp:
                    timestamp = timestamp[:19]  # YYYY-MM-DD HH:MM:SS
                model = row.get("model", "unknown")[:19]
                p_tokens = row.get("prompt_tokens", 0)
                c_tokens = row.get("completion_tokens", 0)
                cost = row.get("cost", 0)
                agent = row.get("agent_type", "unknown")[:14]
                
                print(f"{timestamp:<25} {model:<20} {p_tokens:<10} {c_tokens:<10} ${cost:<7.4f} {agent:<15}")
                total_cost += cost
            
            print("-" * 100)
            print(f"Total Cost: ${total_cost:.4f}")
        else:
            print("No budget tracking entries found. No LLM calls have been logged yet.")
    
    except Exception as e:
        print(f"Error fetching budget tracking: {e}")
    
    # Show response cache info
    print("\n" + "="*80)
    print("RESPONSE CACHE - Cached Responses")
    print("="*80)
    
    try:
        result = client.client.table("response_cache").select(
            "cache_key,agent_type,hit_count,created_at,expires_at"
        ).order("created_at", desc=True).limit(10).execute()
        
        if result.data:
            print(f"\nCached responses: {len(result.data)}\n")
            print(f"{'Agent':<15} {'Hits':<6} {'Created':<19} {'Expires':<19}")
            print("-" * 60)
            
            for row in result.data:
                agent = row.get("agent_type", "unknown")[:14]
                hits = row.get("hit_count", 0)
                created = row.get("created_at", "")[:19] if row.get("created_at") else "N/A"
                expires = row.get("expires_at", "")[:19] if row.get("expires_at") else "N/A"
                
                print(f"{agent:<15} {hits:<6} {created:<19} {expires:<19}")
        else:
            print("No cached responses found.")
    
    except Exception as e:
        print(f"Error fetching response cache: {e}")
    
    # Show total budget spent
    print("\n" + "="*80)
    print("BUDGET SUMMARY")
    print("="*80)
    
    try:
        total = await client.get_total_spent()
        print(f"\nTotal spent: ${total:.4f}")
        print(f"Budget limit: ${settings.budget_limit:.2f}")
        print(f"Remaining: ${settings.budget_limit - total:.4f}")
        
        if total > settings.budget_warning_threshold:
            print(f"⚠️  WARNING: Spent over ${settings.budget_warning_threshold:.2f}")
    
    except Exception as e:
        print(f"Error fetching budget summary: {e}")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(view_llm_logs())
