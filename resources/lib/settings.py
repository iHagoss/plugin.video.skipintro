import xbmc
import xbmcaddon

class Settings:
    def __init__(self):
        self.addon = xbmcaddon.Addon()
        self.settings = self.validate_settings()

    def validate_settings(self):
        """Validate and sanitize addon settings"""
        try:
            default_delay = int(self.addon.getSetting('default_delay'))
            skip_duration = int(self.addon.getSetting('skip_duration'))
            use_chapters = self.addon.getSettingBool('use_chapters')
            use_api = self.addon.getSettingBool('use_api')
            save_times = self.addon.getSettingBool('save_times')
            
            # Ensure values are within reasonable bounds
            if default_delay < 0:
                default_delay = 30
                self.addon.setSetting('default_delay', '30')
            elif default_delay > 300:  # Max 5 minutes
                default_delay = 300
                self.addon.setSetting('default_delay', '300')
                
            if skip_duration < 10:  # Min 10 seconds
                skip_duration = 60
                self.addon.setSetting('skip_duration', '60')
            elif skip_duration > 300:  # Max 5 minutes
                skip_duration = 300
                self.addon.setSetting('skip_duration', '300')
                
            return {
                'default_delay': default_delay,
                'skip_duration': skip_duration,
                'use_chapters': use_chapters,
                'use_api': use_api,
                'save_times': save_times
            }
        except ValueError as e:
            xbmc.log('SkipIntro: Error reading settings: {} - using defaults'.format(str(e)), xbmc.LOGERROR)
            return {
                'default_delay': 30,
                'skip_duration': 60,
                'use_chapters': True,
                'use_api': False,
                'save_times': True
            }

    def get_setting(self, key):
        return self.settings.get(key)
