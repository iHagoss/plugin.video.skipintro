import xbmc
import xbmcgui

class PlayerUI:
    def __init__(self):
        self.prompt_shown = False

    def prompt_skip_intro(self, callback):
        """Show skip intro dialog and execute callback if user agrees"""
        xbmc.log('SkipIntro: Prompting user to skip intro', xbmc.LOGINFO)
        try:
            dialog = xbmcgui.Dialog()
            choice = dialog.yesno(
                heading='Skip Intro',
                message='Skip intro sequence?',
                nolabel='No',
                yeslabel='Skip',
                autoclose=10000
            )
            xbmc.log('SkipIntro: User choice from dialog: {}'.format(choice), xbmc.LOGINFO)
            
            if choice:
                callback()
            return choice
                
        except Exception as e:
            xbmc.log('SkipIntro: Error showing skip prompt: {}'.format(str(e)), xbmc.LOGERROR)
            return False

    def show_notification(self, message, time=5000):
        """Show a notification message"""
        xbmc.executebuiltin(f'Notification(SkipIntro,{message},{time})')
