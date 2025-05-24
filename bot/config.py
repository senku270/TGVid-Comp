#    Copyright (c) 2021 Danish_00
#    Improved By @Zylern
from decouple import config

try:
    APP_ID = config("APP_ID", default=24810254, cast=int)
    API_HASH = config("API_HASH", default="aadb42caec01695fa0a77c09b3e0ef47")
    BOT_TOKEN = config("BOT_TOKEN", default="5822396703:AAH2V7eOy9-UdqyVpWkawnHbDXzdvpfsc0w")
    DEV = config("DEV", default="5385471287")
    OWNER = config("OWNER", default="5385471287")
    ffmpegcode = ["-preset faster -c:v libx265 -s 854x480 -x265-params 'bframes=8:psy-rd=1:ref=3:aq-mode=3:aq-strength=0.8:deblock=1,1' -metadata 'title=Encoded By TGVid-Comp (https://github.com/Zylern/TGVid-Comp)' -pix_fmt yuv420p -crf 30 -c:a libopus -b:a 32k -c:s copy -map 0 -ac 2 -ab 32k -vbr 2 -level 3.1 -threads 1"]
    TELEGRAPH_API = config("TELEGRAPH_API", default="https://api.telegra.ph")
    THUMB = config(
        "THUMBNAIL", default="https://graph.org/file/75ee20ec8d8c8bba84f02.jpg"
    )
except Exception as e:
    print("Environment vars Missing! Exiting App.")
    print(str(e))
    exit(1)
