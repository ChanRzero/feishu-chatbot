import uvicorn

if __name__ == "__main__":
    config = uvicorn.Config("process:app", port=80, log_level="info")
    server = uvicorn.Server(config)
    server.run()
