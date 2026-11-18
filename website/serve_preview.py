"""Dev/preview launcher, including tools that pass --host/--port to npm run dev."""

import argparse
import os

import uvicorn

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    args, _ = p.parse_known_args()
    uvicorn.run("app.main:app", host=args.host, port=args.port)
