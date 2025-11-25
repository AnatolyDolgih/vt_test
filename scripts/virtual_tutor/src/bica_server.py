from unified_server import app

if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("unified_server:app", host="0.0.0.0", port=5050, reload=False)
