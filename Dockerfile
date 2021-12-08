FROM dodeka/server-deps AS install
COPY . .
RUN poetry install

FROM install as runtime
ENTRYPOINT ["./entrypoint.sh"]