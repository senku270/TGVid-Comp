FROM python:3.9.2-slim-buster

# Set up working directory
RUN mkdir /bot && chmod 777 /bot
WORKDIR /bot

# Set environment variable for non-interactive installations
ENV DEBIAN_FRONTEND=noninteractive

# Update package list and install dependencies
RUN apt -qq update && apt -qq install -y \
    git wget pv jq python3-dev \
    software-properties-common \
    && add-apt-repository ppa:savoury1/ffmpeg4 \
    && apt update \
    && apt install -y ffmpeg=6.0.1* mediainfo \
    && apt clean \
    && rm -rf /var/lib/apt/lists/*

# Install neofetch (for system info)
RUN apt-get install neofetch -y -f

# Copy bot files
COPY . .

# Install Python dependencies
RUN pip3 install -r requirements.txt

# Start the bot
CMD ["bash","run.sh"]