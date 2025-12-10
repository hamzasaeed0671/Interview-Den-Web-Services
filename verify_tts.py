import edge_tts
import asyncio

async def main():
    print("Testing EdgeTTS...")
    text = "Hello, this is a test of the Microsoft Edge Text to Speech service."
    voice = "en-US-AriaNeural"
    output_file = "test_audio.mp3"
    
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
        print(f"Success! Saved to {output_file}")
    except Exception as e:
        print(f"Failed: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
