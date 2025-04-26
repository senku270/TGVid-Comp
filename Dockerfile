FROM python:3.10-slim-bookworm
RUN mkdir /bot && chmod 777 /bot
WORKDIR /bot
ENV DEBIAN_FRONTEND=noninteractive

# Update and install dependencies
RUN apt -qq update && apt -qq install -y git wget pv jq python3-dev mediainfo
RUN apt-get install neofetch -y -f

# Download and install the specific FFmpeg build
RUN wget -q https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz && \
    mkdir -p /opt/ffmpeg && \
    tar -xf ffmpeg-master-latest-linux64-gpl.tar.xz -C /opt/ffmpeg --strip-components=1 && \
    ln -sf /opt/ffmpeg/bin/ffmpeg /usr/bin/ffmpeg && \
    ln -sf /opt/ffmpeg/bin/ffprobe /usr/bin/ffprobe && \
    rm ffmpeg-master-latest-linux64-gpl.tar.xz

COPY . .
RUN pip3 install -r requirements.txt
EXPOSE 8000
CMD ["bash","run.sh"]