FROM python:3.10-slim-bookworm

# Create working directory
RUN mkdir /bot && chmod 777 /bot
WORKDIR /bot
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y \
    git wget pv jq python3-dev mediainfo neofetch \
    build-essential yasm pkg-config libtool autoconf automake cmake \
    libass-dev libfreetype6-dev libsdl2-dev libtheora-dev libtool libva-dev \
    libvdpau-dev libvorbis-dev libxcb1-dev libxcb-shm0-dev libxcb-xfixes0-dev \
    texinfo zlib1g-dev nasm libx264-dev libx265-dev libnuma-dev libvpx-dev \
    libmp3lame-dev libopus-dev librsvg2-dev libwebp-dev

# Create directory for FFmpeg sources
RUN mkdir -p /ffmpeg_sources /ffmpeg_build

# Install libfdk-aac
RUN cd /ffmpeg_sources && \
    wget -O fdk-aac.tar.gz https://github.com/mstorsjo/fdk-aac/archive/refs/tags/v2.0.2.tar.gz && \
    tar xzvf fdk-aac.tar.gz && \
    cd fdk-aac-2.0.2 && \
    autoreconf -fiv && \
    ./configure --prefix="/ffmpeg_build" --disable-shared && \
    make -j$(nproc) && \
    make install

# Download and compile FFmpeg with non-free components
RUN cd /ffmpeg_sources && \
    wget -O ffmpeg.tar.bz2 https://ffmpeg.org/releases/ffmpeg-6.0.tar.bz2 && \
    tar xjvf ffmpeg.tar.bz2 && \
    cd ffmpeg-6.0 && \
    PATH="/ffmpeg_build/bin:$PATH" PKG_CONFIG_PATH="/ffmpeg_build/lib/pkgconfig" ./configure \
    --prefix="/ffmpeg_build" \
    --pkg-config-flags="--static" \
    --extra-cflags="-I/ffmpeg_build/include" \
    --extra-ldflags="-L/ffmpeg_build/lib" \
    --extra-libs="-lpthread -lm" \
    --enable-gpl \
    --enable-nonfree \
    --enable-libass \
    --enable-libfdk-aac \
    --enable-libfreetype \
    --enable-libmp3lame \
    --enable-libopus \
    --enable-libtheora \
    --enable-libvorbis \
    --enable-libvpx \
    --enable-libx264 \
    --enable-libx265 \
    && \
    PATH="/ffmpeg_build/bin:$PATH" make -j$(nproc) && \
    make install && \
    hash -r

# Create symbolic links to the compiled FFmpeg binaries
RUN ln -sf /ffmpeg_build/bin/ffmpeg /usr/local/bin/ffmpeg && \
    ln -sf /ffmpeg_build/bin/ffprobe /usr/local/bin/ffprobe

# Clean up to reduce image size
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /ffmpeg_sources

# Copy your application files
COPY . .
RUN pip3 install -r requirements.txt

EXPOSE 8000
CMD ["bash","run.sh"]