from chronos_engine.core.interfaces import BasePromptOrchestrator
from chronos_engine.core.models import PromptContext, RetrievedContext, UserInput


class PromptOrchestrator(BasePromptOrchestrator):
    async def orchestrate_prompt(
        self, user_input: UserInput, retrieved_context: RetrievedContext
    ) -> PromptContext:
        # Format System Prompt
        system_prompt = (
            "You are ChronOS, the central personal intelligence layer for OpenTime.\n"
            "You sit between the user's raw data and language models.\n"
            "Your objective is to respond with high contextual awareness, personal alignment, "
            "and deep continuity across the user's life timeline, evolving identity, and behavioral patterns.\n"
            "NEVER treat the user input as a standalone query; ground every response in the user's stored memories and evolving identity."
        )

        # Format Memories Section
        memories_str = "\n".join(
            [f"- [{m.timestamp.strftime('%Y-%m-%d')}] (Relevance High) {m.content}" for m in retrieved_context.relevant_memories]
        ) if retrieved_context.relevant_memories else "No prior closely related memories."

        # Format Timeline Section
        timeline_str = "\n".join(
            [f"- [{e.timestamp.strftime('%Y-%m-%d')}] [{e.life_phase}] {e.title}: {e.description}" for e in retrieved_context.timeline_events]
        ) if retrieved_context.timeline_events else "Timeline initialized."

        # Format Identity Section
        identity = retrieved_context.identity_summary
        identity_str = (
            f"User Interests: {', '.join(identity.get('interests', []))}\n"
            f"Active Goals: {', '.join(identity.get('goals', []))}\n"
            f"Core Values: {', '.join(identity.get('values', []))}\n"
            f"Communication Style: {identity.get('communication_style', 'Direct & Thoughtful')}\n"
            f"Emotional Tendencies: {identity.get('emotional_tendencies', {})}"
        )

        # Format Patterns Section
        patterns_str = "\n".join(
            [f"- [{p.category.value.upper()}] {p.title}: {p.description} (Confidence: {p.confidence_score*100:.0f}%)" for p in retrieved_context.patterns]
        ) if retrieved_context.patterns else "No active behavioral patterns detected yet."

        # Format Changes & Goals Section
        recent_str = "\n".join([f"- {c}" for c in retrieved_context.recent_changes])

        user_prompt = f"""=== CHRONOS ENGINE CONTEXT ENRICHMENT ===

[CURRENT USER INPUT ({user_input.input_type.value.upper()})]
"{user_input.content}"

[USER EVOLVING IDENTITY PROFILE]
{identity_str}

[CURRENT LIFE PHASE]
{retrieved_context.life_phase}

[RELEVANT MEMORIES & HISTORICAL CONTEXT]
{memories_str}

[TIMELINE HIGHLIGHTS]
{timeline_str}

[DETECTED BEHAVIORAL PATTERNS & HABITS]
{patterns_str}

[RECENT PERSONAL EVOLUTION & GOALS]
{recent_str}

=== INSTRUCTION TO UNDERLYING LLM ===
Respond directly to the user's current input using the enriched context above. Seamlessly integrate awareness of their goals, values, and past experiences. Keep the tone aligned with their preferred communication style."""

        return PromptContext(
            current_input=user_input,
            retrieved_context=retrieved_context,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
