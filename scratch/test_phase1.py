import asyncio
from pathlib import Path

from backend.phase1.hit_detector import run_hit_detection
from backend.agents.video_intelligence_agent import VideoIntelligenceAgent, analyze_video_intelligence
from pydantic import BaseModel

async def main():
    video_path = Path("samples/FO_Demo.mp4")
    print(f"--- Testing Video Intelligence (Agent 1) on {video_path.name} ---")
    data = analyze_video_intelligence(video_path)
    print(f"FPS: {data['fps']}, Res: {data['width']}x{data['height']}")
    print(f"Sampled frames: {[s['frame_index'] for s in data['geometry_samples']]}")
    
    print(f"\n--- Testing Hit Detection (Phase 1) on {video_path.name} ---")
    res = run_hit_detection(video_path)
    print(f"Total attempts: {res.total_swing_attempts}")
    print(f"Selected swing attempt: {res.selected_swing_index}")
    print(f"Hit confidence: {res.hit_confidence_score}")
    print(f"Address range: {res.address_frame_range}")
    print(f"Backswing start: {res.backswing_start_frame_index}")
    print(f"Impact: {res.impact_frame_index}")
    print(f"Follow through end: {res.follow_through_end_frame_index}")

if __name__ == "__main__":
    asyncio.run(main())
