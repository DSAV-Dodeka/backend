import uvicorn


def run():
    uvicorn.run("dodekaserver.app:app", host="127.0.0.1", port=4242, reload=True)


if __name__ == '__main__':
    run()
