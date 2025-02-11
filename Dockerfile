# Use an official Ubuntu as a base image
FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV NVM_DIR=/root/.nvm
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/tests
ENV DISPLAY=:99
ENV LIBGL_ALWAYS_INDIRECT=1

# Update package list and install basic utilities
RUN apt-get update && apt-get install -y \
    curl \
    git \
    wget \
    tar \
    gzip \
    gnupg \
    openssh-client \
    xz-utils \
    patch \
    --no-install-recommends

# Install Python and related tools
RUN apt install software-properties-common -y && \
    add-apt-repository ppa:deadsnakes/ppa -y

RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    --no-install-recommends

# Install conda
RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh -O /tmp/miniconda.sh \
    && bash /tmp/miniconda.sh -b -p /opt/conda \
    && rm -f /tmp/miniconda.sh \
    && /opt/conda/bin/conda clean -ya
ENV PATH="/opt/conda/bin:$PATH"

# Create testbed
RUN conda create -n testbed python=3.12

# Install browser dependencies
RUN apt-get update && apt-get install -y \
    chromium-browser \
    fonts-liberation \
    fonts-noto-color-emoji \
    libnss3-tools \
    libatk-bridge2.0-0 \
    libnss3 \
    libxcomposite1 \
    libxrandr2 \
    libxdamage1 \
    libxkbcommon0 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    --no-install-recommends

# Install Xvfb, Fluxbox, and VNC tools
RUN apt-get update && apt-get install -y \
    xvfb \
    fluxbox \
    x11vnc \
    novnc \
    websockify \
    --no-install-recommends

# Install GNOME/GTK-related dependencies for proper GUI support
RUN apt-get update && apt-get install -y \
    gnome-settings-daemon \
    gnome-session-bin \
    gnome-control-center \
    dconf-cli \
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    --no-install-recommends

# Install libraries to fix Xvfb-related issues
RUN apt-get update && apt-get install -y \
    libsecret-1-0 \
    --no-install-recommends

# Install dependencies related to tests
RUN apt-get update && apt-get install -y \
    mkcert \
    watchman \
    python3-pyqt5 \
    ffmpeg \
    --no-install-recommends

# Clone the GitHub repository into /app/expensify
# RUN mkdir -p -m 0700 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts
RUN git clone https://github.com/Expensify/App.git /app/expensify --single-branch

# Install NVM and Node.js
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash && \
    . "$NVM_DIR/nvm.sh"

# Install Pip and Pipx
COPY requirements.txt .
RUN curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python3.12 get-pip.py && \
    python3.12 -m pip install --upgrade pip && \
    python3.12 -m pip install --no-cache-dir -r requirements.txt && \
    python3.12 -m pipx ensurepath && \
    /bin/bash -c "source /root/.bashrc"

# Install ansible
RUN python3.12 -m pipx install --include-deps ansible==11.1.0

# Install browser drivers
RUN python3.12 -m pipx run --spec playwright playwright install

# Install mitmdump, mitmproxy, and inject dependencies
COPY requirements.txt .
RUN python3.12 -m pipx install mitmproxy==11.0.2 && \
    python3.12 -m pipx runpip mitmproxy install -r requirements.txt

# Install pytest, dependencies, and browser drivers
COPY requirements.txt .
RUN python3.12 -m pipx install pytest==8.3.4 && \
    python3.12 -m pipx runpip pytest install -r requirements.txt

# Create the /app/tests/ directory
RUN mkdir -p /app/tests

# Copy files into the /app/tests/ directory
COPY issues/ /app/tests/issues/
COPY utils/ /app/tests/utils/
COPY runtime_scripts/setup_expensify.yml /app/tests/setup_expensify.yml
COPY runtime_scripts/setup_mitmproxy.yml /app/tests/setup_mitmproxy.yml
COPY runtime_scripts/run_test.yml /app/tests/run_test.yml
COPY runtime_scripts/run_fixed_state.yml /app/tests/run_fixed_state.yml
COPY runtime_scripts/run_user_tool.yml /app/tests/run_user_tool.yml
COPY runtime_scripts/run_broken_state.yml /app/tests/run_broken_state.yml
COPY runtime_scripts/setup_eval.yml /app/tests/setup_eval.yml
COPY runtime_scripts/run.sh /app/tests/run.sh
COPY runtime_scripts/replay.py /app/tests/replay.py
COPY runtime_scripts/rewrite_test.py /app/tests/rewrite_test.py
COPY runtime_scripts/npm_fix.py /app/expensify/npm_fix.py
RUN chmod +x /app/tests/run.sh
WORKDIR /app/expensify

# Expose the NoVNC and VNC ports
EXPOSE 5901
EXPOSE 5900

# Create python alias
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1 && \
    update-alternatives --set python /usr/bin/python3

# Set the entrypoint and default command
ENTRYPOINT ["/bin/bash", "-l", "-c"]
CMD ["/app/tests/run.sh"]
