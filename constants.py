import os
import platform


USERNAME = "mindyt@ridgevalleyexteriors.com"
PASSWORD = "Roofing20!"

DOWNLOAD_DIRECTORY = "%s%soutput" % (
    os.path.dirname(os.path.realpath(__file__)),
    os.sep,
)

CHROME_DRIVER = None
if os.name == "nt":
    CHROME_DRIVER = "%s%sdrivers%schromedriver.exe" % (
        os.path.dirname(os.path.realpath(__file__)),
        os.sep,
        os.sep,
    )
elif platform.system() == "Linux":
    CHROME_DRIVER = "%s%sdrivers%schromedriverlinux" % (
        os.path.dirname(os.path.realpath(__file__)),
        os.sep,
        os.sep,
    )
elif os.name == "posix":
    CHROME_DRIVER = "%s%sdrivers%schromedriver" % (
        os.path.dirname(os.path.realpath(__file__)),
        os.sep,
        os.sep,
    )