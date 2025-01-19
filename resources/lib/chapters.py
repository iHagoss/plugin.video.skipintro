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
            
            # Try getting chapter count from both methods
            chapter_count_str = xbmc.getInfoLabel('VideoPlayer.ChapterCount')
            player_chapter_count = player.getTotalChapters()
            
            xbmc.log(f'SkipIntro: Chapter counts - InfoLabel: {chapter_count_str}, Player API: {player_chapter_count}', xbmc.LOGINFO)
            
            # Use the larger of the two counts
            try:
                info_chapter_count = int(chapter_count_str)
                chapter_count = max(info_chapter_count, player_chapter_count)
            except (ValueError, TypeError):
                chapter_count = player_chapter_count
                xbmc.log('SkipIntro: Using Player API chapter count', xbmc.LOGINFO)
                
            if chapter_count <= 0:
                xbmc.log('SkipIntro: No chapters found', xbmc.LOGWARNING)
                return []
                
            for i in range(1, chapter_count + 1):
                try:
                    # Get chapter name and time from InfoLabels
                    chapter_name = xbmc.getInfoLabel(f'VideoPlayer.ChapterName({i})')
                    time_str = xbmc.getInfoLabel(f'VideoPlayer.ChapterTime({i})')
                    method_used = 'InfoLabel'
                    
                    # Fallback to player method if InfoLabel fails
                    if not time_str:
                        try:
                            player.seekChapter(i)
                            time_str = xbmc.getInfoLabel('VideoPlayer.Time')
                            method_used = 'Player API'
                        except Exception as e:
                            xbmc.log(f'SkipIntro: Player API fallback failed: {str(e)}', xbmc.LOGWARNING)
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
