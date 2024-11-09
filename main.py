# TODO: To bring down the costs we can use neets for the tts and we can use groq for speed to lower latency
import asyncio
from dotenv import load_dotenv
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.voice_assistant import VoiceAssistant
from livekit.plugins import openai, silero, deepgram, cartesia
from api import CalendarAssistant
from datetime import datetime, timezone

load_dotenv()

async def entrypoint(ctx: JobContext):
    current_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    #TODO: Adjust this prompt
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=f"""
            You are a voice assistant specializing in calendar management. Current UTC time is: {current_utc}

            Your core responsibilities:
            1. Help users find available calendar slots
            2. Gather required information:
               - Date (YYYY-MM-DD format)
               - Timezone (e.g., 'Europe/Helsinki', 'America/New_York')

            When interacting:
            - Use natural, conversational voice
            - Keep responses concise and clear
            - Avoid unpronounceable punctuation
            - If user doesn't specify timezone, ask for their location to determine it
            - If date format is unclear, politely ask for clarification
            - Convert informal date references (e.g., "tomorrow", "next week") to YYYY-MM-DD

            When checking availability:
            - Use the get_available_slots tool with collected date and timezone
            - Wait for API response before suggesting times
            - If no slots available, suggest checking different dates
            - Present times in user's local timezone

            Remember: You need both date and timezone before checking availability.
            Example: "I can help you find available slots. Could you tell me what date you're interested in, and what timezone you're in?"
        """
    )
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    fnc_ctx = CalendarAssistant()  
    
    assitant = VoiceAssistant(
        vad=silero.VAD.load(),
        stt=deepgram.STT(), 
        llm=openai.LLM(),
        tts=cartesia.TTS(), #TODO: Better voice that can handle dates and times
        chat_ctx=initial_ctx,
        fnc_ctx=fnc_ctx,
    )
    assitant.start(ctx.room)

    await asyncio.sleep(1)
    await assitant.say("Hey, how can I help you today!", allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))