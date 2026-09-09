# ============================================================
# НАСТРОЙКИ
# ============================================================

PYTHON = python

SERVER_DIR = D:/AI
SERVER = D:/AI/llama-server.exe
MODEL = D:/AI/models/Qwen3-8B-Q4_K_M.gguf

SERVER_ARGS = \
	-m "$(MODEL)" \
	-ngl 99 \
	-c 4096 \
	-t 12 \
	--port 8080 \
	--reasoning off


# ============================================================
# КОМАНДЫ
# ============================================================

.PHONY: server run start

server:
	powershell -NoProfile -Command "& '$(SERVER)' $(SERVER_ARGS)"

run:
	$(PYTHON) main.py

start:
	powershell -NoProfile -Command "Start-Process powershell -ArgumentList '-NoExit', '-Command', '& ''$(SERVER)'' $(SERVER_ARGS)'"
	$(PYTHON) main.py