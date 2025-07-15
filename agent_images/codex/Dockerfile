# you must build the claude_code image first

FROM claude_code

RUN npm install -g @openai/codex@0.1.2504172351

ENTRYPOINT ["codex", "--dangerously-auto-approve-everything", "--quiet", "--full-stdout"]


