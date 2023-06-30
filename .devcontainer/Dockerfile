FROM ubuntu:latest

# Instala curl y bzip2
RUN apt-get update -y && \
    apt-get install -y curl bzip2

# Instala Nix
RUN curl -L https://nixos.org/nix/install | sh

# Agrega nix a tu path
ENV PATH="/root/.nix-profile/bin:${PATH}"
