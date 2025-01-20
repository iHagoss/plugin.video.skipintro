import xbmc
import json
import subprocess
from typing import List, Dict, Union

class ChapterManager:
    """Manages chapter detection for video files using FFmpeg."""
    
    def __init__(self):
        self._cached_chapters = {}
        # On macOS, ffmpeg is typically installed in /usr/local/bin
        self._ffmpeg_path = "/usr/local/bin/ffmpeg"
    
    def get_chapters(self) -> List[Dict[str, Union[str, int, float]]]:
        """Get chapter information using ffmpeg."""
        try:
            # Get current file using Kodi's JSON-RPC API
            result = xbmc.executeJSONRPC(json.dumps({
                "jsonrpc": "2.0",
                "method": "Player.GetItem",
                "params": {
                    "playerid": 1,
                    "properties": ["title", "file"]
                },
                "id": 1
            }))
            
            result = json.loads(result)
            if 'result' not in result or 'item' not in result['result']:
                return []
                
            current_file = result['result']['item'].get('file')
            if not current_file:
                return []
            
            # Return cached chapters if available
            if current_file in self._cached_chapters:
                return self._cached_chapters[current_file]
            
            # Get chapter metadata using ffmpeg
            cmd = [self._ffmpeg_path, "-i", current_file, "-f", "ffmetadata", "-"]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                metadata = result.stdout
                
                if result.returncode != 0:
                    xbmc.log(f"SkipIntro: FFmpeg error: {result.stderr}", xbmc.LOGERROR)
                    return []
                
                chapters = []
                current_chapter = {}
                chapter_number = 1
                
                # Parse metadata
                for line in metadata.splitlines():
                    if line.startswith("[CHAPTER]"):
                        if current_chapter and 'start' in current_chapter and 'end' in current_chapter:
                            chapters.append({
                                'name': current_chapter.get('title', f'Chapter {chapter_number}'),
                                'time': current_chapter['start'],
                                'end_time': current_chapter['end'],
                                'number': chapter_number
                            })
                            chapter_number += 1
                        current_chapter = {}
                    elif line.startswith("START="):
                        current_chapter["start"] = int(line.split("=")[1]) / 1e9  # Convert nanoseconds to seconds
                    elif line.startswith("END="):
                        current_chapter["end"] = int(line.split("=")[1]) / 1e9  # Convert nanoseconds to seconds
                    elif line.startswith("title="):
                        current_chapter["title"] = line.split("=")[1]
                
                # Add the last chapter
                if current_chapter and 'start' in current_chapter and 'end' in current_chapter:
                    chapters.append({
                        'name': current_chapter.get('title', f'Chapter {chapter_number}'),
                        'time': current_chapter['start'],
                        'end_time': current_chapter['end'],
                        'number': chapter_number
                    })
                
                if chapters:
                    xbmc.log(f"SkipIntro: Found {len(chapters)} chapters", xbmc.LOGINFO)
                        
                self._cached_chapters[current_file] = chapters
                return chapters
                
            except subprocess.TimeoutExpired:
                xbmc.log("SkipIntro: FFmpeg command timed out", xbmc.LOGERROR)
                return []
            except Exception as e:
                xbmc.log(f"SkipIntro: Error running ffmpeg: {str(e)}", xbmc.LOGERROR)
                return []

        except Exception as e:
            xbmc.log(f'SkipIntro: Error getting chapters: {str(e)}', xbmc.LOGERROR)
            return []

    @staticmethod
    def find_intro_chapter(chapters):
        """Find the intro chapter based on chapter number."""
        if not chapters:
            return None
            
        try:
            if len(chapters) >= 2:
                # Assume second chapter is intro (common in TV shows where Chapter 1 is "Previously on...")
                intro_start_time = chapters[1]['time']
                xbmc.log(f'SkipIntro: Using second chapter as intro at {intro_start_time} seconds', xbmc.LOGINFO)
                return intro_start_time
            return None
        except Exception as e:
            xbmc.log(f'SkipIntro: Error finding intro chapter: {str(e)}', xbmc.LOGERROR)
            return None
