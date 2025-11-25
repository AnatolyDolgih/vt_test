from unified_server import app

if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("unified_server:app", host="127.0.0.1", port=5000, reload=False)
