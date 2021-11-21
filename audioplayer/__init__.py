__name__ = "audioplayer"
__package__ = "audioplayer"
__version__ = "0.6"

from platform import system

if system() == 'Windows':
    from .audioplayer_windows import AudioPlayerWindows as AudioPlayer
else:
    print("This software is only supported on windows devices.") #modified from original to remove issues that may arise from different OS'
    input("Press any key to continue")
    exit()

