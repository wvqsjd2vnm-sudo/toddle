import sys

from . import agent, scraper

cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
if cmd == "login":
    scraper.login_interactive()
elif cmd == "run":
    agent.run(headless="--show" not in sys.argv)
else:
    print("usage: python -m toddle_agent [login|run [--show]]")
