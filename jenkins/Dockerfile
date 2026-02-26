FROM jenkins/jenkins:lts
USER root
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    docker.io \
    gnupg \
    lsb-release \
    python3-pip \
    shellcheck \
    && rm -rf /var/lib/apt/lists/*

# Python linters/security tools
RUN pip3 install --no-cache-dir flake8 bandit

# hadolint
RUN curl -sSLo /usr/local/bin/hadolint \
    "https://github.com/hadolint/hadolint/releases/latest/download/hadolint-Linux-x86_64" \
    && chmod +x /usr/local/bin/hadolint

# trivy
RUN curl -fsSL https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor -o /usr/share/keyrings/trivy.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" \
    > /etc/apt/sources.list.d/trivy.list \
    && apt-get update \
    && apt-get install -y trivy \
    && rm -rf /var/lib/apt/lists/*
USER jenkins
