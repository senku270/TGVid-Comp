FROM python:3.9.2-slim-buster

# Set up working directory
RUN mkdir /bot && chmod 777 /bot
WORKDIR /bot

# Set environment variable for non-interactive installations
ENV DEBIAN_FRONTEND=noninteractive

# Update package list and install dependencies
RUN apt update && apt install -y \
    git wget pv jq python3-dev curl software-properties-common \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

# Install latest FFmpeg 6.x from Debian Multimedia repository
RUN echo "deb http://www.deb-multimedia.org buster main non-free" | tee /etc/apt/sources.list.d/deb-multimedia.list && \
    apt update && \
    apt install -y --allow-change-held-packages deb-multimedia-keyring && \
    apt update && \
    apt install -y ffmpeg mediainfo && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

# Install neofetch (for system info)
RUN apt-get install neofetch -y -f

# Copy bot files
COPY . .

# Install Python dependencies
RUN pip3 install -r requirements.txt

# Start the bot
CMD ["bash","run.sh"]