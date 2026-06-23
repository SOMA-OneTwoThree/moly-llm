def create_mem0_client(
    db_connection_string: str,
    openai_api_key: str,
    memory_llm_model: str,
    embedder_model: str,
):
    from mem0 import AsyncMemory

    return AsyncMemory.from_config(
        {
            "vector_store": {
                "provider": "supabase",
                "config": {
                    "connection_string": db_connection_string,
                    "collection_name": "memories",
                    "index_method": "hnsw",
                    "index_measure": "cosine_distance",
                },
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "api_key": openai_api_key,
                    "model": memory_llm_model,
                    "temperature": 0.1,
                },
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "api_key": openai_api_key,
                    "model": embedder_model,
                },
            },
        }
    )
