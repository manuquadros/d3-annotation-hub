import uvicorn

if __name__ == "__main__":
    uvicorn.run("ahbackend.api.api:app", reload=True, reload_dirs=["src"])
