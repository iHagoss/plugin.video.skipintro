import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs
import json
import os
from resources.lib.database import ShowDatabase
from resources.lib.metadata import ShowMetadata

def get_selected_item_info():
    """Get info about the selected item in Kodi"""
    try:
        xbmc.log('SkipIntro: Getting selected item info', xbmc.LOGINFO)
        
        # Get info from selected list item
        showtitle = xbmc.getInfoLabel('ListItem.TVShowTitle')
        season = xbmc.getInfoLabel('ListItem.Season')
        episode = xbmc.getInfoLabel('ListItem.Episode')
        filepath = xbmc.getInfoLabel('ListItem.FileNameAndPath')
        
        if not all([showtitle, season, episode, filepath]):
            xbmc.log('SkipIntro: Missing required item info', xbmc.LOGWARNING)
            return None
            
        item = {
            'showtitle': showtitle,
            'season': int(season),
            'episode': int(episode),
            'file': filepath
        }
        
        xbmc.log(f'SkipIntro: Found item - Show: {showtitle}, S{season}E{episode}', xbmc.LOGINFO)
        return item
    except Exception as e:
        xbmc.log(f'SkipIntro: Error getting item info: {str(e)}', xbmc.LOGERROR)
    return None

def get_show_settings(show_id, db):
    """Get or create show settings"""
    config = db.get_show_config(show_id)
    if not config:
        config = {
            'use_defaults': True,
            'use_chapters': False,
            'intro_duration': 60
        }
        db.save_show_config(show_id, config)
    return config

def get_manual_times(show_id, db):
    """Get times manually from user input"""
    try:
        dialog = xbmcgui.Dialog()
        addon = xbmcaddon.Addon()
        
        # Get show config
        config = get_show_settings(show_id, db)
        
        # Ask if using chapters
        if addon.getSettingBool('use_chapters'):
            use_chapters = dialog.yesno('Skip Intro', 'Use chapter numbers for skipping?\n(Will use next chapter as end point)')
            if use_chapters:
                intro_start = dialog.numeric(0, 'Enter Intro Chapter Number')
                if not intro_start:
                    return None
                    
                outro_start = dialog.numeric(0, 'Enter Outro Start Chapter Number (Optional)')
                
                # Update show config with chapter settings
                config.update({
                    'use_defaults': True,
                    'use_chapters': True,
                    'intro_start_chapter': int(intro_start),
                    'outro_start_chapter': int(outro_start) if outro_start else None
                })
                db.save_show_config(show_id, config)
                
                # Return empty dict to indicate success without episode-specific save
                return {}
        
        # Time-based input
        intro_start = dialog.numeric(2, 'Enter Intro Start Time (MM:SS)')
        if not intro_start:
            return None
            
        intro_duration = dialog.numeric(2, 'Enter Intro Duration (MM:SS)')
        if not intro_duration:
            return None
            
        outro_start = dialog.numeric(2, 'Enter Outro Start Time (MM:SS) (Optional)')
        
        # Convert MM:SS to seconds using built-in time parsing
        def time_to_seconds(time_str):
            if not time_str:
                return None
            try:
                parts = time_str.split(':')
                return int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else None
            except (ValueError, IndexError):
                return None
            
        # Ask if these times should be used for all episodes
        use_defaults = dialog.yesno('Skip Intro', 'Use these times for all episodes of this show?')
        
        times = {
            'intro_start_chapter': None,
            'outro_start_chapter': None,
            'intro_start_time': time_to_seconds(intro_start),
            'intro_duration_time': time_to_seconds(intro_duration),
            'outro_start_time': time_to_seconds(outro_start) if outro_start else None,
            'source': 'manual'
        }
        
        # Update show config
        config.update({
            'use_defaults': use_defaults,
            'use_chapters': False,
            'intro_duration': time_to_seconds(intro_duration)
        })
        db.save_show_config(show_id, config)
        
        return times
    except Exception as e:
        xbmc.log(f'SkipIntro: Error getting manual times: {str(e)}', xbmc.LOGERROR)
        return None

def save_user_times():
    """Save user-provided times for show/episode"""
    xbmc.log('SkipIntro: Starting manual time input', xbmc.LOGINFO)
    
    item = get_selected_item_info()
    if not item:
        xbmc.log('SkipIntro: No item selected', xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Skip Intro', 'No item selected', xbmcgui.NOTIFICATION_ERROR)
        return
        
    # Initialize database
    xbmc.log('SkipIntro: Initializing database', xbmc.LOGINFO)
    addon = xbmcaddon.Addon()
    db_path = addon.getSetting('database_path')
    if not db_path:
        db_path = 'special://userdata/addon_data/plugin.video.skipintro/shows.db'
    
    translated_path = xbmcvfs.translatePath(db_path)
    xbmc.log(f'SkipIntro: Database path translated: {translated_path}', xbmc.LOGINFO)
    
    # Ensure database directory exists
    db_dir = os.path.dirname(translated_path)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        xbmc.log(f'SkipIntro: Created database directory: {db_dir}', xbmc.LOGINFO)
    
    try:
        db = ShowDatabase(translated_path)
        if not db:
            raise Exception("Failed to initialize database")
    except Exception as e:
        xbmc.log(f'SkipIntro: Database initialization error: {str(e)}', xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Skip Intro', 'Database error', xbmcgui.NOTIFICATION_ERROR)
        return
    show_id = db.get_show(item['showtitle'])
    if not show_id:
        xbmc.log('SkipIntro: Failed to get show ID', xbmc.LOGERROR)
        xbmcgui.Dialog().notification('Skip Intro', 'Database error', xbmcgui.NOTIFICATION_ERROR)
        return
    
    # Get times from user
    times = get_manual_times(show_id, db)
    if times is None:
        xbmc.log('SkipIntro: User cancelled time input', xbmc.LOGINFO)
        return
    
    if times:  # Only save episode times if we have times to save
        xbmc.log(f'SkipIntro: Saving episode times: {times}', xbmc.LOGINFO)
        success = db.save_episode_times(
            show_id,
            item['season'],
            item['episode'],
            times
        )
        
        if success:
            xbmc.log('SkipIntro: Episode times saved successfully', xbmc.LOGINFO)
            xbmcgui.Dialog().notification('Skip Intro', 'Times saved successfully', xbmcgui.NOTIFICATION_INFO)
        else:
            xbmc.log('SkipIntro: Failed to save episode times', xbmc.LOGERROR)
            xbmcgui.Dialog().notification('Skip Intro', 'Failed to save times', xbmcgui.NOTIFICATION_ERROR)
    else:
        xbmc.log('SkipIntro: Show config updated successfully', xbmc.LOGINFO)
        xbmcgui.Dialog().notification('Skip Intro', 'Show settings saved', xbmcgui.NOTIFICATION_INFO)

if __name__ == '__main__':
    save_user_times()
