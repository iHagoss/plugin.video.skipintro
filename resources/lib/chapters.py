import xbmc

class ChapterManager:
    @staticmethod
    def get_chapters():
        """Get chapter information using SeekChapter"""
        try:
            # Get total chapters
            chapter_count = int(xbmc.getInfoLabel('VideoPlayer.ChapterCount'))
            xbmc.log(f'SkipIntro: Total chapters found: {chapter_count}', xbmc.LOGDEBUG)
            
            if chapter_count <= 0:
                xbmc.log('SkipIntro: No chapters found', xbmc.LOGWARNING)
                return []
                
            chapters = []
            for i in range(1, chapter_count + 1):
                # Get chapter name and time
                chapter_name = xbmc.getInfoLabel(f'VideoPlayer.ChapterName({i})')
                if not chapter_name or chapter_name.isspace():
                    chapter_name = f'Chapter {i}'
                    
                # Get chapter time from ChapterTime property
                time_str = xbmc.getInfoLabel(f'VideoPlayer.ChapterTime({i})')
                if time_str and ':' in time_str:
                    # Parse time string (format: HH:MM:SS)
                    parts = time_str.split(':')
                    if len(parts) == 3:
                        hours, minutes, seconds = map(int, parts)
                        chapter_time = hours * 3600 + minutes * 60 + seconds
                    else:
                        xbmc.log(f'SkipIntro: Invalid time format for chapter {i}: {time_str}', xbmc.LOGWARNING)
                        continue
                else:
                    xbmc.log(f'SkipIntro: No time available for chapter {i}', xbmc.LOGWARNING)
                    continue
                chapters.append({
                    'name': chapter_name,
                    'time': chapter_time
                })
                xbmc.log(f'SkipIntro: Added chapter {i}: {chapter_name} at {chapter_time}s', 
                        xbmc.LOGINFO)
            
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
