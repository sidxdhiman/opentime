import uuid
from typing import List
from chronos_engine.core.interfaces import BaseEmbeddingProvider, BaseMemorySystem, BaseStorageAdapter
from chronos_engine.core.models import MemoryItem, MemoryType, UserInput


class MemorySystem(BaseMemorySystem):
    def __init__(self, storage: BaseStorageAdapter, embedding_provider: BaseEmbeddingProvider):
        self.storage = storage
        self.embedding_provider = embedding_provider

    async def add_interaction(self, input_item: UserInput) -> MemoryItem:
        embedding = await self.embedding_provider.get_embedding(input_item.content)
        memory_id = f"mem_{uuid.uuid4().hex[:12]}"

        # Calculate semantic connections to prior memories for memory linking graph
        existing_memories = await self.storage.get_memories_by_user(input_item.user_id, limit=30)
        linked_ids = []
        for prev_mem in existing_memories:
            if prev_mem.embedding:
                sim = self.embedding_provider.similarity(embedding, prev_mem.embedding)
                if sim > 0.45:  # threshold for linking
                    linked_ids.append(prev_mem.id)

        # Extract tags
        words = set(input_item.content.lower().split())
        key_tags = [w for w in words if len(w) > 4][:5]

        memory = MemoryItem(
            id=memory_id,
            user_id=input_item.user_id,
            content=input_item.content,
            memory_type=MemoryType.LONG_TERM,
            embedding=embedding,
            timestamp=input_item.timestamp,
            importance_score=min(1.0, 0.4 + (len(input_item.content) / 200.0)),
            linked_memory_ids=linked_ids,
            tags=key_tags,
            metadata={
                "input_type": input_item.input_type.value,
                "media_url": input_item.media_url,
                "file_name": input_item.file_name,
                "media_metadata": input_item.media_metadata,
            },
        )

        return await self.storage.save_memory(memory)

    async def search_semantic_memories(
        self, user_id: str, query: str, top_k: int = 5
    ) -> List[MemoryItem]:
        query_embedding = await self.embedding_provider.get_embedding(query)
        all_memories = await self.storage.get_memories_by_user(user_id, limit=200)

        scored = []
        for mem in all_memories:
            if mem.embedding:
                sim = self.embedding_provider.similarity(query_embedding, mem.embedding)
                scored.append((sim, mem))
            else:
                scored.append((0.0, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [mem for _, mem in scored[:top_k]]

    async def get_short_term_context(self, user_id: str, limit: int = 5) -> List[MemoryItem]:
        all_memories = await self.storage.get_memories_by_user(user_id, limit=limit)
        return sorted(all_memories, key=lambda m: m.timestamp, reverse=True)
