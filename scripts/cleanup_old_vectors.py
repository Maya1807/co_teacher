"""
Cleanup script to remove old non-chunked vectors from Pinecone.

Removes vectors whose IDs don't contain '_chunk_' from the teaching-methods namespace.
"""

import asyncio
from app.memory.pinecone_client import get_pinecone_client


async def cleanup_old_vectors():
    """Remove non-chunked vectors from teaching-methods namespace."""
    pc = get_pinecone_client()

    print("Fetching current index stats...")
    stats = await pc.get_index_stats()
    print(f"Before cleanup: {stats}")

    namespace = "teaching-methods"

    # Pinecone doesn't have a "list all IDs" API directly,
    # but we can use the list() method if available, or query with a dummy vector

    # Get the index
    index = pc.index

    # List vectors in namespace (Pinecone serverless supports list())
    print(f"\nListing vectors in '{namespace}' namespace...")

    old_vector_ids = []

    # Use list() to get all vector IDs
    # This returns pages of vector IDs
    try:
        for ids_batch in index.list(namespace=namespace):
            for vector_id in ids_batch:
                # Check if this is an old non-chunked vector
                if "_chunk_" not in vector_id:
                    old_vector_ids.append(vector_id)
    except Exception as e:
        print(f"Error listing vectors: {e}")
        print("Trying alternative approach...")

        # Alternative: query with metadata filter or known prefixes
        # This is a fallback if list() doesn't work
        prefixes = ["eric_E", "iris_module_", "wiki_", "method_"]

        # We'll need to use a different approach - delete by prefix
        # Pinecone supports delete by ID prefix in some versions
        for prefix in prefixes:
            try:
                # Try to delete by prefix (only non-chunked)
                # This won't work directly, so we'll skip
                pass
            except:
                pass

        print("Could not list vectors. Manual cleanup may be needed.")
        return

    print(f"Found {len(old_vector_ids)} old non-chunked vectors to delete")

    if not old_vector_ids:
        print("No old vectors to clean up!")
        return

    # Show sample of what will be deleted
    print(f"\nSample IDs to delete (first 10):")
    for vid in old_vector_ids[:10]:
        print(f"  - {vid}")

    # Delete in batches of 100
    print(f"\nDeleting {len(old_vector_ids)} vectors...")
    batch_size = 100
    deleted = 0

    for i in range(0, len(old_vector_ids), batch_size):
        batch = old_vector_ids[i:i + batch_size]
        try:
            index.delete(ids=batch, namespace=namespace)
            deleted += len(batch)
            print(f"  Deleted {deleted}/{len(old_vector_ids)}...")
        except Exception as e:
            print(f"  Error deleting batch: {e}")

    print(f"\nDeleted {deleted} old vectors")

    # Verify
    print("\nFetching updated stats...")
    stats = await pc.get_index_stats()
    print(f"After cleanup: {stats}")


if __name__ == "__main__":
    asyncio.run(cleanup_old_vectors())
