FROM nixos/nix AS builder

WORKDIR /app

RUN mkdir -p /output/store

# Install batsim
RUN nix-env -f https://github.com/oar-team/nur-kapack/archive/master.tar.gz --profile /output/profile -iA batsim pybatsim batexpe

# Copy all the run time dependencies into /output/store
RUN cp -va $(nix-store -qR /output/profile) /output/store

ENTRYPOINT [ "/bin/sh" ]

FROM python:3.10-slim

WORKDIR /sched-sim

COPY --from=builder /output/store /nix/store
COPY --from=builder /output/profile /usr/.local

RUN apt update -y && apt install -y git iproute2 procps

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:/usr/.local/bin:$PATH"
RUN pip install evalys pybatsim pandas matplotlib pyswarms scipy

CMD ["bash"]