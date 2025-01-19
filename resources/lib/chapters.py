import xbmc

class ChapterManager:
    def __init__(self):
        self._cached_chapters = None
        self._last_file = None

    @staticmethod
    def _parse_time(time_str):
        """Parse HH:MM:SS time string to seconds"""
        try:
            if time_str and ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 3:
                    hours, minutes, seconds = map(int, parts)
                    return hours * 3600 + minutes * 60 + seconds
        except (ValueError, IndexError) as e:
            xbmc.log(f'SkipIntro: Error parsing time {time_str}: {str(e)}', xbmc.LOGWARNING)
        return None

    def get_chapters(self):
        """Get chapter information using multiple methods with caching"""
        try:
            player = xbmc.Player()
            if not player.isPlaying():
                return []

            current_file = player.getPlayingFile()
            if self._cached_chapters and current_file == self._last_file:
                xbmc.log('SkipIntro: Using cached chapter info', xbmc.LOGDEBUG)
                return self._cached_chapters

            chapters = []
            self._last_file = current_file
            
            # Try different methods to get chapter count with multiple retries
            max_retries = 5
            retry_delay = 2000  # 2 seconds
            
            for attempt in range(max_retries):
                # Method 1: VideoPlayer.ChapterCount
                chapter_count_str = xbmc.getInfoLabel('VideoPlayer.ChapterCount')
                xbmc.log(f'SkipIntro: Attempt {attempt + 1}/{max_retries} - ChapterCount: "{chapter_count_str}"', xbmc.LOGINFO)
                
                # Method 2: Check individual chapters until we find none
                if chapter_count_str == 'VideoPlayer.ChapterCount' or not chapter_count_str:
                    xbmc.log(f'SkipIntro: Trying manual chapter detection', xbmc.LOGINFO)
                    for i in range(1, 20):  # Check up to 20 chapters
                        name = xbmc.getInfoLabel(f'VideoPlayer.Chapter({i})')
                        if name and name != f'VideoPlayer.Chapter({i})':
                            chapter_count_str = str(i)
                            xbmc.log(f'SkipIntro: Found chapter {i}: {name}', xbmc.LOGINFO)
                            break
                
                if chapter_count_str and chapter_count_str != 'VideoPlayer.ChapterCount':
                    xbmc.log(f'SkipIntro: Valid chapter count found: {chapter_count_str}', xbmc.LOGINFO)
                    break
                    
                xbmc.log(f'SkipIntro: No valid chapter count yet, waiting {retry_delay/1000}s...', xbmc.LOGINFO)
                xbmc.sleep(retry_delay)
            
            try:
                if chapter_count_str and chapter_count_str != 'VideoPlayer.ChapterCount':
                    chapter_count = int(chapter_count_str)
                    xbmc.log(f'SkipIntro: Valid chapter count: {chapter_count}', xbmc.LOGINFO)
                else:
                    xbmc.log('SkipIntro: No valid chapter count available', xbmc.LOGWARNING)
                    chapter_count = 0
            except (ValueError, TypeError) as e:
                xbmc.log(f'SkipIntro: Invalid chapter count format: {str(e)}', xbmc.LOGWARNING)
                chapter_count = 0
                
            if chapter_count <= 0:
                xbmc.log('SkipIntro: No chapters found', xbmc.LOGWARNING)
                return []
                
            for i in range(1, chapter_count + 1):
                try:
                    # Get chapter name and time from InfoLabels
                    chapter_name = xbmc.getInfoLabel(f'VideoPlayer.ChapterName({i})')
                    time_str = xbmc.getInfoLabel(f'VideoPlayer.ChapterTime({i})')
                    method_used = 'InfoLabel'
                    
                    xbmc.log(f'SkipIntro: Chapter {i} InfoLabel data:', xbmc.LOGINFO)
                    xbmc.log(f'SkipIntro: - ChapterName: "{chapter_name}"', xbmc.LOGINFO)
                    xbmc.log(f'SkipIntro: - ChapterTime: "{time_str}"', xbmc.LOGINFO)
                    
                    # Fallback to player method if InfoLabel fails
                    if not time_str:
                        try:
                            xbmc.log(f'SkipIntro: Attempting Player API fallback for chapter {i}', xbmc.LOGINFO)
                            player.seekChapter(i)
                            time_str = xbmc.getInfoLabel('VideoPlayer.Time')
                            method_used = 'Player API'
                            xbmc.log(f'SkipIntro: Player API fallback got time: "{time_str}"', xbmc.LOGINFO)
                        except Exception as e:
                            xbmc.log(f'SkipIntro: Player API fallback failed for chapter {i}:', xbmc.LOGWARNING)
                            xbmc.log(f'SkipIntro: Exception details: {str(e)}', xbmc.LOGWARNING)
                            xbmc.log(f'SkipIntro: Exception type: {type(e).__name__}', xbmc.LOGWARNING)
                            continue
                            
                    if not chapter_name or chapter_name.isspace():
                        chapter_name = f'Chapter {i}'
                        
                    chapter_time = self._parse_time(time_str)
                    if chapter_time is not None:
                        chapters.append({
                            'name': chapter_name,
                            'time': chapter_time,
                            'number': i
                        })
                        xbmc.log(f'SkipIntro: Added chapter {i} ({method_used}): {chapter_name} at {chapter_time}s', 
                                xbmc.LOGINFO)
                except Exception as e:
                    xbmc.log(f'SkipIntro: Error processing chapter {i}: {str(e)}', xbmc.LOGWARNING)
                    continue
            
            self._cached_chapters = chapters
            return chapters
        except Exception as e:
            xbmc.log(f'SkipIntro: Error getting chapters: {str(e)}', xbmc.LOGERROR)
            return []

    @staticmethod
    def find_intro_chapter(chapters):
        xbmc.log('SkipIntro: Searching for intro chapter', xbmc.LOGDEBUG)
        try:
            # Check if chapters are using default numbering (Chapter 1, Chapter 2, etc.)
            using_default_numbers = all(ch['name'].startswith('Chapter ') and ch['name'][8:].isdigit() for ch in chapters)
            
            if using_default_numbers and len(chapters) >= 2:
                # When using default chapter numbers, assume second chapter is intro
                # This is common in TV shows where Chapter 1 is "Previously on..."
                intro_start_time = chapters[1]['time']
                xbmc.log('SkipIntro: Using second chapter as intro at {} seconds'.format(
                    intro_start_time), xbmc.LOGINFO)
                return intro_start_time
            else:
                # Try to find explicitly marked intro chapter
                for i, chapter in enumerate(chapters):
                    xbmc.log('SkipIntro: Checking chapter: {} at {} seconds'.format(
                        chapter['name'], chapter['time']), xbmc.LOGDEBUG)
                    if 'intro' in chapter['name'].lower():
                        xbmc.log('SkipIntro: Intro chapter found at {} seconds'.format(
                            chapter['time']), xbmc.LOGINFO)
                        return chapter['time']
                xbmc.log('SkipIntro: No intro chapter found', xbmc.LOGINFO)
                return None
        except Exception as e:
            xbmc.log('SkipIntro: Error finding intro chapter: {}'.format(str(e)), xbmc.LOGERROR)
            return None

    @staticmethod
    def find_chapter_by_name(chapters, name):
        """Find chapter time by name"""
        if not name:
            return None
        for chapter in chapters:
            if chapter['name'].lower() == name.lower():
                return chapter['time']
        return None
