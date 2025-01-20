import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs
import os
from resources.lib.settings import Settings
from resources.lib.chapters import ChapterManager
from resources.lib.ui import PlayerUI
from resources.lib.show import ShowManager
from resources.lib.database import ShowDatabase
from resources.lib.metadata import ShowMetadata

addon = xbmcaddon.Addon()

def get_database():
    """Initialize and return database connection"""
    try:
        db_path = addon.getSetting('database_path')
        if not db_path:
            db_path = 'special://userdata/addon_data/plugin.video.skipintro/shows.db'
        
        # Ensure directory exists
        translated_path = xbmcvfs.translatePath(db_path)
        db_dir = os.path.dirname(translated_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        return ShowDatabase(translated_path)
    except Exception as e:
        xbmc.log('SkipIntro: Error initializing database: {}'.format(str(e)), xbmc.LOGERROR)
        return None

class SkipIntroPlayer(xbmc.Player):
    def __init__(self):
        super(SkipIntroPlayer, self).__init__()
        self.intro_start = None
        self.intro_duration = None
        self.intro_bookmark = None
        self.outro_bookmark = None
        self.bookmarks_checked = False
        self.default_skip_checked = False
        self.prompt_shown = False
        self.show_info = None
        self.db = get_database()
        self.metadata = ShowMetadata()
        self.ui = PlayerUI()
        
        # Initialize settings
        self.settings_manager = Settings()
        self.settings = self.settings_manager.settings
        
    def onPlayBackStopped(self):
        """Called when playback is stopped by user"""
        self.cleanup()
        
    def onPlayBackEnded(self):
        """Called when playback ends naturally"""
        self.cleanup()
        
    def onPlayBackStarted(self):
        """Called when Kodi starts playing a file"""
        xbmc.log('SkipIntro: Playback started', xbmc.LOGINFO)
        self.cleanup()  # Reset state for new playback
        
    def onAVStarted(self):
        """Called when Kodi has prepared audio/video for the file"""
        xbmc.log('SkipIntro: AV started', xbmc.LOGINFO)
        # Reset flags for new video
        self.bookmarks_checked = False
        self.prompt_shown = False
        self.default_skip_checked = False
        
        # Wait longer for video info and chapters to be available
        xbmc.sleep(5000)  # Initial 5 second wait
        if not self.isPlaying():
            return
            
        self.detect_show()
        
        # Additional wait for chapters with player state validation
        xbmc.sleep(3000)  # 3 more seconds
        if not self.isPlaying():
            return
            
        if self.show_info:
            # First check saved times
            self.check_saved_times()
            
            # If no saved times and chapters enabled, check chapters
            if not self.intro_bookmark and self.settings['use_chapters']:
                chapters = self.getChapters()
                if chapters:
                    xbmc.log(f'SkipIntro: Found {len(chapters)} chapters', xbmc.LOGINFO)
                self.check_for_intro_chapter()
            
            # If still no intro bookmark, use default skip
            if not self.intro_bookmark:
                self.check_for_default_skip()
            self.bookmarks_checked = True
            
            # If we have intro times, start checking
            if self.intro_start is not None and self.intro_bookmark is not None:
                xbmc.log(f'SkipIntro: Starting time monitoring for intro period {self.intro_start}-{self.intro_bookmark}', xbmc.LOGINFO)
                self.check_intro_time()

    def onPlayBackTime(self, time):
        """Called during playback with current time"""
        if not self.prompt_shown and self.intro_start is not None and self.intro_bookmark is not None:
            if time >= self.intro_start and time < self.intro_bookmark:
                xbmc.log(f'SkipIntro: In intro period at {time}, showing skip button', xbmc.LOGINFO)
                if self.ui.prompt_skip_intro(lambda: self.skip_to_intro_end()):
                    self.prompt_shown = True
                    xbmc.log('SkipIntro: Skip button shown successfully', xbmc.LOGINFO)

    def detect_show(self):
        """Detect current TV show and episode"""
        if not self.isPlaying():
            xbmc.log('SkipIntro: Not playing, skipping show detection', xbmc.LOGINFO)
            return
            
        playing_file = self.getPlayingFile()
        xbmc.log(f'SkipIntro: Detecting show for file: {playing_file}', xbmc.LOGINFO)
            
        self.show_info = self.metadata.get_show_info()
        if self.show_info:
            xbmc.log('SkipIntro: Detected show info:', xbmc.LOGINFO)
            xbmc.log(f'  Title: {self.show_info.get("title")}', xbmc.LOGINFO)
            xbmc.log(f'  Season: {self.show_info.get("season")}', xbmc.LOGINFO)
            xbmc.log(f'  Episode: {self.show_info.get("episode")}', xbmc.LOGINFO)
        else:
            xbmc.log('SkipIntro: Could not detect show info', xbmc.LOGINFO)

    def find_chapter_by_name(self, chapters, name):
        return ChapterManager.find_chapter_by_name(chapters, name)

    def check_saved_times(self):
        """Check database for saved intro/outro times"""
        if not self.db or not self.show_info:
            return

        try:
            show_id = self.db.get_show(self.show_info['title'])
            if not show_id:
                return

            def process_chapter_times(chapter_num, chapters, source_desc):
                """Process chapter times and set bookmarks"""
                try:
                    if chapter_num and 1 <= chapter_num <= len(chapters):
                        start_time = chapters[chapter_num - 1]['time']
                        if chapter_num < len(chapters):
                            end_time = chapters[chapter_num]['time']
                        else:
                            end_time = start_time + self.settings['skip_duration']
                        
                        self.intro_start = start_time
                        self.intro_bookmark = end_time
                        self.intro_duration = end_time - start_time
                        return True
                except Exception as e:
                    xbmc.log(f'SkipIntro: Error processing chapter times: {str(e)}', xbmc.LOGERROR)
                return False

            # First check show config for chapter settings
            config = self.db.get_show_config(show_id)
            if config and config['use_chapters']:
                chapters = self.getChapters()
                if chapters:
                    intro_chapter = config.get('intro_start_chapter')
                    outro_chapter = config.get('outro_start_chapter')
                    
                    if intro_chapter:
                        if process_chapter_times(intro_chapter, chapters, "show chapter config"):
                            if outro_chapter and 1 <= outro_chapter <= len(chapters):
                                self.outro_bookmark = chapters[outro_chapter - 1]['time']
                            return
            
            # If no show chapter config or chapters not available, check episode times
            times = self.db.get_episode_times(
                show_id, 
                self.show_info['season'],
                self.show_info['episode']
            )

            if times:
                xbmc.log('SkipIntro: Found saved times for show', xbmc.LOGINFO)
                if times.get('intro_start_chapter'):
                    xbmc.log('SkipIntro: Using chapter-based times', xbmc.LOGINFO)
                    chapters = self.getChapters()
                    if chapters:
                        intro_chapter = times.get('intro_start_chapter')
                        outro_chapter = times.get('outro_start_chapter')
                        xbmc.log(f'SkipIntro: Found chapters - intro: {intro_chapter}, outro: {outro_chapter}', xbmc.LOGINFO)
                        
                        if process_chapter_times(intro_chapter, chapters, "episode chapter times"):
                            if outro_chapter and 1 <= outro_chapter <= len(chapters):
                                self.outro_bookmark = chapters[outro_chapter - 1]['time']
                                xbmc.log(f'SkipIntro: Set outro bookmark to {self.outro_bookmark}', xbmc.LOGINFO)
                elif times.get('intro_start_time') is not None:
                    xbmc.log('SkipIntro: Using saved time-based markers', xbmc.LOGINFO)
                    # Use exact times for manual input
                    self.intro_start = times['intro_start_time']
                    self.intro_duration = times['intro_duration_time']
                    if self.intro_start is not None and self.intro_duration is not None:
                        self.intro_bookmark = self.intro_start + self.intro_duration
                        xbmc.log(f'SkipIntro: Calculated intro bookmark: {self.intro_bookmark}', xbmc.LOGINFO)
                    self.outro_bookmark = times['outro_start_time']
                
                xbmc.log('SkipIntro: Final times - intro_start: {}, duration: {}, outro_start: {}, bookmark: {}'.format(
                    self.intro_start, self.intro_duration, self.outro_bookmark, self.intro_bookmark), xbmc.LOGINFO)
        except Exception as e:
            xbmc.log('SkipIntro: Error checking saved times: {}'.format(str(e)), xbmc.LOGERROR)

    def check_for_intro_chapter(self):
        try:
            playing_file = self.getPlayingFile()
            if not playing_file:
                xbmc.log('SkipIntro: No file playing, skipping chapter check', xbmc.LOGINFO)
                return

            # Retrieve chapters
            xbmc.log('SkipIntro: Getting chapters for file', xbmc.LOGINFO)
            chapters = self.getChapters()
            if chapters:
                xbmc.log(f'SkipIntro: Found {len(chapters)} chapters:', xbmc.LOGINFO)
                for i, chapter in enumerate(chapters):
                    xbmc.log(f'  Chapter {i+1}: time={chapter.get("time")}, name={chapter.get("name", "Unnamed")}', xbmc.LOGINFO)
                
                intro_start = self.find_intro_chapter(chapters)
                if intro_start is not None:
                    xbmc.log(f'SkipIntro: Found potential intro start at {intro_start}', xbmc.LOGINFO)
                    intro_chapter_index = None
                    for i, chapter in enumerate(chapters):
                        if abs(chapter['time'] - intro_start) < 0.1:  # Compare with small tolerance
                            intro_chapter_index = i
                            xbmc.log(f'SkipIntro: Matched intro to chapter {i+1}', xbmc.LOGINFO)
                            break
                    
                    if intro_chapter_index is not None and intro_chapter_index + 1 < len(chapters):
                        self.intro_start = chapters[intro_chapter_index]['time']
                        self.intro_bookmark = chapters[intro_chapter_index + 1]['time']
                        self.intro_duration = self.intro_bookmark - self.intro_start
                        xbmc.log('SkipIntro: Set chapter-based intro times:', xbmc.LOGINFO)
                        xbmc.log(f'  Start: {self.intro_start}', xbmc.LOGINFO)
                        xbmc.log(f'  End: {self.intro_bookmark}', xbmc.LOGINFO)
                        xbmc.log(f'  Duration: {self.intro_duration}', xbmc.LOGINFO)
                        
                        if self.settings['save_times'] and self.show_info and self.db:
                            show_id = self.db.get_show(self.show_info['title'])
                            times = {
                                'intro_start_time': self.intro_start,
                                'intro_duration_time': self.intro_duration,
                                'intro_start_chapter': intro_chapter_index + 1,  # Convert to 1-based index
                                'outro_start_chapter': None,
                                'outro_start_time': None,
                                'source': 'chapters'
                            }
                            self.db.save_episode_times(
                                show_id,
                                self.show_info['season'],
                                self.show_info['episode'],
                                times
                            )
                else:
                    self.bookmarks_checked = True
            else:
                self.check_for_default_skip()
        except Exception as e:
            xbmc.log('SkipIntro: Error in check_for_intro_chapter: {}'.format(str(e)), xbmc.LOGERROR)
            self.bookmarks_checked = True

    def getChapters(self):
        chapter_manager = ChapterManager()
        return chapter_manager.get_chapters()

    def find_intro_chapter(self, chapters):
        chapter_manager = ChapterManager()
        return chapter_manager.find_intro_chapter(chapters)

    def check_for_default_skip(self):
        if self.default_skip_checked:
            xbmc.log('SkipIntro: Default skip already checked', xbmc.LOGINFO)
            return

        try:
            current_time = self.getTime()
            default_delay = self.settings['default_delay']
            skip_duration = self.settings['skip_duration']
            
            xbmc.log(f'SkipIntro: Checking default skip - current time: {current_time}, delay: {default_delay}', xbmc.LOGINFO)
            
            if current_time >= default_delay:
                self.intro_bookmark = current_time + skip_duration
                xbmc.log(f'SkipIntro: Using default skip - will skip to: {self.intro_bookmark}', xbmc.LOGINFO)
                self.prompt_skip_intro()
            else:
                xbmc.log('SkipIntro: Not yet at default skip delay', xbmc.LOGINFO)
        except Exception as e:
            xbmc.log('SkipIntro: Error in default skip check: {}'.format(str(e)), xbmc.LOGERROR)

        self.default_skip_checked = True

    def prompt_skip_intro(self):
        """Show skip intro button"""
        try:
            if self.ui.prompt_skip_intro(lambda: self.skip_to_intro_end()):
                # If we used default skip, save the time
                if self.settings['save_times'] and self.show_info and self.db and not self.bookmarks_checked:
                    show_id = self.db.get_show(self.show_info['title'])
                    times = {
                        'intro_start_time': self.settings['default_delay'],
                        'intro_duration_time': self.settings['skip_duration'],
                        'intro_start_chapter': None,
                        'outro_start_chapter': None,
                        'outro_start_time': None,
                        'source': 'default'
                    }
                    self.db.save_episode_times(
                        show_id,
                        self.show_info['season'],
                        self.show_info['episode'],
                        times
                    )
        except Exception as e:
            xbmc.log('SkipIntro: Error showing skip button: {}'.format(str(e)), xbmc.LOGERROR)

    def skip_to_intro_end(self):
        if self.intro_bookmark:
            try:
                current_time = self.getTime()
                xbmc.log(f'SkipIntro: Skipping from {current_time} to {self.intro_bookmark} seconds', xbmc.LOGINFO)
                self.seekTime(self.intro_bookmark)
                xbmc.log('SkipIntro: Skip completed', xbmc.LOGINFO)
            except Exception as e:
                xbmc.log('SkipIntro: Error skipping to intro end: {}'.format(str(e)), xbmc.LOGERROR)

    def check_intro_time(self):
        """Check if we need to show the skip intro prompt"""
        try:
            if not self.prompt_shown and self.intro_start is not None and self.intro_bookmark is not None:
                current_time = self.getTime()
                xbmc.log(f'SkipIntro: Time check - current: {current_time}, start: {self.intro_start}, end: {self.intro_bookmark}', xbmc.LOGINFO)
                
                if current_time >= self.intro_start and current_time < self.intro_bookmark:
                    xbmc.log('SkipIntro: In intro period, showing skip button', xbmc.LOGINFO)
                    if self.ui.prompt_skip_intro(lambda: self.skip_to_intro_end()):
                        self.prompt_shown = True
                        xbmc.log('SkipIntro: Skip button shown successfully', xbmc.LOGINFO)
        except Exception as e:
            xbmc.log('SkipIntro: Error checking intro time: {}'.format(str(e)), xbmc.LOGERROR)

    def cleanup(self):
        """Clean up resources"""
        self.ui.cleanup()
        self.intro_start = None
        self.intro_duration = None
        self.intro_bookmark = None
        self.outro_bookmark = None
        self.bookmarks_checked = False
        self.default_skip_checked = False
        self.prompt_shown = False
        self.show_info = None

def main():
    player = SkipIntroPlayer()
    monitor = xbmc.Monitor()

    try:
        while not monitor.abortRequested():
            if monitor.waitForAbort(1):  # Just keep service alive
                break
    finally:
        player.cleanup()
        xbmc.log('SkipIntro: Service stopped', xbmc.LOGINFO)

if __name__ == '__main__':
    main()
