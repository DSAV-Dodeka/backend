import uvicorn


def run():
    uvicorn.run("app:app", host="127.0.0.1", port=5000)


if __name__ == '__main__':
    run()
