import uvicorn


def run() -> None:
    """Run function for use in development environment."""
    uvicorn.run(
        "apiserver.app_inst:apiserver_app",
        host="127.0.0.1",
        port=4243,
        reload=True,
        access_log=False,
    )


if __name__ == "__main__":
    run()
