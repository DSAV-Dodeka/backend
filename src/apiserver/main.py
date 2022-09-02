import uvicorn


def run():
    """ Run function for use in tests. """
    uvicorn.run("apiserver.app:app", host="127.0.0.1", port=4243, reload=True)


if __name__ == '__main__':
    run()
