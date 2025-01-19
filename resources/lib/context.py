import xbmc
import xbmcgui
import xbmcaddon
from .metadata import ShowMetadata
from .database import ShowDatabase

class TimeInputDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.intro_start = None
        self.intro_duration = None
        self.outro_start = None
        self.result = None
        super().__init__(*args, **kwargs)
    
    def onInit(self):
        # Set up input fields
        self.intro_start_input = self.getControl(1001)
        self.intro_duration_input = self.getControl(1002)
        self.outro_start_input = self.getControl(1003)
        
        # Set up buttons
        self.ok_button = self.getControl(1005)
        self.cancel_button = self.getControl(1006)
    
    def onClick(self, controlId):
        if controlId == 1005:  # OK button
            try:
                self.intro_start = float(self.intro_start_input.getText())
                self.intro_duration = float(self.intro_duration_input.getText())
                self.outro_start = float(self.outro_start_input.getText()) if self.outro_start_input.getText() else None
                self.result = True
            except ValueError:
                xbmcgui.Dialog().ok('Error', 'Please enter valid numbers for times')
                return
            self.close()
        elif controlId == 1006:  # Cancel button
            self.result = False
            self.close()

def get_chapter_times():
    """Get times and chapter names from chapter selection"""
    try:
        # Get chapters from current playback
        player = xbmc.Player()
        if not player.isPlaying():
            return None
            
        chapter_count = int(xbmc.getInfoLabel('Player.ChapterCount'))
        if chapter_count <= 0:
            return None
            
        # Build chapter list
        chapters = []
        for i in range(1, chapter_count + 1):
            name = xbmc.getInfoLabel(f'Player.ChapterName({i})')
            time = player.getChapterTime(i)
            if time is not None:
                chapters.append({'name': name, 'time': time, 'index': i})
        
        if not chapters:
            return None
            
        # Let user select chapters
        dialog = xbmcgui.Dialog()
        
        # Intro chapter
        names = [f"{c['name']} ({c['time']}s)" for c in chapters]
        intro_start = dialog.select('Select Intro Chapter', names)
        if intro_start < 0:
            return None
            
        # Calculate intro duration using next chapter
        intro_duration = None
        if intro_start < len(chapters) - 1:
            intro_duration = chapters[intro_start + 1]['time'] - chapters[intro_start]['time']
            
        # Outro start (optional)
        outro_start = dialog.select('Select Outro Chapter (Optional)', names)
        if outro_start < 0:
            outro_start = None
            
        return {
            'intro_start_chapter': intro_start + 1,  # Convert to 1-based index
            'outro_start_chapter': outro_start + 1 if outro_start is not None else None,
            'intro_start_time': chapters[intro_start]['time'],
            'intro_duration_time': intro_duration,
            'outro_start_time': chapters[outro_start]['time'] if outro_start is not None else None,
            'source': 'chapters'
        }
    except Exception as e:
        xbmc.log(f'SkipIntro: Error getting chapter times: {str(e)}', xbmc.LOGERROR)
        return None

def get_user_times():
    """Show dialog to get user input for intro/outro times"""
    # First try chapters
    times = get_chapter_times()
    if times:
        return times
        
    # Fall back to manual input
    dialog = TimeInputDialog('time_input.xml', xbmcaddon.Addon().getAddonInfo('path'))
    dialog.doModal()
    if dialog.result:
        return {
            'intro_start_time': dialog.intro_start,
            'intro_duration_time': dialog.intro_duration,
            'outro_start_time': dialog.outro_start,
            'source': 'user_input'
        }
    return None

def save_user_times():
    """Save user-provided times for current show"""
    try:
        # Get current show info
        metadata = ShowMetadata()
        show_info = metadata.get_show_info()
        if not show_info:
            xbmcgui.Dialog().ok('Error', 'No show detected')
            return False
            
        # Get times from user
        times = get_user_times()
        if not times:
            return False
            
        # Save to database
        db = ShowDatabase(xbmcaddon.Addon().getSetting('database_path'))
        show_id = db.get_show(show_info['title'])
        if not show_id:
            return False
            
        success = db.save_episode_times(
            show_id,
            show_info['season'],
            show_info['episode'],
            times
        )
        
        if success:
            xbmcgui.Dialog().ok('Success', 'Times saved successfully')
        else:
            xbmcgui.Dialog().ok('Error', 'Failed to save times')
            
        return success
    except Exception as e:
        xbmc.log(f'SkipIntro: Error saving user times: {str(e)}', xbmc.LOGERROR)
        xbmcgui.Dialog().ok('Error', 'An error occurred while saving times')
        return False
