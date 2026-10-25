from fastapi import FastAPI

app = FastAPI(title="Docket")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
