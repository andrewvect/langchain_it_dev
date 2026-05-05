"""Manual test: ping each model via copilot CLI with a simple prompt."""

import subprocess
import shutil
import time

COPILOT_BIN = (
    shutil.which("copilot")
    or "/Users/andrey/.nvm/versions/node/v20.20.2/bin/copilot"
)

MODELS = [
    "claude-haiku-4.5",
    "claude-sonnet-4.6",
    "gpt-4o-mini",
    "gpt-4.1",
    "gpt-5.4",
    "gpt-5.4-mini",
]

PROMPT = "Reply with exactly one word: PONG"


def check_model(model: str) -> tuple[bool, str, float]:
    start = time.time()
    try:
        result = subprocess.run(
            [COPILOT_BIN, "-p", PROMPT, "--silent",
                "--allow-all-tools", "--model", model],
            capture_output=True,
            text=True,
            timeout=60,
            stdin=subprocess.DEVNULL,
        )
        elapsed = time.time() - start
        if result.returncode != 0:
            return False, result.stderr.strip()[:120], elapsed
        return True, result.stdout.strip()[:120], elapsed
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT (60s)", time.time() - start


def main():
    print(f"{'Model':<25} {'Status':<8} {'Response':<30} {'Time':>6}")
    print("─" * 75)
    for model in MODELS:
        ok, response, elapsed = check_model(model)
        status = "✅ OK" if ok else "❌ ERR"
        print(f"{model:<25} {status:<8} {response:<30} {elapsed:>5.1f}s")


if __name__ == "__main__":
    main()
