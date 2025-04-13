# Use python:3.10 slim image as the base
FROM python:3.10-slim-bookworm

# Set the bot directory and give necessary permissions
RUN mkdir /bot && chmod 777 /bot
WORKDIR /bot

# Set environment variable to avoid interactive prompts during apt-get installation
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies including FFmpeg, mediainfo, git, etc.
RUN apt -qq update && apt -qq install -y \
    git wget pv jq python3-dev ffmpeg mediainfo \
    build-essential cmake yasm nasm pkg-config libtool \
    zlib1g-dev libssl-dev libass-dev libfdk-aac-dev \
    libx264-dev libvpx-dev libx265-dev libfreetype6-dev \
    libfontconfig1-dev libfribidi-dev libharfbuzz-dev \
    && rm -rf /var/lib/apt/lists/*

# Clone and build SVT-HEVC
RUN git clone https://gitlab.com/AOMediaCodec/SVT-HEVC.git /opt/SVT-HEVC && \
    cd /opt/SVT-HEVC/Build/linux && \
    ./build.sh release && \
    mkdir -p /usr/local/lib /usr/local/include && \
    cp /opt/SVT-HEVC/Bin/Release/libSvtHevcEnc.so /usr/local/lib/ && \
    cp /opt/SVT-HEVC/Source/API/svt-hevcenc.h /usr/local/include/

# Clone FFmpeg and build it with SVT-HEVC support
RUN git clone https://git.ffmpeg.org/ffmpeg.git /opt/ffmpeg && \
    cd /opt/ffmpeg && \
    ./configure --prefix=/usr/local --enable-gpl --enable-libsvthevc --enable-nonfree && \
    make -j$(nproc) && \
    make install

# Add FFmpeg to PATH
ENV PATH="/usr/local/bin:${PATH}"

# Clean up unnecessary build files to reduce image size
RUN rm -rf /opt/SVT-HEVC /opt/ffmpeg

# Copy your project files into the container
COPY . .

# Install Python dependencies
RUN pip3 install -r requirements.txt

# Run the bot using the run.sh script
CMD ["bash", "run.sh"]