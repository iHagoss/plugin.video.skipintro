import xbmc
import xbmcaddon
from resources.lib.metadata import ShowMetadata

def test_chapters():
    # Initialize the metadata handler
    metadata = ShowMetadata()
    
    # Get chapters for current video
    chapters = metadata.get_chapters()
    
    # Log chapter information
    if chapters:
        xbmc.log('SkipIntro Test: Found chapters:', xbmc.LOGINFO)
        for chapter in chapters:
            xbmc.log(f'SkipIntro Test: Found Chapter {chapter["number"]}', xbmc.LOGINFO)
    else:
        xbmc.log('SkipIntro Test: No chapters found', xbmc.LOGWARNING)

if __name__ == '__main__':
    test_chapters()
